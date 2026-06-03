"""Anthropic provider: LLM only.

Embeddings are not offered by Anthropic — use the ``local`` or ``openai`` embedding
provider alongside this one. Structured output is achieved with a forced tool call whose
``input_schema`` is the requested JSON schema (Anthropic has no JSON-schema chat mode),
with a prompt-and-repair fallback.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from citely.config import Config
from citely.providers.base import (
    GenerationConfig,
    LLMProvider,
    Message,
    StructuredOutputError,
    try_parse_json,
)

_REPAIR_REMINDER = (
    "Your previous reply was not valid JSON. Return ONLY a single valid JSON object. "
    "No prose, no code fences."
)


def _split_messages(messages: list[Message]) -> tuple[str | None, list[dict]]:
    """Anthropic takes ``system`` separately from the user/assistant turns."""
    system_parts = [m.content for m in messages if m.role == "system"]
    convo = [
        {"role": m.role, "content": m.content}
        for m in messages
        if m.role in ("user", "assistant")
    ]
    system = "\n\n".join(system_parts) if system_parts else None
    return system, convo


def _client(timeout_s: float) -> AsyncAnthropic:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in the environment.")
    return AsyncAnthropic(api_key=key, timeout=timeout_s)


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str, timeout_s: float = 120.0) -> None:
        self._model = model
        self._timeout = timeout_s

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self, messages: list[Message], cfg: GenerationConfig | None = None
    ) -> str:
        cfg = cfg or GenerationConfig()
        system, convo = _split_messages(messages)
        client = _client(self._timeout)
        resp = await client.messages.create(
            model=self._model,
            system=system or "",
            messages=convo,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    async def stream(
        self, messages: list[Message], cfg: GenerationConfig | None = None
    ) -> AsyncIterator[str]:
        cfg = cfg or GenerationConfig()
        system, convo = _split_messages(messages)
        client = _client(self._timeout)
        async with client.messages.stream(
            model=self._model,
            system=system or "",
            messages=convo,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                if text:
                    yield text

    async def generate_json(
        self, messages: list[Message], schema: dict, cfg: GenerationConfig | None = None
    ) -> dict:
        cfg = cfg or GenerationConfig()
        system, convo = _split_messages(messages)
        client = _client(self._timeout)
        tool = {
            "name": "emit",
            "description": "Emit the structured result.",
            "input_schema": schema,
        }
        resp = await client.messages.create(
            model=self._model,
            system=system or "",
            messages=convo,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            tools=[tool],
            tool_choice={"type": "tool", "name": "emit"},
        )
        for block in resp.content:
            if block.type == "tool_use" and isinstance(block.input, dict):
                return block.input

        # Fallback: plain text + parse + repair.
        text = "".join(b.text for b in resp.content if b.type == "text")
        parsed = try_parse_json(text)
        if parsed is not None:
            return parsed

        repair = [*convo, {"role": "user", "content": _REPAIR_REMINDER}]
        resp = await client.messages.create(
            model=self._model,
            system=system or "",
            messages=repair,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        parsed = try_parse_json(text)
        if parsed is None:
            raise StructuredOutputError(
                f"Anthropic model {self._model} did not return valid JSON after repair."
            )
        return parsed


def build_anthropic_llm(cfg: Config) -> AnthropicProvider:
    return AnthropicProvider(
        model=cfg.models.anthropic_llm,
        timeout_s=cfg.providers.request_timeout_s,
    )
