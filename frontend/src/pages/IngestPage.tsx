import { useEffect, useRef, useState } from "react";
import { getHealth, HealthResponse, IngestDone, IngestProgress, streamIngest } from "../api";
import { Icon } from "../components/Icon";

const CATEGORIES = [
  { id: "cs.AI", label: "cs.AI (Artificial Intelligence)" },
  { id: "cs.LG", label: "cs.LG (Machine Learning)" },
  { id: "cs.CL", label: "cs.CL (Computation & Language)" },
  { id: "cs.CV", label: "cs.CV (Computer Vision)" },
  { id: "eess.SP", label: "eess.SP (Signal Processing)" },
];

type Phase = "idle" | "fetching" | "embedding" | "done" | "error";

function progressPercent(phase: Phase, p: IngestProgress | null, maxPapers: number): number {
  if (phase === "idle" || phase === "error") return 0;
  if (phase === "done") return 100;
  if (phase === "fetching") {
    const papers = p?.papers ?? 0;
    const denom = p?.max_papers ?? maxPapers;
    return Math.min((papers / denom) * 60, 58);
  }
  // embedding: 60–100%
  const embedded = p?.embedded ?? 0;
  const total = p?.total ?? 1;
  return 60 + (embedded / total) * 40;
}

export function IngestPage() {
  const [selected, setSelected] = useState<Set<string>>(new Set(["cs.AI", "cs.LG", "cs.CL"]));
  const [maxPapers, setMaxPapers] = useState(150);
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState<IngestProgress | null>(null);
  const [result, setResult] = useState<IngestDone | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const start = async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setPhase("fetching");
    setProgress(null);
    setError(null);
    setResult(null);

    await streamIngest(
      { categories: [...selected], max_papers: maxPapers },
      {
        onProgress(p) {
          setProgress(p);
          if (p.phase === "embed") setPhase("embedding");
        },
        onDone(d) {
          setResult(d);
          setPhase("done");
        },
        onError(e) {
          setError(e.message);
          setPhase("error");
        },
      },
      ctrl.signal,
    );
  };

  const cancel = () => {
    abortRef.current?.abort();
    setPhase("idle");
    setProgress(null);
  };

  const pct = progressPercent(phase, progress, maxPapers);
  const running = phase === "fetching" || phase === "embedding";

  return (
    <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-10 md:py-16 w-full">
      <header className="mb-12">
        <h1 className="font-headline-lg text-headline-lg-mobile md:text-headline-lg text-primary mb-2">
          Ingest Papers
        </h1>
        <p className="text-on-surface-variant font-article-body text-article-body">
          Configure parameters and pull papers from arXiv into your local corpus.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-gutter">
        {/* Form */}
        <div className="md:col-span-8 space-y-8">
          <div className="border border-outline/20 rounded-lg p-6 bg-surface">
            <h2 className="font-headline-lg text-[20px] text-on-surface mb-6">Retrieval Configuration</h2>

            <div className="mb-8">
              <label className="block font-citation-caps text-citation-caps text-on-surface-variant mb-4 uppercase">
                arXiv Categories
              </label>
              <div className="flex flex-wrap gap-4">
                {CATEGORIES.map((c) => (
                  <label key={c.id} className="flex items-center gap-2 cursor-pointer group">
                    <input
                      type="checkbox"
                      className="academic-checkbox"
                      checked={selected.has(c.id)}
                      onChange={() => toggle(c.id)}
                    />
                    <span className="font-ui-label-md text-ui-label-md text-on-surface group-hover:text-primary transition-colors">
                      {c.label}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* NOTE(pending-backend): /ingest does not accept a date window yet. */}
            <div className="mb-8 opacity-60">
              <label className="block font-citation-caps text-citation-caps text-on-surface-variant mb-4 uppercase">
                Publication Window (pending backend)
              </label>
              <div className="flex gap-4">
                <input type="date" disabled className="flex-1 bg-transparent border-b border-outline-variant px-0 py-2 font-ui-label-md text-ui-label-md text-on-surface-variant" />
                <span className="flex items-center text-on-surface-variant">to</span>
                <input type="date" disabled className="flex-1 bg-transparent border-b border-outline-variant px-0 py-2 font-ui-label-md text-ui-label-md text-on-surface-variant" />
              </div>
            </div>

            <div className="mb-8">
              <div className="flex justify-between items-end mb-4">
                <label className="block font-citation-caps text-citation-caps text-on-surface-variant uppercase">
                  Maximum Papers to Retrieve
                </label>
                <span className="font-ui-label-md text-ui-label-md text-primary font-semibold">
                  {maxPapers}
                </span>
              </div>
              <input
                type="range"
                className="citely-range"
                min={10}
                max={2000}
                step={10}
                value={maxPapers}
                onChange={(e) => setMaxPapers(Number(e.target.value))}
              />
            </div>

            <div className="pt-4 flex justify-end gap-3 border-t border-outline/10">
              {running && (
                <button
                  onClick={cancel}
                  className="font-ui-label-md text-ui-label-md px-4 py-2.5 rounded border border-outline/30 text-on-surface-variant hover:border-error hover:text-error transition-colors"
                >
                  Cancel
                </button>
              )}
              <button
                onClick={start}
                disabled={running || selected.size === 0}
                className="bg-primary text-on-primary font-ui-label-md text-ui-label-md px-6 py-2.5 rounded hover:bg-primary-container hover:text-on-primary-container transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <Icon name={running ? "progress_activity" : "cloud_download"} className={`text-[18px] ${running ? "animate-spin" : ""}`} />
                {running ? "Ingesting…" : "Start Ingestion"}
              </button>
            </div>
          </div>

          {/* Status */}
          <div className="border border-outline/20 rounded-lg p-6 bg-surface-container-lowest">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-citation-caps text-citation-caps text-on-surface-variant uppercase">
                Operation Status
              </h3>
              <span className={`font-ui-label-sm text-ui-label-sm px-2 py-1 rounded uppercase ${
                phase === "done" ? "bg-verify-bg text-verify-fg"
                : phase === "error" ? "bg-error/10 text-error"
                : "bg-surface-variant text-outline"
              }`}>
                {phase}
              </span>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-surface-variant h-2 rounded-full overflow-hidden mb-2">
              <div
                className="bg-primary h-full rounded-full transition-all duration-300 ease-out"
                style={{ width: `${pct}%` }}
              />
            </div>

            {/* Phase label + live counters */}
            <div className="flex justify-between items-center text-ui-label-sm font-ui-label-sm text-on-surface-variant mb-3">
              <span>
                {phase === "fetching" && (
                  <>Fetching papers… <span className="text-primary font-semibold">{progress?.papers ?? 0}</span> / {maxPapers}</>
                )}
                {phase === "embedding" && (
                  <>Embedding passages… <span className="text-primary font-semibold">{progress?.embedded ?? 0}</span>{progress?.total ? ` / ${progress.total}` : ""}</>
                )}
                {phase === "done" && "Complete"}
                {phase === "error" && "Failed"}
                {phase === "idle" && "Ready"}
              </span>
              <span className="tabular-nums">{Math.round(pct)}%</span>
            </div>

            {error && <p className="font-ui-label-md text-ui-label-sm text-error mb-2">{error}</p>}
            {result && (
              <div className="flex gap-6 text-ui-label-sm font-ui-label-sm text-on-surface-variant border-t border-outline/10 pt-3">
                <span><span className="text-on-surface font-semibold">{result.papers_stored}</span> papers stored</span>
                <span><span className="text-on-surface font-semibold">{result.passages_stored}</span> passages</span>
                <span>
                  <span className="text-on-surface font-semibold">
                    {result.total_embedded ?? result.passages_embedded}
                  </span>{" embedded"}
                  {result.passages_embedded > 0 && (
                    <span className="ml-1 opacity-60">({result.passages_embedded} new)</span>
                  )}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar: backend services */}
        <div className="md:col-span-4 space-y-6">
          <div>
            <h3 className="font-citation-caps text-citation-caps text-on-surface-variant uppercase mb-3 ml-1">
              Backend Services
            </h3>
            <div className="border border-outline/20 rounded bg-surface overflow-hidden">
              <Service label="LLM Inference" value={health?.llm_model} online={Boolean(health)} />
              <Service label="Embeddings" value={health?.embedding_model} online={Boolean(health)} last />
            </div>
          </div>
          <div className="border border-outline/20 rounded p-4 bg-surface">
            <p className="font-ui-label-md text-ui-label-sm text-on-surface-variant">
              Ingestion is idempotent — re-running skips arXiv ids already stored. New passages are
              embedded automatically, so they’re searchable as soon as ingestion completes.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Service({
  label,
  value,
  online,
  last,
}: {
  label: string;
  value?: string | null;
  online: boolean;
  last?: boolean;
}) {
  return (
    <div className={`p-4 flex items-center justify-between ${last ? "" : "border-b border-outline/10"}`}>
      <div className="flex items-center gap-3">
        <span className={`w-2 h-2 rounded-full ${online ? "bg-verify-fg" : "bg-error"}`} />
        <span className="font-ui-label-md text-ui-label-md text-on-surface">{label}</span>
      </div>
      <span className="font-ui-label-sm text-ui-label-sm text-on-surface-variant">
        {value ?? (online ? "—" : "offline")}
      </span>
    </div>
  );
}
