import type { Ref } from "react";
import type { FlowNode } from "../../data/types";
import { InlineText } from "../../lib/markdown";

interface FlowCardProps {
  node: FlowNode;
  accent: string;
  /** Which edge carries the accent stripe. Distinguishes a branch from a step. */
  edge?: "top" | "left";
  /** Step number, shown only where reading order is part of the meaning. */
  badge?: number;
  className?: string;
  ref?: Ref<HTMLDivElement>;
}

/** The node body every flow shape shares; only the connectors between them differ. */
export function FlowCard({ node, accent, edge = "top", badge, className, ref }: FlowCardProps) {
  return (
    <div
      ref={ref}
      className={`rounded-md border bg-card px-3 py-2 shadow-sm ${className ?? ""}`}
      style={{
        borderColor: `color-mix(in oklab, ${accent} 33%, transparent)`,
        ...(edge === "top"
          ? { borderTopWidth: 3, borderTopColor: accent }
          : { borderLeftWidth: 3, borderLeftColor: accent }),
      }}
    >
      {badge !== undefined && (
        <div
          className="mb-0.5 font-mono text-[9.5px] uppercase tracking-[0.14em] tabular-nums"
          style={{ color: accent }}
        >
          Step {badge}
        </div>
      )}
      <div className="text-[12.5px] font-semibold leading-snug text-ink">
        <InlineText text={node.label} />
      </div>
      {node.sub && (
        <div className="mt-0.5 text-[11px] leading-snug text-graphite">
          <InlineText text={node.sub} />
        </div>
      )}
    </div>
  );
}
