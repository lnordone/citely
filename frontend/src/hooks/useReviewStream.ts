import { useCallback, useRef, useState } from "react";
import {
  ReviewClaim,
  ReviewDone,
  search as apiSearch,
  SourceOut,
  streamReview,
} from "../api";

export type RunPhase = "idle" | "retrieving" | "streaming" | "done" | "error";

export interface ReviewState {
  phase: RunPhase;
  query: string;
  sources: SourceOut[];
  claims: ReviewClaim[];
  markdown: string | null;
  error: string | null;
  searchOnly: boolean;
}

const initial: ReviewState = {
  phase: "idle",
  query: "",
  sources: [],
  claims: [],
  markdown: null,
  error: null,
  searchOnly: false,
};

// Orchestrates a single research run: /search (sources) then the /review SSE (claims),
// with cancellation. `searchOnly` skips generation for fast retrieval-only exploration.
export function useReviewStream() {
  const [state, setState] = useState<ReviewState>(initial);
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setState((s) => (s.phase === "streaming" || s.phase === "retrieving" ? { ...s, phase: "done" } : s));
  }, []);

  const run = useCallback(async (query: string, searchOnly = false) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ ...initial, query, searchOnly, phase: "retrieving" });

    try {
      const res = await apiSearch(query, undefined, controller.signal);
      setState((s) => ({ ...s, sources: res.sources }));
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setState((s) => ({ ...s, phase: "error", error: (err as Error).message }));
      return;
    }

    if (searchOnly) {
      setState((s) => ({ ...s, phase: "done" }));
      return;
    }

    setState((s) => ({ ...s, phase: "streaming" }));
    await streamReview(
      query,
      {
        onClaim: (claim: ReviewClaim) => setState((s) => ({ ...s, claims: [...s.claims, claim] })),
        onDone: (done: ReviewDone) =>
          setState((s) => ({ ...s, markdown: done.markdown, phase: "done" })),
        onError: (err: Error) => setState((s) => ({ ...s, phase: "error", error: err.message })),
      },
      controller.signal,
    );
    setState((s) => (s.phase === "streaming" ? { ...s, phase: "done" } : s));
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setState(initial);
  }, []);

  return { state, run, stop, reset };
}
