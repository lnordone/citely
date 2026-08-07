"""Pydantic request/response models for the API."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from citely.retrieval.types import RetrievedPassage


class HealthResponse(BaseModel):
    status: str = "ok"
    llm_model: str | None = None
    embedding_model: str | None = None


class IngestRequest(BaseModel):
    categories: list[str] | None = None
    max_papers: int | None = None


class IngestResponse(BaseModel):
    papers_stored: int
    passages_stored: int
    passages_embedded: int = 0


class ModelsResponse(BaseModel):
    provider: str
    default: str
    installed: list[str] = []
    error: str | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = None
    model: str | None = None  # override the LLM used for query construction


class SourceOut(BaseModel):
    source_key: str
    passage_id: str
    paper_id: str
    title: str | None = None
    text: str
    score: float


def to_sources_out(passages: list[RetrievedPassage]) -> list[SourceOut]:
    """Project retrieved passages onto the wire format.

    Shared by ``/search`` and ``/review``'s ``sources`` event so the two describe a
    source identically — the citation keys are only comparable if the shape is.
    """
    return [
        SourceOut(
            source_key=p.source_key,
            passage_id=p.passage_id,
            paper_id=p.paper_id,
            title=p.paper.title if p.paper else None,
            text=p.text,
            score=p.score,
        )
        for p in passages
    ]


class SearchResponse(BaseModel):
    query: str
    sources: list[SourceOut]


class ReviewRequest(BaseModel):
    query: str
    model: str | None = None  # override the LLM for construction/review/verify


class PaperOut(BaseModel):
    id: str
    title: str
    authors: list[str]
    categories: list[str]
    published: date
    pdf_url: str
    ingested_at: datetime
    passage_count: int
    embedded_count: int


class PapersResponse(BaseModel):
    papers: list[PaperOut]
    total: int
