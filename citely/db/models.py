"""SQLAlchemy ORM models: Paper and Passage.

Declarations only (no business logic). The vector column width MUST equal
``EmbeddingProvider.dimension`` — this is asserted at startup; a mismatch is a hard
error. Index DDL (pgvector flat/IVFFlat/HNSW, btree on published, category filtering)
lives in migrations.
"""

from __future__ import annotations

from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Must match EmbeddingProvider.dimension (bge-base-en-v1.5 == 768). Asserted at startup.
EMBEDDING_DIM = 768


class Base(DeclarativeBase):
    pass


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # arxiv id (dedup key)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    abstract: Mapped[str] = mapped_column(Text, nullable=False)
    categories: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    published: Mapped[date] = mapped_column(Date, nullable=False)
    pdf_url: Mapped[str] = mapped_column(String, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    passages: Mapped[list[Passage]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )


class Passage(Base):
    __tablename__ = "passages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    paper_id: Mapped[str] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )  # PARENT LINK — required for citations
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    # Optional int8 quantized vector (config toggle indexing.quantization).
    embedding_i8: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # BM25 lives in the SparseIndex, not a column.

    paper: Mapped[Paper] = relationship(back_populates="passages")
