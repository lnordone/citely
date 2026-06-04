"""Pydantic request/response models for the API.

# TODO(phase 8): expand fields as routes are implemented.
"""

from __future__ import annotations

from pydantic import BaseModel


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


class ModelsResponse(BaseModel):
    provider: str
    default: str
    installed: list[str] = []
    error: str | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = None
    model: str | None = None  # override the LLM used for query construction (ollama only)


class SourceOut(BaseModel):
    source_key: str
    passage_id: str
    paper_id: str
    title: str | None = None
    text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    sources: list[SourceOut]


class ReviewRequest(BaseModel):
    query: str
    model: str | None = None  # override the LLM for construction/review/verify (ollama only)
