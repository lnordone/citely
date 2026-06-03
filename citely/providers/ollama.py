"""Ollama provider: local LLM (chat) and embeddings over the Ollama HTTP API.

``httpx`` is imported at module top (it is a hard dependency); the Ollama *server* is a
runtime dependency contacted lazily, so importing this module never requires a running
Ollama.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from citely.config import Config
from citely.logging import get_logger
from citely.providers.base import (
    EmbeddingProvider,
    GenerationConfig,
    LLMProvider,
    Message,
    StructuredOutputError,
    try_parse_json,
)

log = get_logger(__name__)

# Known embedding dimensions; otherwise we probe the server once.
_KNOWN_DIMS = {
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    "all-minilm": 384,
}

_REPAIR_REMINDER = (
    "Your previous reply was not valid JSON. Return ONLY a single valid JSON object "
    "matching the requested schema. No prose, no code fences."
)


def _options(cfg: GenerationConfig, num_ctx: int) -> dict:
    return {
        "temperature": cfg.temperature,
        "num_predict": cfg.max_tokens,
        "num_ctx": num_ctx,
    }


def _to_ollama_messages(messages: list[Message]) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in messages]


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        model: str,
        host: str,
        num_ctx: int = 8192,
        timeout_s: float = 120.0,
    ) -> None:
        self._model = model
        self._host = host.rstrip("/")
        self._num_ctx = num_ctx
        self._timeout = timeout_s

    @property
    def model_name(self) -> str:
        return self._model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
    async def generate(
        self, messages: list[Message], cfg: GenerationConfig | None = None
    ) -> str:
        cfg = cfg or GenerationConfig()
        payload = {
            "model": self._model,
            "messages": _to_ollama_messages(messages),
            "stream": False,
            "options": _options(cfg, self._num_ctx),
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._host}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("message", {}).get("content", "")

    async def stream(
        self, messages: list[Message], cfg: GenerationConfig | None = None
    ) -> AsyncIterator[str]:
        cfg = cfg or GenerationConfig()
        payload = {
            "model": self._model,
            "messages": _to_ollama_messages(messages),
            "stream": True,
            "options": _options(cfg, self._num_ctx),
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", f"{self._host}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    import json as _json

                    try:
                        chunk = _json.loads(line)
                    except _json.JSONDecodeError:
                        continue
                    delta = chunk.get("message", {}).get("content", "")
                    if delta:
                        yield delta
                    if chunk.get("done"):
                        break

    async def generate_json(
        self, messages: list[Message], schema: dict, cfg: GenerationConfig | None = None
    ) -> dict:
        cfg = cfg or GenerationConfig()
        # Ollama supports JSON-schema-constrained output via the `format` field.
        payload = {
            "model": self._model,
            "messages": _to_ollama_messages(messages),
            "stream": False,
            "format": schema,
            "options": _options(cfg, self._num_ctx),
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._host}/api/chat", json=payload)
            resp.raise_for_status()
            text = resp.json().get("message", {}).get("content", "")

        parsed = try_parse_json(text)
        if parsed is not None:
            return parsed

        # Repair pass: remind the model to return only JSON, retry once.
        repair_messages = [*messages, Message("user", _REPAIR_REMINDER)]
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._host}/api/chat",
                json={
                    "model": self._model,
                    "messages": _to_ollama_messages(repair_messages),
                    "stream": False,
                    "format": schema,
                    "options": _options(cfg, self._num_ctx),
                },
            )
            resp.raise_for_status()
            text = resp.json().get("message", {}).get("content", "")
        parsed = try_parse_json(text)
        if parsed is None:
            raise StructuredOutputError(
                f"Ollama model {self._model} did not return valid JSON after repair."
            )
        return parsed


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model: str,
        host: str,
        timeout_s: float = 120.0,
    ) -> None:
        self._model = model
        self._host = host.rstrip("/")
        self._timeout = timeout_s
        self._dim: int | None = _KNOWN_DIMS.get(model)

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        if self._dim is None:
            # One-time synchronous probe so the property can be read at startup.
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{self._host}/api/embed",
                    json={"model": self._model, "input": "dimension probe"},
                )
                resp.raise_for_status()
                vec = resp.json()["embeddings"][0]
            self._dim = len(vec)
        return self._dim

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._host}/api/embed",
                json={"model": self._model, "input": texts},
            )
            resp.raise_for_status()
            vectors = resp.json()["embeddings"]
        if self._dim is None and vectors:
            self._dim = len(vectors[0])
        return vectors


def build_ollama_llm(cfg: Config) -> OllamaProvider:
    return OllamaProvider(
        model=cfg.models.ollama_llm,
        host=cfg.providers.ollama_host,
        num_ctx=cfg.models.num_ctx,
        timeout_s=cfg.providers.request_timeout_s,
    )


def build_ollama_embedding(cfg: Config) -> OllamaEmbeddingProvider:
    return OllamaEmbeddingProvider(
        model=cfg.models.ollama_embed,
        host=cfg.providers.ollama_host,
        timeout_s=cfg.providers.request_timeout_s,
    )
