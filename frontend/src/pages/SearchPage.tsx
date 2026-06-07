import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { search as apiSearch, arxivAbsUrl, SourceOut } from "../api";
import { maxScore, relevanceFraction } from "../lib/relevance";
import { Icon } from "../components/Icon";
import { RelevanceBar } from "../components/RelevanceBar";

export function SearchPage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [sources, setSources] = useState<SourceOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [ran, setRan] = useState(false);

  const top = maxScore(sources);

  const runSearch = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setSelected(new Set());
    try {
      const res = await apiSearch(q.trim());
      setSources(res.sources);
      setRan(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <div className="flex flex-col min-h-screen">
      {/* Search header */}
      <div className="w-full px-margin-mobile md:px-margin-desktop pt-10 md:pt-margin-desktop pb-8 border-b border-outline-variant/30 bg-surface/95 backdrop-blur-sm sticky top-0 z-30">
        <div className="max-w-container-max mx-auto">
          <div className="relative group">
            <Icon
              name="search"
              className="absolute left-0 top-1/2 -translate-y-1/2 text-outline-variant group-focus-within:text-primary transition-colors text-[32px]"
            />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runSearch(query)}
              placeholder="Search ingested arXiv passages…"
              className="w-full pl-12 pr-4 py-4 bg-transparent border-b border-outline-variant focus:border-primary font-headline-lg text-headline-lg text-on-surface placeholder:text-outline-variant transition-colors outline-none"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3 mt-6">
            {/* NOTE(pending-backend): filters are auto-extracted server-side and not yet
                accepted as explicit /search params. These chips are display-only. */}
            <div className="flex items-center gap-2 border border-outline-variant/50 rounded-full px-3 py-1.5 text-on-surface-variant/60" title="Pending backend: explicit filters not yet supported">
              <Icon name="filter_list" className="text-[16px]" />
              <span className="font-ui-label-sm text-ui-label-sm">Filters (auto)</span>
            </div>
            <div className="flex items-center gap-2 border border-outline-variant/50 rounded-full px-3 py-1.5 text-on-surface-variant/60" title="Pending backend: sort is fixed to relevance">
              <Icon name="sort" className="text-[16px]" />
              <span className="font-ui-label-sm text-ui-label-sm">Sort: Relevance</span>
            </div>
            <div className="ml-auto text-on-surface-variant font-ui-label-sm text-ui-label-sm">
              {ran ? `${sources.length} passages` : "Enter a query"}
            </div>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="w-full px-margin-mobile md:px-margin-desktop py-8 flex-1">
        <div className="max-w-article-width mx-auto flex flex-col gap-6">
          {loading && (
            <div className="flex items-center gap-2 text-on-surface-variant font-ui-label-md text-ui-label-md">
              <Icon name="progress_activity" className="animate-spin" /> Searching…
            </div>
          )}
          {error && (
            <div className="flex items-center gap-2 text-error font-ui-label-md text-ui-label-md bg-error-container/40 border border-error/20 rounded-lg p-4">
              <Icon name="error" className="text-[18px]" />
              {error}
            </div>
          )}
          {ran && !loading && sources.length === 0 && !error && (
            <p className="font-ui-label-md text-ui-label-md text-on-surface-variant">
              No passages matched. Ingest more papers or broaden the query.
            </p>
          )}

          {sources.map((s) => (
            <article
              key={s.passage_id}
              className="group border border-outline/10 bg-surface rounded p-6 hover:bg-surface-container-low transition-colors"
            >
              <div className="flex items-start gap-4">
                <input
                  type="checkbox"
                  className="academic-checkbox mt-1"
                  checked={selected.has(s.passage_id)}
                  onChange={() => toggle(s.passage_id)}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-3 mb-2">
                    <span className="bg-surface-container-high text-on-surface font-citation-caps text-citation-caps px-1.5 py-0.5 rounded-sm">
                      {s.source_key}
                    </span>
                    <h2 className="font-headline-lg-mobile text-headline-lg-mobile text-on-surface leading-snug group-hover:text-primary transition-colors">
                      {s.title ?? s.paper_id}
                    </h2>
                  </div>
                  <div className="flex items-center flex-wrap gap-x-4 gap-y-1 mb-4 font-ui-label-sm text-ui-label-sm text-on-surface-variant">
                    <a
                      href={arxivAbsUrl(s.paper_id)}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 text-primary hover:underline"
                    >
                      <Icon name="open_in_new" className="text-[14px]" /> arXiv:{s.paper_id}
                    </a>
                    <span className="w-1 h-1 rounded-full bg-outline-variant" />
                    <RelevanceBar fraction={relevanceFraction(s.score, top)} />
                  </div>
                  <p className="font-article-body text-on-surface-variant line-clamp-3 text-[16px]">
                    {s.text}
                  </p>
                </div>
              </div>
            </article>
          ))}
          <div className="h-24" />
        </div>
      </div>

      {/* Sticky action bar */}
      {selected.size > 0 && (
        <div className="fixed bottom-20 md:bottom-8 left-1/2 -translate-x-1/2 z-50 animate-fade-in-up">
          <div className="bg-inverse-surface text-inverse-on-surface shadow-[0_4px_40px_rgba(0,0,0,0.15)] rounded-full px-6 py-3 flex items-center gap-6 border border-outline/20">
            <div className="font-ui-label-md text-ui-label-md">
              <span className="font-semibold">{selected.size}</span> selected
            </div>
            <div className="w-px h-6 bg-outline-variant/30" />
            {/* NOTE(pending-backend): /review synthesizes from a query, not a chosen paper
                set. We carry the query forward; per-paper review needs backend support. */}
            <button
              onClick={() => navigate(`/review?q=${encodeURIComponent(query.trim())}`)}
              className="bg-primary text-on-primary font-ui-label-md text-ui-label-md px-5 py-2 rounded hover:bg-primary-container transition-colors flex items-center gap-2"
            >
              <Icon name="play_arrow" className="text-[18px]" />
              Start Review
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
