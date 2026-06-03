"""OpenAI provider: LLM (chat) + embeddings via the official async client.

The ``openai`` package is imported at module top. The factory only imports this module
when an OpenAI path is selected, so an unset ``OPENAI_API_KEY`` or a missing package
never breaks unrelated phases.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from citely.config import Config
from citely.providers.base import (
    EmbeddingProvider,
    GenerationConfig,
    LLMProvider,
    Message,
    StructuredOutputError,
    try_parse_json,
)

_KNOWN_EMBED_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}

_REPAIR_REMINDER = (
    "Your previous reply was not valid JSON. Return ONLY a single valid JSON object. "
    "No prose, no code fences."
)


def _to_openai_messages(messages: list[Message]) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in messages]


def _client(base_url: str | None, timeout_s: float) -> AsyncOpenAI:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set in the environment.")
    return AsyncOpenAI(api_key=key, base_url=base_url, timeout=timeout_s)


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        timeout_s: float = 120.0,
    ) -> None:
        self._model = model
        self._base_url = base_url
        self._timeout = timeout_s

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self, messages: list[Message], cfg: GenerationConfig | None = None
    ) -> str:
        cfg = cfg or GenerationConfig()
        client = _client(self._base_url, self._timeout)
        resp = await client.chat.completions.create(
            model=self._model,
            messages=_to_openai_messages(messages),
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
        return resp.choices[0].message.content or ""

    async def stream(
        self, messages: list[Message], cfg: GenerationConfig | None = None
    ) -> AsyncIterator[str]:
        cfg = cfg or GenerationConfig()
        client = _client(self._base_url, self._timeout)
        stream = await client.chat.completions.create(
            model=self._model,
            messages=_to_openai_messages(messages),
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def generate_json(
        self, messages: list[Message], schema: dict, cfg: GenerationConfig | None = None
    ) -> dict:
        cfg = cfg or GenerationConfig()
        client = _client(self._base_url, self._timeout)
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": "citely_response", "schema": schema, "strict": False},
        }
        resp = await client.chat.completions.create(
            model=self._model,
            messages=_to_openai_messages(messages),
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            response_format=response_format,
        )
        text = resp.choices[0].message.content or ""
        parsed = try_parse_json(text)
        if parsed is not None:
            return parsed

        repair = [*messages, Message("user", _REPAIR_REMINDER)]
        resp = await client.chat.completions.create(
            model=self._model,
            messages=_to_openai_messages(repair),
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content or ""
        parsed = try_parse_json(text)
        if parsed is None:
            raise StructuredOutputError(
                f"OpenAI model {self._model} did not return valid JSON after repair."
            )
        return parsed


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        timeout_s: float = 120.0,
        batch_size: int = 256,
    ) -> None:
        self._model = model
        self._base_url = base_url
        self._timeout = timeout_s
        self._batch_size = batch_size
        self._dim: int | None = _KNOWN_EMBED_DIMS.get(model)

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        if self._dim is None:
            from openai import OpenAI

            key = os.environ.get("OPENAI_API_KEY")
            if not key:
                raise RuntimeError("OPENAI_API_KEY is not set in the environment.")
            sync = OpenAI(api_key=key, base_url=self._base_url, timeout=self._timeout)
            vec = sync.embeddings.create(model=self._model, input="dimension probe")
            self._dim = len(vec.data[0].embedding)
        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = _client(self._base_url, self._timeout)
        out: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            resp = await client.embeddings.create(model=self._model, input=batch)
            out.extend(item.embedding for item in resp.data)
        if self._dim is None and out:
            self._dim = len(out[0])
        return out


def build_openai_llm(cfg: Config) -> OpenAIProvider:
    return OpenAIProvider(
        model=cfg.models.openai_llm,
        base_url=cfg.providers.openai_base_url,
        timeout_s=cfg.providers.request_timeout_s,
    )


def build_openai_embedding(cfg: Config) -> OpenAIEmbeddingProvider:
    return OpenAIEmbeddingProvider(
        model=cfg.models.openai_embed,
        base_url=cfg.providers.openai_base_url,
        timeout_s=cfg.providers.request_timeout_s,
    )
