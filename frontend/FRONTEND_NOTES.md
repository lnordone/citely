# Citely frontend — notes

React + Vite + TypeScript + Tailwind. Routes: `/review` (workspace, default), `/search`,
`/ingest`, `/library`. In dev, Vite proxies `/health`, `/search`, `/review`, `/ingest` to
`http://localhost:8000` (see `vite.config.ts`).

```bash
cd frontend
npm install
npm run dev      # start backend first: make serve (or docker compose up)
```

## Wired to the backend today
- **/review** workspace: `POST /search` (sources panel) + `POST /review` SSE (streamed
  claims, per-claim verification badges, inline `[S?]` citation chips with source hover
  cards, bibliography, copy-as-markdown, stop/abort). SSE framing is parsed properly.
- **/search**: `POST /search` ranked passages with relevance bars + arXiv links.
- **/ingest**: `POST /ingest` (categories + max papers) and `GET /health` for backend status.
- Live `GET /health` status chip (LLM + embedding model names).

## Pending backend (UI is built/stubbed; flagged in code with `NOTE(pending-backend)`)
1. **Rich source metadata** — `SourceOut` lacks `authors`, `year`, `url`, `venue`. Cards
   derive the arXiv URL from `paper_id` and omit authors/year. Expose `PaperRef` fields on
   `SourceOut` to complete source cards and the bibliography.
2. **Structured citations in the stream** — `claim`/`done` give `source_ids` + final
   markdown only. Chips currently join `source_ids` against `/search` results by
   `source_key`. A `sources` SSE event (or `sources` in `done`) would decouple them.
3. **Multi-turn / follow-ups** — backend is single-shot (no conversation state).
4. **Explicit filters** — date/category are auto-extracted server-side; `/search` and
   `/review` don't accept explicit filters. Search filter chips are display-only.
5. **Per-paper review** — `/review` synthesizes from a query, not a selected paper set; the
   Search page carries the query forward instead.
6. **Ingestion progress** — `/ingest` is synchronous (final counts only); no live progress.
7. **Library / corpus browsing** — no `GET /papers` listing endpoint, so `/library` is a
   placeholder.
8. **Export** (BibTeX/PDF) and **persisted history** — not yet backed by endpoints.
