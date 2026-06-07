import { bars } from "../lib/relevance";

export function RelevanceBar({ fraction }: { fraction: number }) {
  const filled = bars(fraction);
  const label = filled >= 4 ? "High relevance" : filled >= 2 ? "Medium relevance" : "Low relevance";
  return (
    <div className="flex gap-0.5" title={label} aria-label={label}>
      {[0, 1, 2, 3].map((i) => (
        <span
          key={i}
          className={`w-1.5 h-3 rounded-sm ${i < filled ? "bg-primary" : "bg-surface-variant"}`}
        />
      ))}
    </div>
  );
}
