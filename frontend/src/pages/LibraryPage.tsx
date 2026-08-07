import { useEffect, useRef, useState } from "react";
import { arxivAbsUrl, getPapers, PaperOut } from "../api";
import { Icon } from "../components/Icon";

const PAGE_SIZE = 50;

function formatAuthors(authors: string[]): string {
  if (authors.length === 0) return "Unknown authors";
  if (authors.length <= 3) return authors.join(", ");
  return `${authors.slice(0, 3).join(", ")} +${authors.length - 3} more`;
}

function formatYear(published: string): string {
  return published.slice(0, 4);
}

function EmbedDot({ embedded, total }: { embedded: number; total: number }) {
  if (total === 0) return null;
  const color =
    embedded === 0
      ? "bg-outline"
      : embedded < total
        ? "bg-warn-fg"
        : "bg-verify-fg";
  const label =
    embedded === 0
      ? "Not embedded"
      : embedded < total
        ? `${embedded}/${total} embedded`
        : "Fully embedded";
  return (
    <span title={label} className={`inline-block w-2 h-2 rounded-full ${color} shrink-0`} />
  );
}

function PaperCard({ paper }: { paper: PaperOut }) {
  const year = formatYear(paper.published);
  const authors = formatAuthors(paper.authors);
  const isFullyEmbedded = paper.embedded_count === paper.passage_count && paper.passage_count > 0;

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 hover:border-primary/40 transition-colors group">
      <div className="flex items-start justify-between gap-4 mb-1.5">
        <a
          href={arxivAbsUrl(paper.id)}
          target="_blank"
          rel="noreferrer"
          className="font-headline-lg text-[16px] font-semibold text-on-surface leading-snug group-hover:text-primary transition-colors flex-1 min-w-0"
        >
          {paper.title}
        </a>
        <span className="font-ui-label-sm text-ui-label-sm text-on-surface-variant shrink-0 mt-0.5">
          {year}
        </span>
      </div>

      <p className="font-ui-label-md text-ui-label-sm text-on-surface-variant mb-3 truncate">
        {authors}
        <span className="mx-2 opacity-40">·</span>
        <a
          href={arxivAbsUrl(paper.id)}
          target="_blank"
          rel="noreferrer"
          className="text-primary hover:underline inline-flex items-center gap-0.5"
        >
          {paper.id}
          <Icon name="open_in_new" className="text-[11px]" />
        </a>
      </p>

      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1 min-w-0">
          {paper.categories.slice(0, 5).map((cat) => (
            <span
              key={cat}
              className="px-1.5 py-0.5 bg-surface-variant text-on-surface-variant rounded text-[10px] font-medium font-ui-label-sm leading-none"
            >
              {cat}
            </span>
          ))}
          {paper.categories.length > 5 && (
            <span className="text-[10px] text-on-surface-variant font-ui-label-sm">
              +{paper.categories.length - 5}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0 font-ui-label-sm text-ui-label-sm text-on-surface-variant">
          <span className={isFullyEmbedded ? "text-verify-fg" : ""}>
            {paper.passage_count} {paper.passage_count === 1 ? "passage" : "passages"}
          </span>
          <EmbedDot embedded={paper.embedded_count} total={paper.passage_count} />
        </div>
      </div>
    </div>
  );
}

export function LibraryPage() {
  const [papers, setPapers] = useState<PaperOut[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [submittedSearch, setSubmittedSearch] = useState("");
  const [page, setPage] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === "visible") setRefreshKey((k) => k + 1);
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, []);

  useEffect(() => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setLoading(true);
    setError(null);

    getPapers(
      { limit: PAGE_SIZE, offset: page * PAGE_SIZE, search: submittedSearch || undefined },
      ctrl.signal,
    )
      .then((res) => {
        setPapers(res.papers);
        setTotal(res.total);
        setLoading(false);
      })
      .catch((err: Error) => {
        if (err.name === "AbortError") return;
        setError(err.message);
        setLoading(false);
      });

    return () => ctrl.abort();
  }, [page, submittedSearch, refreshKey]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    setSubmittedSearch(search);
  };

  const clearSearch = () => {
    setSearch("");
    setPage(0);
    setSubmittedSearch("");
  };

  return (
    <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-10 md:py-16 w-full">
      <header className="mb-10">
        <div className="flex items-end justify-between mb-2">
          <h1 className="font-headline-lg text-headline-lg-mobile md:text-headline-lg text-primary">
            Local Library
          </h1>
          <div className="flex items-center gap-2">
            {!loading && !error && (
              <span className="font-ui-label-sm text-ui-label-sm text-on-surface-variant">
                {total.toLocaleString()} {total === 1 ? "paper" : "papers"}
              </span>
            )}
            <button
              onClick={() => setRefreshKey((k) => k + 1)}
              title="Refresh"
              className="text-on-surface-variant hover:text-primary transition-colors"
            >
              <Icon name="refresh" className={`text-[18px] ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>
        <p className="text-on-surface-variant font-article-body text-article-body">
          Browse and manage your ingested research corpus.
        </p>
      </header>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-8">
        <div className="relative flex-1">
          <Icon
            name="search"
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant pointer-events-none"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title…"
            className="w-full pl-10 pr-10 py-2.5 border border-outline-variant rounded bg-surface-container-lowest font-ui-label-md text-ui-label-md text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:border-primary transition-colors"
          />
          {search && (
            <button
              type="button"
              onClick={clearSearch}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface"
            >
              <Icon name="close" className="text-[16px]" />
            </button>
          )}
        </div>
        <button
          type="submit"
          className="bg-primary text-on-primary font-ui-label-md text-ui-label-md px-5 py-2.5 rounded hover:opacity-90 transition-opacity"
        >
          Search
        </button>
      </form>

      {/* Content */}
      {error && (
        <div className="border border-error/30 bg-error/5 rounded-lg p-6 text-center">
          <p className="font-ui-label-md text-ui-label-md text-error">{error}</p>
        </div>
      )}

      {loading && (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="border border-outline-variant rounded-lg p-5 animate-pulse">
              <div className="h-4 bg-surface-variant rounded w-3/4 mb-3" />
              <div className="h-3 bg-surface-variant rounded w-1/2 mb-4" />
              <div className="flex gap-2">
                <div className="h-3 bg-surface-variant rounded w-12" />
                <div className="h-3 bg-surface-variant rounded w-12" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && !error && papers.length === 0 && (
        <div className="border border-dashed border-outline-variant rounded-xl p-12 flex flex-col items-center text-center">
          <Icon name="menu_book" className="text-[40px] text-outline mb-4" />
          {submittedSearch ? (
            <>
              <h2 className="font-headline-lg text-[18px] text-on-surface mb-1">No results</h2>
              <p className="font-ui-label-md text-ui-label-sm text-on-surface-variant mb-4">
                No papers match "{submittedSearch}"
              </p>
              <button onClick={clearSearch} className="font-ui-label-md text-ui-label-md text-primary hover:underline">
                Clear search
              </button>
            </>
          ) : (
            <>
              <h2 className="font-headline-lg text-[18px] text-on-surface mb-1">No papers yet</h2>
              <p className="font-ui-label-md text-ui-label-sm text-on-surface-variant">
                Ingest papers from the Ingest page to populate your library.
              </p>
            </>
          )}
        </div>
      )}

      {!loading && !error && papers.length > 0 && (
        <>
          <div className="flex flex-col gap-3 mb-8">
            {papers.map((paper) => (
              <PaperCard key={paper.id} paper={paper} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-outline/10 pt-6">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="flex items-center gap-1 font-ui-label-md text-ui-label-md text-on-surface-variant hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <Icon name="chevron_left" className="text-[18px]" />
                Previous
              </button>
              <span className="font-ui-label-sm text-ui-label-sm text-on-surface-variant">
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="flex items-center gap-1 font-ui-label-md text-ui-label-md text-on-surface-variant hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next
                <Icon name="chevron_right" className="text-[18px]" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
