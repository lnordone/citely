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

// Orchestrates a single research run, with cancellation.
//
// A review run reads its sources from the /review stream's `sources` event rather than a
// separate /search call. Citation keys (S1..Sn) are assigned per retrieval, so resolving
// them against an independently-ranked /search response could point a chip at a paper the
// review never cited. Using one retrieval also halves the work per run.
//
// `searchOnly` skips generation for fast retrieval-only exploration; that path has no
// citations to align, so it calls /search directly.
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

    if (searchOnly) {
      try {
        const res = await apiSearch(query, undefined, controller.signal);
        setState((s) => ({ ...s, sources: res.sources, phase: "done" }));
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setState((s) => ({ ...s, phase: "error", error: (err as Error).message }));
      }
      return;
    }

    await streamReview(
      query,
      {
        // Arrives before the first claim; flips the run from retrieving to streaming.
        onSources: (sources: SourceOut[]) =>
          setState((s) => ({ ...s, sources, phase: "streaming" })),
        onClaim: (claim: ReviewClaim) => setState((s) => ({ ...s, claims: [...s.claims, claim] })),
        onDone: (done: ReviewDone) =>
          setState((s) => ({ ...s, markdown: done.markdown, phase: "done" })),
        onError: (err: Error) => setState((s) => ({ ...s, phase: "error", error: err.message })),
      },
      controller.signal,
    );
    // Stream ended without a `done` event (or without ever sending sources) — don't
    // strand the UI mid-run.
    setState((s) =>
      s.phase === "streaming" || s.phase === "retrieving" ? { ...s, phase: "done" } : s,
    );
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setState(initial);
  }, []);

  return { state, run, stop, reset };
}
