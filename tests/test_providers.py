"""Provider interface conformance with MOCKED clients (no network).

Also covers the shared structured-output repair helpers, which are the backbone of
``generate_json`` for providers without strict JSON modes.
"""

from __future__ import annotations

import pytest

from citely.providers.base import (
    EmbeddingProvider,
    LLMProvider,
    Message,
    extract_json_object,
    strip_code_fences,
    try_parse_json,
)
from tests.conftest import MockEmbeddingProvider, MockLLMProvider


def test_mock_llm_is_a_provider(mock_llm: MockLLMProvider) -> None:
    assert isinstance(mock_llm, LLMProvider)
    assert mock_llm.model_name == "mock-llm"


def test_mock_embedder_is_a_provider(mock_embedder: MockEmbeddingProvider) -> None:
    assert isinstance(mock_embedder, EmbeddingProvider)
    assert mock_embedder.dimension == 8


async def test_generate_returns_str(mock_llm: MockLLMProvider) -> None:
    out = await mock_llm.generate([Message("user", "hi")])
    assert isinstance(out, str)


async def test_stream_yields_deltas(mock_llm: MockLLMProvider) -> None:
    chunks = [c async for c in mock_llm.stream([Message("user", "hi there")])]
    assert chunks
    assert "".join(chunks).strip() == "mock reply"


async def test_generate_json_returns_dict(mock_llm: MockLLMProvider) -> None:
    out = await mock_llm.generate_json([Message("user", "x")], schema={"type": "object"})
    assert isinstance(out, dict)


async def test_embed_preserves_order_and_dim(mock_embedder: MockEmbeddingProvider) -> None:
    texts = ["alpha", "beta", "gamma"]
    vecs = await mock_embedder.embed(texts)
    assert len(vecs) == len(texts)
    assert all(len(v) == mock_embedder.dimension for v in vecs)
    # Deterministic + order-preserving: same input -> same vector.
    again = await mock_embedder.embed(["beta"])
    assert again[0] == vecs[1]


async def test_embed_empty_input(mock_embedder: MockEmbeddingProvider) -> None:
    assert await mock_embedder.embed([]) == []


@pytest.mark.parametrize(
    "raw",
    [
        '{"a": 1}',
        '```json\n{"a": 1}\n```',
        '```\n{"a": 1}\n```',
        'here is your answer:\n{"a": 1}\nthanks',
    ],
)
def test_try_parse_json_variants(raw: str) -> None:
    parsed = try_parse_json(raw)
    assert parsed == {"a": 1}


def test_try_parse_json_unparseable() -> None:
    assert try_parse_json("not json at all") is None


def test_strip_code_fences() -> None:
    assert strip_code_fences('```json\n{"x":1}\n```') == '{"x":1}'


def test_extract_balanced_object() -> None:
    raw = 'noise {"a": {"b": 2}} trailing }'
    assert extract_json_object(raw) == '{"a": {"b": 2}}'
