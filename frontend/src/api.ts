// API wrappers incl. SSE consumption of /review.
// TODO(phase 10): flesh out types and error handling.

export interface SourceOut {
  source_key: string;
  passage_id: string;
  paper_id: string;
  title?: string;
  text: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  sources: SourceOut[];
}

export async function search(query: string): Promise<SearchResponse> {
  const res = await fetch("/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(`search failed: ${res.status}`);
  return res.json();
}

// Consume the SSE /review stream, invoking onDelta for each event payload.
export async function streamReview(
  query: string,
  onDelta: (chunk: string) => void,
): Promise<void> {
  const res = await fetch("/review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.body) throw new Error("no response body for /review");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  // TODO(phase 10): parse proper SSE framing (event:/data: lines).
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    onDelta(decoder.decode(value, { stream: true }));
  }
}
