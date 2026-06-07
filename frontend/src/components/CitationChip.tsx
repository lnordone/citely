import { SourceOut } from "../api";
import { Icon } from "./Icon";

// Inline [S?] citation marker with a hover preview of its source. Clicking activates the
// matching card in the SourcesPanel.
export function CitationChip({
  sourceKey,
  source,
  onActivate,
}: {
  sourceKey: string;
  source?: SourceOut;
  onActivate?: (key: string) => void;
}) {
  return (
    <span className="inline-flex relative group align-baseline">
      <button
        type="button"
        onClick={() => onActivate?.(sourceKey)}
        className="font-citation-caps text-citation-caps text-primary bg-primary-fixed/40 hover:bg-primary-fixed/70 px-1.5 py-0.5 rounded border border-primary/20 transition-colors mx-0.5"
        aria-label={`Citation ${sourceKey}${source?.title ? `: ${source.title}` : ""}`}
      >
        {sourceKey}
      </button>
      {source && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 bg-surface-container-lowest border border-outline-variant p-3 shadow-[0_4px_40px_-10px_rgba(0,0,0,0.12)] rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-30 pointer-events-none">
          <span className="block font-display-lg text-ui-label-sm font-semibold mb-1 text-on-surface">
            {source.title ?? source.paper_id}
          </span>
          <span className="block font-ui-label-md text-ui-label-sm text-on-surface-variant line-clamp-3 mb-2">
            {source.text}
          </span>
          <span className="flex items-center gap-1 font-ui-label-md text-[11px] text-primary">
            <Icon name="open_in_new" className="text-[12px]" />
            arXiv:{source.paper_id}
          </span>
        </span>
      )}
    </span>
  );
}
