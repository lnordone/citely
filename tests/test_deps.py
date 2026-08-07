"""AppState helpers: per-request model override resolution and retriever wiring."""

from __future__ import annotations

from citely.api.deps import AppState, make_retriever, resolve_llm
from citely.config import Config
from tests.conftest import MockEmbeddingProvider, MockLLMProvider


class StubReranker:
    async def rerank(self, query, passages, top_k):  # type: ignore[no-untyped-def]
        return passages[:top_k]


class StubIndex:
    def build(self, passages):  # type: ignore[no-untyped-def]
        pass

    def search(self, query, top_n):  # type: ignore[no-untyped-def]
        return []

    def save(self, path):  # type: ignore[no-untyped-def]
        pass

    def load(self, path):  # type: ignore[no-untyped-def]
        pass


def _state(cfg: Config | None = None) -> AppState:
    llm = MockLLMProvider(model="default-model")
    return AppState(
        cfg=cfg or Config(),
        llm=llm,
        embedder=MockEmbeddingProvider(),
        reranker=StubReranker(),  # type: ignore[arg-type]
        bm25_index=StubIndex(),  # type: ignore[arg-type]
        constructor=object(),  # type: ignore[arg-type]
    )


def test_no_override_returns_the_shared_singleton():
    state = _state()
    assert resolve_llm(state, None) is state.llm
    assert resolve_llm(state, "") is state.llm


def test_override_matching_the_default_reuses_the_singleton():
    state = _state()
    assert resolve_llm(state, "default-model") is state.llm
    assert state.llm_overrides == {}


def test_override_builds_a_provider_for_the_requested_model():
    state = _state()
    provider = resolve_llm(state, "qwen2.5:14b")
    assert provider is not state.llm
    assert provider.model_name == "qwen2.5:14b"


def test_override_providers_are_cached_per_model():
    state = _state()
    first = resolve_llm(state, "qwen2.5:14b")
    second = resolve_llm(state, "qwen2.5:14b")
    assert first is second
    assert list(state.llm_overrides) == ["qwen2.5:14b"]


def test_override_keeps_the_configured_provider_kind():
    """Only the model name is overridable — the provider itself is config-level."""
    state = _state(Config(provider="anthropic"))
    provider = resolve_llm(state, "claude-haiku-4-5")
    assert type(provider).__name__ == "AnthropicProvider"


def test_retriever_reuses_the_shared_constructor_by_default():
    state = _state()
    retriever = make_retriever(state, session=object())  # type: ignore[arg-type]
    assert retriever._constructor is state.constructor


def test_retriever_rebuilds_the_constructor_for_an_overridden_llm():
    """Only the query constructor depends on the LLM; everything else stays shared."""
    state = _state()
    override = resolve_llm(state, "qwen2.5:14b")
    retriever = make_retriever(state, session=object(), llm=override)  # type: ignore[arg-type]
    assert retriever._constructor is not state.constructor
    assert retriever._reranker is state.reranker
