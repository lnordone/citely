"""API route behaviour with the retrieval/DB layers faked out.

These build a bare app and mount the routers directly, so the real lifespan (which needs
Postgres, an embedding model and a cross-encoder) never runs. What's under test is the
routing, serialization and SSE framing.
"""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from citely.api import app as app_mod
from citely.api.deps import AppState
from citely.api.routes import health, models, papers, review, search
from citely.config import Config
from citely.db.session import get_session
from citely.retrieval.types import Claim, PaperRef, RetrievalResult, RetrievedPassage
from tests.conftest import MockEmbeddingProvider, MockLLMProvider
from tests.test_deps import StubIndex, StubReranker


def _passage(n: int, key: str) -> RetrievedPassage:
    return RetrievedPassage(
        passage_id=f"2401.{n}::0",
        paper_id=f"2401.{n}",
        text=f"passage text {n}",
        score=1.0 / n,
        source_key=key,
        paper=PaperRef(
            paper_id=f"2401.{n}", title=f"Title {n}", authors=["A"], year=2024, url="u"
        ),
    )


SOURCES = [_passage(1, "S1"), _passage(2, "S2"), _passage(3, "S3")]


class StubRetriever:
    def __init__(self, passages: list[RetrievedPassage]) -> None:
        self.passages = passages
        self.queries: list[str] = []

    async def retrieve(self, query: str) -> RetrievalResult:
        self.queries.append(query)
        return RetrievalResult(query=query, passages=self.passages)


class StubSession:
    """Stands in for the request-scoped AsyncSession (only /health touches it)."""

    async def execute(self, *_a: object, **_kw: object) -> None:
        return None


@pytest.fixture
def state() -> AppState:
    return AppState(
        cfg=Config(),
        llm=MockLLMProvider(model="default-model"),
        embedder=MockEmbeddingProvider(),
        reranker=StubReranker(),  # type: ignore[arg-type]
        bm25_index=StubIndex(),  # type: ignore[arg-type]
        constructor=object(),  # type: ignore[arg-type]
    )


@pytest.fixture
def client(state: AppState, monkeypatch) -> TestClient:
    app = FastAPI()
    for module in (health, models, papers, review, search):
        app.include_router(module.router)
    app.state.citely = state

    async def fake_session():
        yield StubSession()

    app.dependency_overrides[get_session] = fake_session

    retriever = StubRetriever(SOURCES)
    # Record the LLM each route resolved, so the model override is observable.
    seen: dict = {"llm": [], "retriever": retriever}

    def fake_make_retriever(_state, _session, llm=None):
        seen["llm"].append(llm)
        return retriever

    monkeypatch.setattr(search, "make_retriever", fake_make_retriever)
    monkeypatch.setattr(review, "make_retriever", fake_make_retriever)

    test_client = TestClient(app)
    test_client.seen = seen  # type: ignore[attr-defined]
    return test_client


def _sse_events(body: str) -> list[tuple[str, dict]]:
    """Parse an SSE body into (event, payload) pairs."""
    out: list[tuple[str, dict]] = []
    for raw in body.replace("\r\n", "\n").split("\n\n"):
        if not raw.strip():
            continue
        name, data = "message", []
        for line in raw.split("\n"):
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].lstrip())
        if data:
            out.append((name, json.loads("\n".join(data))))
    return out


# --- /health ---------------------------------------------------------------------


def test_health_reports_the_active_models(client: TestClient):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["llm_model"] == "default-model"
    assert body["embedding_model"] == "mock-embed"


def test_health_degrades_instead_of_raising_when_the_db_is_down(client: TestClient):
    class BrokenSession:
        async def execute(self, *_a: object, **_kw: object) -> None:
            raise RuntimeError("db is gone")

    async def broken():
        yield BrokenSession()

    client.app.dependency_overrides[get_session] = broken
    body = client.get("/health").json()
    assert body["status"] == "degraded"


# --- /search ---------------------------------------------------------------------


def test_search_returns_citation_keyed_sources(client: TestClient):
    body = client.post("/search", json={"query": "attention"}).json()
    assert body["query"] == "attention"
    assert [s["source_key"] for s in body["sources"]] == ["S1", "S2", "S3"]
    assert body["sources"][0]["title"] == "Title 1"
    assert body["sources"][0]["paper_id"] == "2401.1"


def test_search_top_k_truncates(client: TestClient):
    body = client.post("/search", json={"query": "q", "top_k": 2}).json()
    assert len(body["sources"]) == 2


def test_search_without_model_uses_the_shared_llm(client: TestClient):
    client.post("/search", json={"query": "q"})
    assert client.seen["llm"][0].model_name == "default-model"


def test_search_honours_the_model_override(client: TestClient):
    client.post("/search", json={"query": "q", "model": "qwen2.5:14b"})
    assert client.seen["llm"][0].model_name == "qwen2.5:14b"


# --- /review ---------------------------------------------------------------------


@pytest.fixture
def stub_generation(monkeypatch):
    """Reviewer emits two claims; verifier marks the first supported."""

    class StubReviewer:
        def __init__(self, llm, cfg):
            self.llm = llm

        async def generate(self, query, sources):
            yield Claim(text="First claim.", source_ids=["S1"])
            yield Claim(text="Second claim.", source_ids=["S2", "S3"])

    class StubVerifier:
        def __init__(self, llm, enabled=True):
            pass

        async def verify(self, claim, sources):
            claim.supported = claim.source_ids == ["S1"]
            return claim

    monkeypatch.setattr(review, "ReviewGenerator", StubReviewer)
    monkeypatch.setattr(review, "ClaimVerifier", StubVerifier)


def test_review_emits_sources_before_any_claim(client: TestClient, stub_generation):
    events = _sse_events(client.post("/review", json={"query": "q"}).text)
    names = [name for name, _ in events]
    assert names[0] == "sources"
    assert names[-1] == "done"
    assert names.count("claim") == 2


def test_review_source_keys_match_the_streamed_sources(client: TestClient, stub_generation):
    """The whole point of the sources event: every cited key resolves within it."""
    events = _sse_events(client.post("/review", json={"query": "q"}).text)
    payload = dict(events)["sources"]
    available = {s["source_key"] for s in payload["sources"]}
    cited = {sid for name, data in events if name == "claim" for sid in data["source_ids"]}
    assert cited <= available


def test_review_sources_event_matches_the_search_shape(client: TestClient, stub_generation):
    """A client must be able to reuse one SourceOut type for both endpoints."""
    from_search = client.post("/search", json={"query": "q"}).json()["sources"]
    events = _sse_events(client.post("/review", json={"query": "q"}).text)
    from_review = dict(events)["sources"]["sources"]
    assert [sorted(s) for s in from_search] == [sorted(s) for s in from_review]
    assert from_search == from_review


def test_review_streams_verification_verdicts(client: TestClient, stub_generation):
    events = _sse_events(client.post("/review", json={"query": "q"}).text)
    claims = [data for name, data in events if name == "claim"]
    assert claims[0]["supported"] is True
    assert claims[1]["supported"] is False


def test_review_done_carries_rendered_markdown(client: TestClient, stub_generation):
    events = _sse_events(client.post("/review", json={"query": "q"}).text)
    done = dict(events)["done"]
    assert done["num_claims"] == 2
    assert "[S1]" in done["markdown"]
    assert "## Sources" in done["markdown"]


def test_review_honours_the_model_override(client: TestClient, stub_generation):
    client.post("/review", json={"query": "q", "model": "qwen2.5:14b"})
    assert client.seen["llm"][0].model_name == "qwen2.5:14b"


# --- /papers ---------------------------------------------------------------------


@pytest.fixture
def paper_rows(monkeypatch):
    from datetime import date, datetime

    class Row:
        def __init__(self, i: int) -> None:
            self.id = f"2401.{i}"
            self.title = f"Paper {i}"
            self.authors = ["A"]
            self.categories = ["cs.LG"]
            self.published = date(2024, 1, 2)
            self.pdf_url = "u"
            self.ingested_at = datetime(2024, 1, 3, 12, 0, 0)

    captured: dict = {}

    class FakeRepo:
        def __init__(self, session): ...

        async def list_with_counts(self, limit=50, offset=0, search=None):
            captured.update(limit=limit, offset=offset, search=search)
            return [(Row(1), 4, 4), (Row(2), 3, 0)], 2

    monkeypatch.setattr(papers, "PaperRepository", FakeRepo)
    return captured


def test_papers_lists_with_passage_and_embedding_counts(client: TestClient, paper_rows):
    body = client.get("/papers").json()
    assert body["total"] == 2
    assert body["papers"][0]["passage_count"] == 4
    assert body["papers"][0]["embedded_count"] == 4
    assert body["papers"][1]["embedded_count"] == 0
    assert body["papers"][0]["published"] == "2024-01-02"


def test_papers_forwards_pagination_and_search(client: TestClient, paper_rows):
    client.get("/papers", params={"limit": 10, "offset": 30, "search": "transformer"})
    assert paper_rows == {"limit": 10, "offset": 30, "search": "transformer"}


def test_papers_treats_blank_search_as_no_filter(client: TestClient, paper_rows):
    client.get("/papers", params={"search": ""})
    assert paper_rows["search"] is None


def test_papers_rejects_an_out_of_range_limit(client: TestClient, paper_rows):
    assert client.get("/papers", params={"limit": 5000}).status_code == 422
    assert client.get("/papers", params={"offset": -1}).status_code == 422


# --- /models ---------------------------------------------------------------------


def test_models_is_registered_on_the_real_app():
    """Regression: the router existed but was never mounted, so /models 404'd."""
    paths = {r.path for r in app_mod.create_app().routes}
    assert {"/health", "/ingest", "/models", "/papers", "/search", "/review"} <= paths


def test_models_reports_that_listing_is_ollama_only(client: TestClient, state: AppState):
    state.cfg = Config(provider="openai")
    body = client.get("/models").json()
    assert body["provider"] == "openai"
    assert body["installed"] == []
    assert "ollama" in body["error"]


def test_models_surfaces_a_transport_failure_without_crashing(client: TestClient, monkeypatch):
    class BoomClient:
        def __init__(self, **_kw): ...
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a):
            return False

        async def get(self, _url):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(models.httpx, "AsyncClient", BoomClient)
    body = client.get("/models").json()
    assert body["installed"] == []
    assert "connection refused" in body["error"]
    assert body["default"] == "default-model"
