import { SourceOut } from "../api";

// TODO(phase 10): richer source cards.
export function ResultsList({ sources }: { sources: SourceOut[] }) {
  if (!sources.length) return null;
  return (
    <section>
      <h2>Sources</h2>
      <ol>
        {sources.map((s) => (
          <li key={s.passage_id}>
            <strong>[{s.source_key}]</strong> {s.title ?? s.paper_id} — {s.text.slice(0, 160)}…
          </li>
        ))}
      </ol>
    </section>
  );
}
