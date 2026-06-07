// Typed client for the Citely FastAPI backend.
// All paths are same-origin and proxied to http://localhost:8000 in dev (see vite.config.ts).

export interface HealthResponse {
  status: "ok" | "degraded";
  llm_model: string | null;
  embedding_model: string | null;
}

export interface SourceOut {
  source_key: string; // citation key, e.g. "S1"
  passage_id: string;
  paper_id: string; // arXiv id, e.g. "2305.14890"
  title?: string | null;
  text: string;
  score: number;
  // NOTE(pending-backend): authors / year / url / venue are NOT returned by /search yet.
  // They exist server-side as PaperRef; expose them on SourceOut to enrich source cards.
}

export interface SearchResponse {
  query: string;
  sources: SourceOut[];
}

export interface IngestRequest {
  categories?: string[];
  max_papers?: number;
  // NOTE(pending-backend): date range / explicit filters are not accepted by /ingest yet.
}

/** Fired after each paper is stored (phase === "fetch") or embedding batch (phase === "embed"). */
export interface IngestProgress {
  phase: "fetch" | "embed";
  /** fetch phase — papers committed so far */
  papers?: number;
  /** fetch phase — passages committed so far */
  passages?: number;
  /** fetch phase — requested ceiling (denominator for fetch progress) */
  max_papers?: number;
  /** embed phase — passages embedded so far */
  embedded?: number;
  /** embed phase — total passages that need embedding (denominator) */
  total?: number;
}

export interface IngestDone {
  papers_stored: number;
  passages_stored: number;
  passages_embedded: number;
  /** Total passages with embeddings in the DB (includes prior runs). */
  total_embedded?: number;
}

/** @deprecated route now streams SSE — use streamIngest instead */
export interface IngestResponse extends IngestDone {}

export interface IngestHandlers {
  onProgress?: (p: IngestProgress) => void;
  onDone?: (d: IngestDone) => void;
  onError?: (err: Error) => void;
}

// A single streamed claim from /review (event: claim).
export interface ReviewClaim {
  text: string;
  source_ids: string[];
  supported: boolean | null; // true = verified, false = flagged unsupported, null = unverified
}

// Final event payload from /review (event: done).
export interface ReviewDone {
  markdown: string;
  num_claims: number;
}

async function postJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch("/health", { signal });
  if (!res.ok) throw new Error(`/health failed: ${res.status}`);
  return (await res.json()) as HealthResponse;
}

export async function search(
  query: string,
  topK?: number,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  return postJson<SearchResponse>("/search", { query, top_k: topK }, signal);
}

/**
 * POST /ingest as an SSE stream. Calls handlers as progress events arrive.
 * /ingest is a POST with a JSON body (EventSource is GET-only), so we parse SSE manually.
 */
export async function streamIngest(
  req: IngestRequest,
  handlers: IngestHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch("/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(req),
      signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") return;
    handlers.onError?.(err as Error);
    return;
  }

  if (!res.ok || !res.body) {
    handlers.onError?.(new Error(`/ingest failed: ${res.status}`));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let streamResolved = false;

  const append = (chunk: Uint8Array) => {
    buffer += decoder.decode(chunk, { stream: true }).replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  };

  const dispatch = (rawEvent: string) => {
    let event = "message";
    const dataLines: string[] = [];
    for (const line of rawEvent.split("\n")) {
      if (line.startsWith(":")) continue;
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).replace(/^ /, ""));
    }
    if (!dataLines.length) return;
    try {
      const parsed = JSON.parse(dataLines.join("\n"));
      if (event === "progress") handlers.onProgress?.(parsed as IngestProgress);
      else if (event === "done") { streamResolved = true; handlers.onDone?.(parsed as IngestDone); }
      else if (event === "error") { streamResolved = true; handlers.onError?.(new Error(parsed.message ?? "ingest error")); }
    } catch {
      // ignore malformed frames
    }
  };

  let aborted = false;
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      append(value);
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        if (rawEvent.trim()) dispatch(rawEvent);
      }
    }
    if (buffer.trim()) dispatch(buffer);
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      aborted = true;
    } else {
      handlers.onError?.(err as Error);
      return;
    }
  }
  if (!aborted && !streamResolved) {
    handlers.onError?.(new Error("Ingest stream ended without completion"));
  }
}

export interface ReviewHandlers {
  onClaim?: (claim: ReviewClaim) => void;
  onDone?: (done: ReviewDone) => void;
  onError?: (err: Error) => void;
}

/**
 * Consume the SSE /review stream. Parses real SSE framing (event:/data: lines, events
 * separated by blank lines) rather than dumping raw bytes. Returns when the stream ends
 * or is aborted via `signal`.
 *
 * /review is a POST with a JSON body, so EventSource (GET-only) can't be used — we read
 * the response body stream and parse it ourselves.
 */
export async function streamReview(
  query: string,
  handlers: ReviewHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch("/review", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ query }),
      signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") return;
    handlers.onError?.(err as Error);
    return;
  }

  if (!res.ok || !res.body) {
    handlers.onError?.(new Error(`/review failed: ${res.status}`));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const appendReview = (chunk: Uint8Array) => {
    buffer += decoder.decode(chunk, { stream: true }).replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  };

  const dispatch = (rawEvent: string) => {
    let event = "message";
    const dataLines: string[] = [];
    for (const line of rawEvent.split("\n")) {
      if (line.startsWith(":")) continue; // comment / heartbeat
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).replace(/^ /, ""));
    }
    if (!dataLines.length) return;
    const data = dataLines.join("\n");
    try {
      const parsed = JSON.parse(data);
      if (event === "claim") handlers.onClaim?.(parsed as ReviewClaim);
      else if (event === "done") handlers.onDone?.(parsed as ReviewDone);
    } catch {
      // ignore malformed event payloads
    }
  };

  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      appendReview(value);
      let sep: number;
      // SSE events are separated by a blank line ("\n\n").
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        if (rawEvent.trim()) dispatch(rawEvent);
      }
    }
    if (buffer.trim()) dispatch(buffer);
  } catch (err) {
    if ((err as Error).name !== "AbortError") handlers.onError?.(err as Error);
  }
}

// arXiv links derived client-side from paper_id (backend doesn't return a URL yet).
export function arxivAbsUrl(paperId: string): string {
  return `https://arxiv.org/abs/${paperId}`;
}
export function arxivPdfUrl(paperId: string): string {
  return `https://arxiv.org/pdf/${paperId}`;
}
