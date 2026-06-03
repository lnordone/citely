# Migrations

# TODO(phase 2): alembic (or raw SQL) migrations.

Must include:
- `CREATE EXTENSION IF NOT EXISTS vector;`
- `papers` and `passages` tables (see `citely/db/models.py`).
- pgvector index on `passages.embedding` (flat/IVFFlat for MVP; HNSW migration later,
  parameters from `config.indexing.hnsw`).
- btree index on `papers.published` (date filtering).
- GIN / expression index supporting category filtering (the pre-filter path).
