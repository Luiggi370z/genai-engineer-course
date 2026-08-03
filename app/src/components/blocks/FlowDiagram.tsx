import ArrowRight01Icon from "@hugeicons/core-free-icons/ArrowRight01Icon";
import { HugeiconsIcon } from "@hugeicons/react";
import { Fragment } from "react";
import type { FlowNode, FlowShape } from "../../data/types";
import { FlowCard } from "./FlowCard";
import { CycleFlow, DecisionFlow } from "./FlowShapes";

interface FlowDiagramProps {
  title?: string | undefined;
  shape?: FlowShape | undefined;
  nodes: FlowNode[];
  accent: string;
}

/**
 * A flow, drawn in the shape it actually is.
 *
 * `linear` is the default and stays a flex row of cards — it is the right picture
 * for a pipeline and the shape 17 of the course's diagrams genuinely have. The
 * other two get an SVG connector layer, because a cycle and a branch cannot be
 * drawn as a row without saying something false about them.
 */
export function FlowDiagram({ title, shape = "linear", nodes, accent }: FlowDiagramProps) {
  return (
    <div className="my-4">
      {title && (
        <div className="mb-2 font-mono text-[12px] uppercase tracking-[0.12em] text-graphite">
          {title}
        </div>
      )}
      {shape === "cycle" && <CycleFlow nodes={nodes} accent={accent} />}
      {shape === "decision" && <DecisionFlow nodes={nodes} accent={accent} />}
      {shape === "linear" && (
        <div className="flex flex-wrap items-stretch gap-y-2">
          {nodes.map((node, i) => (
            <Fragment key={node.label}>
              <FlowCard
                node={node}
                accent={accent}
                className="min-w-[140px] max-w-[230px] flex-1"
              />
              {i < nodes.length - 1 && (
                <div className="flex select-none items-center px-1.5" style={{ color: accent }}>
                  <HugeiconsIcon icon={ArrowRight01Icon} size={16} strokeWidth={2} />
                </div>
              )}
            </Fragment>
          ))}
        </div>
      )}
      <div
        className="mt-3 h-px"
        style={{
          background: `linear-gradient(90deg, color-mix(in oklab, ${accent} 20%, transparent), transparent)`,
        }}
      />
    </div>
  );
}
