"""drop ivfflat index: honor the `flat` (exact) vector_index default

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-03

The initial schema created an IVFFlat ANN index unconditionally, but the default
``config.indexing.vector_index`` is ``flat`` (exact cosine scan). On small / early
datasets IVFFlat is also actively harmful: with ``lists = 100`` and ``probes = 1`` a
query probes a single near-empty cluster and returns far fewer rows than ``LIMIT``
requests (the planner uses the ANN index for small limits, an exact scan for large
ones — so results silently depend on ``top_n``).

Dropping the index makes dense search exact and correct for the default config. An
approximate index (IVFFlat or HNSW, sized from ``config.indexing.hnsw`` /
``lists ~= rows/1000``) should be (re)introduced in its own migration once the corpus
is large enough to benefit.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_passages_embedding_ivfflat")


def downgrade() -> None:
    op.execute(
        "CREATE INDEX ix_passages_embedding_ivfflat ON passages "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
