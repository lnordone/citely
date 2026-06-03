"""Shared fixtures: mock providers (no network), and placeholders for db/passages.

The mock providers conform to the real ABCs so interface-level tests run with zero
network/model dependencies.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from citely.providers.base import (
    EmbeddingProvider,
    GenerationConfig,
    LLMProvider,
    Message,
)


class MockLLMProvider(LLMProvider):
    """Deterministic, offline LLMProvider for tests."""

    def __init__(self, model: str = "mock-llm", reply: str = "mock reply") -> None:
        self._model = model
        self._reply = reply
        self.calls: list[tuple[str, list[Message]]] = []

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self, messages: list[Message], cfg: GenerationConfig | None = None
    ) -> str:
        self.calls.append(("generate", messages))
        return self._reply

    async def stream(
        self, messages: list[Message], cfg: GenerationConfig | None = None
    ) -> AsyncIterator[str]:
        self.calls.append(("stream", messages))
        for token in self._reply.split():
            yield token + " "

    async def generate_json(
        self, messages: list[Message], schema: dict, cfg: GenerationConfig | None = None
    ) -> dict:
        self.calls.append(("generate_json", messages))
        return {"echo": messages[-1].content if messages else ""}


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic, offline EmbeddingProvider (hash-based pseudo-vectors)."""

    def __init__(self, model: str = "mock-embed", dim: int = 8) -> None:
        self._model = model
        self._dim = dim

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            seed = sum(ord(c) for c in t)
            out.append([((seed + i) % 17) / 17.0 for i in range(self._dim)])
        return out


@pytest.fixture
def mock_llm() -> MockLLMProvider:
    return MockLLMProvider()


@pytest.fixture
def mock_embedder() -> MockEmbeddingProvider:
    return MockEmbeddingProvider()
