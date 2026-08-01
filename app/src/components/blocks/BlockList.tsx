import type { Block } from "../../data/types";
import { InlineText } from "../../lib/markdown";
import { Callout } from "./Callout";
import { CodeBlock } from "./CodeBlock";
import { DataTable } from "./DataTable";
import { DeepDive } from "./DeepDive";
import { FlowDiagram } from "./FlowDiagram";
import { PredictBlock } from "./PredictBlock";

/**
 * The one place block kinds are dispatched. A `Block` variant without a case
 * here renders nothing, so this switch must stay exhaustive — the `never` check
 * below makes TypeScript enforce that.
 */
export function BlockList({ blocks, accent }: { blocks: Block[]; accent: string }) {
  return (
    <>
      {blocks.map((block, i) => {
        switch (block.kind) {
          case "p":
            return (
              <p key={i} className="my-3 text-[13.5px] leading-[1.75] text-ink/85">
                <InlineText text={block.text} />
              </p>
            );
          case "list":
            return (
              <ul key={i} className="my-3 space-y-2">
                {block.items.map((item, j) => (
                  <li key={j} className="flex gap-2.5 text-[13.5px] leading-[1.7] text-ink/85">
                    <span
                      className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-sm"
                      style={{ background: accent }}
                    />
                    <span>
                      <InlineText text={item} />
                    </span>
                  </li>
                ))}
              </ul>
            );
          case "code":
            return <CodeBlock key={i} code={block.code} title={block.title} accent={accent} />;
          case "flow":
            return (
              <FlowDiagram
                key={i}
                title={block.title}
                shape={block.shape}
                nodes={block.nodes}
                accent={accent}
              />
            );
          case "table":
            return <DataTable key={i} headers={block.headers} rows={block.rows} accent={accent} />;
          case "callout":
            return <Callout key={i} tone={block.tone} title={block.title} text={block.text} />;
          case "deepdive":
            return <DeepDive key={i} title={block.title} blocks={block.blocks} accent={accent} />;
          case "predict":
            return (
              <PredictBlock
                key={i}
                prompt={block.prompt}
                answer={block.answer}
                consolidation={block.consolidation}
                accent={accent}
              />
            );
          default: {
            const unhandled: never = block;
            return unhandled;
          }
        }
      })}
    </>
  );
}
