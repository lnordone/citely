"""Retrieval & generation DTOs. Pure data, no logic — safe to import anywhere."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class QueryFilters:
    date_after: date | None = None
    categories: list[str] | None = None
    authors: list[str] | None = None

    def is_empty(self) -> bool:
        return not (self.date_after or self.categories or self.authors)


@dataclass
class ConstructedQuery:
    original: str
    bm25_query: str  # original/keyword query -> sparse leg
    dense_queries: list[str] = field(default_factory=list)  # translated variants -> dense leg
    filters: QueryFilters = field(default_factory=QueryFilters)


@dataclass
class PaperRef:
    paper_id: str
    title: str
    authors: list[str]
    year: int | None
    url: str


@dataclass
class RetrievedPassage:
    passage_id: str
    paper_id: str
    text: str
    score: float
    source_key: str = ""  # e.g. "S1" — assigned for citation labeling
    paper: PaperRef | None = None  # title/authors/year/url for rendering


@dataclass
class RetrievalResult:
    query: str
    passages: list[RetrievedPassage] = field(default_factory=list)


@dataclass
class Claim:
    text: str
    source_ids: list[str]  # the [S?] keys this claim is grounded in
    supported: bool | None = None  # filled by the verifier
