import { SourceOut } from "../api";

// Rerank/cosine scores aren't on a fixed absolute scale, so we normalize relative to the
// strongest source in the current result set to drive the 0–4 "relevance bar" UI.
export function relevanceFraction(score: number, maxScore: number): number {
  if (!isFinite(score) || maxScore <= 0) return 0;
  return Math.max(0, Math.min(1, score / maxScore));
}

export function maxScore(sources: SourceOut[]): number {
  return sources.reduce((m, s) => Math.max(m, s.score), 0);
}

export function bars(fraction: number): number {
  return Math.max(1, Math.round(fraction * 4));
}
