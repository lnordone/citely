import { useEffect, useState } from "react";
import { getHealth, HealthResponse } from "../api";
import { Icon } from "./Icon";

// Live backend status: polls /health and shows the active LLM + embedding models.
export function HealthChip() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const h = await getHealth();
        if (active) {
          setHealth(h);
          setFailed(false);
        }
      } catch {
        if (active) setFailed(true);
      }
    };
    poll();
    const id = setInterval(poll, 15000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const ok = !failed && health?.status === "ok";
  const dot = failed ? "bg-error" : ok ? "bg-verify-fg" : "bg-warn-fg";
  const label = failed
    ? "Backend offline"
    : health
      ? `${health.llm_model ?? "?"} · ${health.embedding_model ?? "?"}`
      : "Connecting…";

  return (
    <div
      className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-container-low border border-outline-variant/40"
      title={failed ? "Could not reach the Citely API" : `LLM and embedding models (status: ${health?.status ?? "?"})`}
    >
      <span className={`w-2 h-2 rounded-full ${dot}`} />
      <Icon name="dns" className="text-[14px] text-on-surface-variant" />
      <span className="font-ui-label-sm text-ui-label-sm text-on-surface-variant truncate max-w-[220px]">
        {label}
      </span>
    </div>
  );
}
