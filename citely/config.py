"""Typed loader + validation for ``config.yaml``.

The single source of runtime config. Every module reads its settings from the typed
``Config`` object returned by :func:`load_config`; nothing is hardcoded.

We use pydantic for validation so a malformed config fails loud at startup rather than
deep inside a pipeline. Enums constrain the string-y switches (provider, methods, ...).
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_CONFIG_PATH = Path(
    os.environ.get("CITELY_CONFIG", Path(__file__).resolve().parent.parent / "config.yaml")
)


class LLMProviderKind(str, Enum):
    ollama = "ollama"
    openai = "openai"
    anthropic = "anthropic"


class EmbeddingProviderKind(str, Enum):
    local = "local"
    ollama = "ollama"
    openai = "openai"


class VectorIndexKind(str, Enum):
    flat = "flat"
    hnsw = "hnsw"


class QuantizationKind(str, Enum):
    none = "none"
    int8 = "int8"
    binary = "binary"


class TranslationMethod(str, Enum):
    none = "none"
    multi_query = "multi_query"
    hyde = "hyde"
    decompose = "decompose"


class RouterKind(str, Enum):
    none = "none"


class FilterOrder(str, Enum):
    pre = "pre"
    post = "post"


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelsConfig(_Base):
    ollama_llm: str = "qwen2.5:7b"
    ollama_embed: str = "nomic-embed-text"
    local_embed: str = "BAAI/bge-base-en-v1.5"
    reranker: str = "BAAI/bge-reranker-base"
    openai_llm: str = "gpt-4o-mini"
    anthropic_llm: str = "claude-3-5-sonnet-latest"
    # ADDED (flagged): embedding model for the OpenAI embedding provider path.
    openai_embed: str = "text-embedding-3-small"
    num_ctx: int = 8192  # MUST set explicitly or Ollama defaults to 2048


class IngestConfig(_Base):
    categories: list[str] = Field(default_factory=lambda: ["cs.AI", "cs.LG", "cs.CL"])
    max_papers: int = 50000
    chunk_tokens: int = 256
    chunk_overlap: int = 32

    @field_validator("chunk_overlap")
    @classmethod
    def _overlap_lt_tokens(cls, v: int, info: Any) -> int:
        tokens = info.data.get("chunk_tokens", 256)
        if v >= tokens:
            raise ValueError("chunk_overlap must be smaller than chunk_tokens")
        return v


class HNSWConfig(_Base):
    m: int = 16
    ef_construction: int = 200
    ef_search: int = 64


class IndexingConfig(_Base):
    vector_index: VectorIndexKind = VectorIndexKind.flat
    quantization: QuantizationKind = QuantizationKind.int8
    hnsw: HNSWConfig = Field(default_factory=HNSWConfig)


class TranslationConfig(_Base):
    method: TranslationMethod = TranslationMethod.multi_query
    num_variants: int = 4


class QueryConfig(_Base):
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    extract_metadata: bool = True
    router: RouterKind = RouterKind.none


class RetrievalConfig(_Base):
    bm25_top_n: int = 200
    dense_top_n: int = 200
    rrf_k: int = 60
    rerank_candidates: int = 50
    final_k: int = 8
    filter_order: FilterOrder = FilterOrder.pre


class GenerationConfig(_Base):
    verify_claims: bool = True
    temperature: float = 0.2
    max_tokens: int = 2048


class DBConfig(_Base):
    url: str = "postgresql+asyncpg://citely:citely@localhost:5432/scholarrag"


class APIConfig(_Base):
    host: str = "0.0.0.0"
    port: int = 8000


class ProvidersConfig(_Base):
    """ADDED (flagged): transport-level provider settings (hosts/timeouts).

    The blueprint config schema did not include endpoints; these are required to point
    providers at Ollama / a custom OpenAI base URL without hardcoding. API *keys* still
    come from the environment, never from config.
    """

    ollama_host: str = "http://localhost:11434"
    openai_base_url: str | None = None
    request_timeout_s: float = 120.0


class Config(_Base):
    provider: LLMProviderKind = LLMProviderKind.ollama
    embedding_provider: EmbeddingProviderKind = EmbeddingProviderKind.local
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    ingest: IngestConfig = Field(default_factory=IngestConfig)
    indexing: IndexingConfig = Field(default_factory=IndexingConfig)
    query: QueryConfig = Field(default_factory=QueryConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    db: DBConfig = Field(default_factory=DBConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Apply a small set of environment overrides (used by docker-compose)."""
    db_url = os.environ.get("CITELY_DB_URL")
    if db_url:
        data.setdefault("db", {})
        data["db"]["url"] = db_url
    ollama_host = os.environ.get("OLLAMA_HOST")
    if ollama_host:
        data.setdefault("providers", {})
        data["providers"]["ollama_host"] = ollama_host
    return data


def load_config(path: str | Path | None = None) -> Config:
    """Load and validate ``config.yaml`` into a typed :class:`Config`.

    Raises ``FileNotFoundError`` if the file is missing and ``pydantic.ValidationError``
    on a malformed config (extra keys, wrong types, invalid enum values).
    """
    cfg_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"config not found at {cfg_path}. Copy config.example.yaml -> config.yaml "
            "or set CITELY_CONFIG."
        )
    with cfg_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"config root must be a mapping, got {type(raw).__name__}")
    raw = _apply_env_overrides(raw)
    return Config.model_validate(raw)


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Process-wide cached config (convenience for DI; tests can call load_config)."""
    return load_config()
