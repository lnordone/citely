import { arxivAbsUrl, SourceOut } from "../api";
import { Icon } from "./Icon";
import { RelevanceBar } from "./RelevanceBar";

// A retrieved-source card for the right-hand SourcesPanel. `cited` dims uncited sources;
// `active` highlights the source a clicked citation points to.
export function SourceCard({
  source,
  fraction,
  cited,
  active,
  onClick,
  registerRef,
}: {
  source: SourceOut;
  fraction: number;
  cited: boolean;
  active: boolean;
  onClick?: () => void;
  registerRef?: (el: HTMLDivElement | null) => void;
}) {
  return (
    <div
      ref={registerRef}
      onClick={onClick}
      className={[
        "bg-surface-container-lowest border rounded-lg p-4 transition-colors group cursor-pointer relative",
        active ? "border-primary ring-1 ring-primary" : "border-outline-variant hover:border-primary/40",
        cited ? "" : "opacity-70",
      ].join(" ")}
    >
      <div
        className={`absolute -left-3 top-4 font-citation-caps text-citation-caps px-1.5 py-0.5 rounded border border-surface-container-lowest ${
          cited ? "bg-primary text-on-primary" : "bg-surface-variant text-on-surface-variant"
        }`}
      >
        {source.source_key}
      </div>

      <div className="flex justify-between items-start mb-2 pl-2">
        <a
          href={arxivAbsUrl(source.paper_id)}
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="font-ui-label-md text-[11px] text-primary hover:underline flex items-center gap-1"
        >
          arXiv:{source.paper_id}
          <Icon name="open_in_new" className="text-[12px]" />
        </a>
        <RelevanceBar fraction={fraction} />
      </div>

      <h4 className="font-display-lg text-[15px] font-semibold text-on-surface leading-snug mb-2 pl-2 group-hover:text-primary transition-colors">
        {source.title ?? source.paper_id}
      </h4>
      <p className="font-ui-label-md text-ui-label-sm text-on-surface-variant line-clamp-3 pl-2 mb-3">
        {source.text}
      </p>
      <div className="pl-2 flex gap-2">
        <span className="px-2 py-1 bg-warn-bg text-warn-fg rounded text-[10px] font-medium border border-warn-fg/20">
          Pre-print
        </span>
      </div>
    </div>
  );
}
