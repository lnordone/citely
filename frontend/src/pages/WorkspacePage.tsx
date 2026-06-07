import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ReviewClaim, SourceOut } from "../api";
import { useReviewStream } from "../hooks/useReviewStream";
import { maxScore, relevanceFraction } from "../lib/relevance";
import { Icon } from "../components/Icon";
import { CitationChip } from "../components/CitationChip";
import { SourceCard } from "../components/SourceCard";
import { HealthChip } from "../components/HealthChip";

const EXAMPLES = [
  { icon: "psychology", text: "How do transformers model long-range dependencies?" },
  { icon: "hub", text: "Recent advances in retrieval-augmented generation" },
  { icon: "memory", text: "Mixture-of-experts routing for efficient LLMs" },
];

function VerifyBadge({ supported }: { supported: boolean | null }) {
  if (supported === true) {
    return (
      <div className="w-6 h-6 rounded-full bg-verify-bg flex items-center justify-center border border-verify-fg/20" title="Verified — entailed by its sources">
        <Icon name="check" className="text-[14px] text-verify-fg" />
      </div>
    );
  }
  if (supported === false) {
    return (
      <div className="w-6 h-6 rounded-full bg-warn-bg flex items-center justify-center border border-warn-fg/20" title="Flagged — not clearly supported by its sources">
        <Icon name="warning" className="text-[14px] text-warn-fg" />
      </div>
    );
  }
  return (
    <div className="w-6 h-6 rounded-full bg-surface-variant flex items-center justify-center border border-outline-variant/40" title="Unverified">
      <Icon name="remove" className="text-[14px] text-on-surface-variant" />
    </div>
  );
}

function ClaimBlock({
  claim,
  sourceMap,
  onActivate,
}: {
  claim: ReviewClaim;
  sourceMap: Map<string, SourceOut>;
  onActivate: (key: string) => void;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-1 flex-shrink-0">
        <VerifyBadge supported={claim.supported} />
      </div>
      <p className="font-article-body text-article-body text-on-surface leading-relaxed">
        {claim.text}{" "}
        {claim.source_ids.map((key) => (
          <CitationChip key={key} sourceKey={key} source={sourceMap.get(key)} onActivate={onActivate} />
        ))}
      </p>
    </div>
  );
}

function SkeletonClaim() {
  return (
    <div className="flex items-start gap-3 animate-pulse">
      <div className="mt-1 w-6 h-6 rounded-full bg-surface-variant flex-shrink-0" />
      <div className="flex-1 space-y-2 mt-1">
        <div className="h-4 bg-surface-variant rounded w-full" />
        <div className="h-4 bg-surface-variant rounded w-5/6" />
        <div className="h-4 bg-surface-variant rounded w-4/6" />
      </div>
    </div>
  );
}

export function WorkspacePage() {
  const { state, run, stop, reset } = useReviewStream();
  const [input, setInput] = useState("");
  const [searchOnly, setSearchOnly] = useState(false);
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [params, setParams] = useSearchParams();
  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Auto-run when navigated here with ?q=... (e.g. from the Search page).
  useEffect(() => {
    const q = params.get("q");
    if (q && q !== state.query) {
      setInput(q);
      run(q, params.get("mode") === "search");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const sourceMap = useMemo(() => {
    const m = new Map<string, SourceOut>();
    for (const s of state.sources) m.set(s.source_key, s);
    return m;
  }, [state.sources]);

  const citedKeys = useMemo(() => {
    const set = new Set<string>();
    for (const c of state.claims) for (const k of c.source_ids) set.add(k);
    return set;
  }, [state.claims]);

  const topScore = useMemo(() => maxScore(state.sources), [state.sources]);
  const verifiedCount = state.claims.filter((c) => c.supported === true).length;
  const running = state.phase === "retrieving" || state.phase === "streaming";

  const submit = (q: string) => {
    if (!q.trim()) return;
    setParams({ q: q.trim(), ...(searchOnly ? { mode: "search" } : {}) });
    run(q.trim(), searchOnly);
  };

  const activate = (key: string) => {
    setActiveKey(key);
    cardRefs.current.get(key)?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const copyMarkdown = () => {
    if (state.markdown) navigator.clipboard.writeText(state.markdown);
  };

  const hasRun = state.phase !== "idle";

  return (
    <div className="flex-1 flex flex-col lg:flex-row w-full mx-auto max-w-container-max">
      {/* Left / center: Ask + review */}
      <div className="flex-1 flex flex-col p-margin-mobile md:p-8 lg:p-12 lg:pr-8 border-r border-outline-variant/30 min-w-0">
        <div className="flex items-center justify-between mb-8">
          <h1 className="font-display-lg text-headline-lg-mobile text-primary">Research Workspace</h1>
          <HealthChip />
        </div>

        {/* AskBox */}
        <section className="mb-10">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 focus-within:border-primary focus-within:ring-1 focus-within:ring-primary transition-all shadow-[0_4px_40px_-10px_rgba(0,0,0,0.04)]">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit(input);
                }
              }}
              placeholder="Ask Citely to review a claim, summarize findings, or synthesize literature…"
              className="w-full bg-transparent border-none p-0 focus:ring-0 resize-none font-article-body text-article-body text-on-surface placeholder:text-on-surface-variant/50 min-h-[80px] outline-none"
            />
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-outline-variant/50">
              <label className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={searchOnly}
                  onChange={(e) => setSearchOnly(e.target.checked)}
                  className="academic-checkbox"
                />
                <span className="font-ui-label-md text-ui-label-sm text-on-surface-variant group-hover:text-on-surface transition-colors">
                  Search-only mode
                </span>
              </label>
              {running ? (
                <button
                  onClick={stop}
                  className="bg-surface-variant text-on-surface font-ui-label-md text-ui-label-md px-6 py-2 rounded flex items-center gap-2 hover:opacity-90 transition-opacity"
                >
                  <Icon name="stop" className="text-[18px]" />
                  Stop
                </button>
              ) : (
                <button
                  onClick={() => submit(input)}
                  className="bg-primary text-on-primary font-ui-label-md text-ui-label-md px-6 py-2 rounded flex items-center gap-2 hover:bg-on-primary-fixed-variant transition-colors disabled:opacity-50"
                  disabled={!input.trim()}
                >
                  <Icon name="send" className="text-[18px]" />
                  {searchOnly ? "Search" : "Synthesize"}
                </button>
              )}
            </div>
          </div>

          {!hasRun && (
            <div className="mt-4 flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex.text}
                  onClick={() => {
                    setInput(ex.text);
                    submit(ex.text);
                  }}
                  className="px-3 py-1.5 border border-outline-variant rounded-full font-ui-label-md text-ui-label-sm text-on-surface-variant hover:bg-surface-variant transition-colors flex items-center gap-1.5"
                >
                  <Icon name={ex.icon} className="text-[14px]" />
                  {ex.text}
                </button>
              ))}
            </div>
          )}
        </section>

        {/* Review */}
        {hasRun && (
          <section className="flex-1">
            <div className="max-w-article-width mx-auto space-y-8">
              <div className="pb-6 border-b border-outline-variant/30">
                <h2 className="font-headline-lg text-headline-lg text-on-surface">{state.query}</h2>
                <div className="flex items-center gap-3 mt-3 flex-wrap">
                  <span className="font-ui-label-md text-ui-label-sm text-on-surface-variant capitalize">
                    {state.phase === "retrieving"
                      ? "Retrieving sources…"
                      : state.phase === "streaming"
                        ? "Synthesizing review…"
                        : state.searchOnly
                          ? "Search-only results"
                          : "Review complete"}
                  </span>
                  {!state.searchOnly && state.claims.length > 0 && (
                    <span className="flex items-center gap-1 font-ui-label-md text-ui-label-sm text-on-primary-container bg-primary-container/10 px-2 py-0.5 rounded">
                      <Icon name="task_alt" className="text-[14px]" />
                      {verifiedCount} / {state.claims.length} claims verified
                    </span>
                  )}
                  <button
                    onClick={reset}
                    className="ml-auto font-ui-label-md text-ui-label-sm text-on-surface-variant hover:text-primary flex items-center gap-1"
                  >
                    <Icon name="restart_alt" className="text-[16px]" /> New
                  </button>
                </div>
              </div>

              {state.phase === "error" && (
                <div className="flex items-center gap-2 text-error font-ui-label-md text-ui-label-md bg-error-container/40 border border-error/20 rounded-lg p-4">
                  <Icon name="error" className="text-[18px]" />
                  {state.error}
                </div>
              )}

              {!state.searchOnly && (
                <div className="space-y-6">
                  {state.claims.map((c, i) => (
                    <ClaimBlock key={i} claim={c} sourceMap={sourceMap} onActivate={activate} />
                  ))}
                  {state.phase === "streaming" && <SkeletonClaim />}
                  {state.phase === "done" && state.claims.length === 0 && (
                    <p className="font-ui-label-md text-ui-label-md text-on-surface-variant">
                      No grounded claims were produced for this query. Try rephrasing, or ingest more
                      papers in the matching area.
                    </p>
                  )}
                </div>
              )}

              {state.searchOnly && state.phase === "done" && (
                <p className="font-ui-label-md text-ui-label-md text-on-surface-variant">
                  Retrieved {state.sources.length} passages. See the Sources panel.
                </p>
              )}

              {/* Bibliography (cited sources) + copy */}
              {!state.searchOnly && citedKeys.size > 0 && (
                <div className="pt-10 mt-10 border-t border-outline-variant/30">
                  <div className="flex justify-between items-end mb-6">
                    <h3 className="font-headline-lg text-[20px] text-on-surface font-semibold">
                      Bibliography
                    </h3>
                    {state.markdown && (
                      <button
                        onClick={copyMarkdown}
                        className="flex items-center gap-2 font-ui-label-md text-ui-label-sm text-on-surface-variant hover:text-primary transition-colors"
                      >
                        <Icon name="content_copy" className="text-[16px]" />
                        Copy as Markdown
                      </button>
                    )}
                  </div>
                  <ul className="space-y-3 font-ui-label-md text-ui-label-sm text-on-surface-variant list-decimal list-inside">
                    {[...citedKeys]
                      .map((k) => sourceMap.get(k))
                      .filter((s): s is SourceOut => Boolean(s))
                      .map((s) => (
                        <li key={s.source_key}>
                          <span className="font-citation-caps text-citation-caps text-primary mr-1">
                            {s.source_key}
                          </span>
                          {s.title ?? s.paper_id}.{" "}
                          <a
                            href={`https://arxiv.org/abs/${s.paper_id}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-primary hover:underline"
                          >
                            arXiv:{s.paper_id}
                          </a>
                        </li>
                      ))}
                  </ul>
                </div>
              )}

              {/* Rendered final markdown (collapsible reference copy) */}
              {state.markdown && (
                <details className="pt-6 border-t border-outline-variant/20">
                  <summary className="cursor-pointer font-ui-label-md text-ui-label-sm text-on-surface-variant hover:text-primary">
                    View rendered markdown
                  </summary>
                  <div className="prose prose-sm max-w-none mt-4 font-article-body">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{state.markdown}</ReactMarkdown>
                  </div>
                </details>
              )}
            </div>
          </section>
        )}
      </div>

      {/* Right: SourcesPanel */}
      <aside className="w-full lg:w-[360px] flex-shrink-0 bg-surface-bright flex flex-col">
        <div className="p-6 border-b border-outline-variant/30 flex justify-between items-center sticky top-0 bg-surface-bright/90 backdrop-blur-sm z-10">
          <h3 className="font-ui-label-md text-[16px] font-semibold text-on-surface flex items-center gap-2">
            <Icon name="library_books" className="text-[20px]" />
            Retrieved Sources
          </h3>
          {state.sources.length > 0 && (
            <span className="bg-surface-variant text-on-surface-variant px-2 py-0.5 rounded font-citation-caps text-citation-caps">
              {state.sources.length} FOUND
            </span>
          )}
        </div>
        <div className="p-6 space-y-4 overflow-y-auto flex-1">
          {state.sources.length === 0 && (
            <p className="font-ui-label-md text-ui-label-sm text-on-surface-variant">
              {running ? "Retrieving…" : "Sources for your query will appear here."}
            </p>
          )}
          {state.sources.map((s) => (
            <SourceCard
              key={s.passage_id}
              source={s}
              fraction={relevanceFraction(s.score, topScore)}
              cited={citedKeys.size === 0 || citedKeys.has(s.source_key)}
              active={activeKey === s.source_key}
              onClick={() => setActiveKey(s.source_key)}
              registerRef={(el) => {
                if (el) cardRefs.current.set(s.source_key, el);
                else cardRefs.current.delete(s.source_key);
              }}
            />
          ))}
        </div>
      </aside>
    </div>
  );
}
