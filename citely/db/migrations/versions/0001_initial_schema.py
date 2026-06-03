"""initial schema: pgvector extension, papers, passages, indexes

Revision ID: 0001
Revises:
Create Date: 2026-06-03

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Snapshot of citely.db.models.EMBEDDING_DIM at the time of this migration. Migrations
# are intentionally static; if the embedding model changes, add a new migration.
EMBEDDING_DIM = 768


def upgrade() -> None:
    # pgvector must exist before any table declares a Vector column.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "papers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", sa.JSON(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=False),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("published", sa.Date(), nullable=False),
        sa.Column("pdf_url", sa.String(), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "passages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "paper_id",
            sa.String(),
            sa.ForeignKey("papers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("embedding_i8", sa.LargeBinary(), nullable=True),
    )

    # Parent link is queried on every citation hydrate.
    op.create_index("ix_passages_paper_id", "passages", ["paper_id"])
    # Date filtering (published-range queries).
    op.create_index("ix_papers_published", "papers", ["published"])
    # Category containment pre-filter. categories is JSON; cast to jsonb (an IMMUTABLE
    # cast) so a GIN index supports `categories::jsonb @> '["cs.AI"]'`.
    op.execute(
        "CREATE INDEX ix_papers_categories_gin ON papers "
        "USING gin ((categories::jsonb) jsonb_path_ops)"
    )
    # Dense ANN index (cosine). IVFFlat is the MVP choice; an HNSW migration can replace
    # it later using config.indexing.hnsw parameters.
    op.execute(
        "CREATE INDEX ix_passages_embedding_ivfflat ON passages "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_passages_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_papers_categories_gin")
    op.drop_index("ix_papers_published", table_name="papers")
    op.drop_index("ix_passages_paper_id", table_name="passages")
    op.drop_table("passages")
    op.drop_table("papers")
    # The vector extension is intentionally left installed.
