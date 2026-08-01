import { useId } from "react";
import type { FlowNode } from "../../data/types";
import { FlowCard } from "./FlowCard";
import { type Box, type Geometry, roundedPath, useFlowGeometry } from "./flow-geometry";

interface ShapeProps {
  nodes: FlowNode[];
  accent: string;
}

/** Left gutter the return path and the branch spine run in. */
const GUTTER = 40;
/** Where in that gutter the vertical run sits. */
const CHANNEL = 14;
/** Room below the last card for the return path to turn in. */
const TAIL = 14;
const CORNER = 8;
/** Gap between an arrowhead and the card edge it points at. */
const STANDOFF = 6;

function ArrowMarker({ id, accent }: { id: string; accent: string }) {
  return (
    <defs>
      <marker
        id={id}
        viewBox="0 0 8 8"
        refX="7"
        refY="4"
        markerWidth="7"
        markerHeight="7"
        orient="auto"
      >
        <path d="M 0 0 L 8 4 L 0 8 z" fill={accent} fillOpacity={0.7} />
      </marker>
    </defs>
  );
}

function ConnectorLayer({
  geometry,
  accent,
  paths,
}: {
  geometry: Geometry;
  accent: string;
  paths: string[];
}) {
  const markerId = useId();
  return (
    <svg
      className="pointer-events-none absolute inset-0"
      width={geometry.width}
      height={geometry.height}
      aria-hidden="true"
    >
      <ArrowMarker id={markerId} accent={accent} />
      <g
        fill="none"
        stroke={accent}
        strokeOpacity={0.55}
        strokeWidth={1.5}
        markerEnd={`url(#${markerId})`}
      >
        {paths.map((d) => (
          <path key={d} d={d} />
        ))}
      </g>
    </svg>
  );
}

/**
 * Steps that come back round, drawn as an actual closed ring.
 *
 * The linear renderer put a loop on a straight line and let it dead-end, which told
 * the student the opposite of the point: `The calibration loop` ends by re-running
 * the thing it began with, and a diagram that stops at the last box says the work is
 * finished. There is no entry arrow, for the same reason — you can pick a loop up
 * anywhere, which is what makes it a loop.
 */
export function CycleFlow({ nodes, accent }: ShapeProps) {
  const { containerRef, setCardRef, geometry } = useFlowGeometry(nodes.length);

  return (
    <div
      ref={containerRef}
      className="relative"
      style={{ paddingLeft: GUTTER, paddingBottom: TAIL }}
    >
      {geometry && (
        <ConnectorLayer geometry={geometry} accent={accent} paths={cyclePaths(geometry)} />
      )}
      <div className="flex flex-col gap-6">
        {nodes.map((node, i) => (
          <FlowCard
            key={node.label}
            ref={setCardRef(i)}
            node={node}
            accent={accent}
            badge={i + 1}
          />
        ))}
      </div>
    </div>
  );
}

function cyclePaths(geometry: Geometry): string[] {
  const { boxes, height } = geometry;
  const first = boxes[0];
  const last = boxes[boxes.length - 1];
  if (!first || !last) return [];

  const stem = first.left + 26;
  const paths = boxes.slice(0, -1).map((box, i) => {
    const next = boxes[i + 1];
    return next ? `M ${stem} ${box.top + box.height + 2} L ${stem} ${next.top - STANDOFF}` : "";
  });

  paths.push(
    roundedPath(
      [
        [stem, last.top + last.height + 2],
        [stem, height - 3],
        [CHANNEL, height - 3],
        [CHANNEL, firstLine(first)],
        [first.left - STANDOFF, firstLine(first)],
      ],
      CORNER,
    ),
  );
  return paths.filter(Boolean);
}

/**
 * One question, and the branches it can go down — none of which leads to the next.
 *
 * The linear renderer chained these with arrows, which turned five independent
 * "first match wins" conditions into a pipeline running from the first option
 * through to the last, and turned approve / edit / reject into a sequence you
 * perform in order. Branches hang off a spine instead: the stem is `nodes[0]`, and
 * everything after it is an alternative to everything else after it.
 */
export function DecisionFlow({ nodes, accent }: ShapeProps) {
  const { containerRef, setCardRef, geometry } = useFlowGeometry(nodes.length);
  const [stem, ...branches] = nodes;
  if (!stem) return null;

  return (
    <div ref={containerRef} className="relative">
      {geometry && (
        <ConnectorLayer geometry={geometry} accent={accent} paths={decisionPaths(geometry)} />
      )}
      <FlowCard ref={setCardRef(0)} node={stem} accent={accent} />
      <div className="mt-3 flex flex-col gap-2.5" style={{ paddingLeft: GUTTER }}>
        {branches.map((node, i) => (
          <FlowCard
            key={node.label}
            ref={setCardRef(i + 1)}
            node={node}
            accent={accent}
            edge="left"
          />
        ))}
      </div>
    </div>
  );
}

function decisionPaths(geometry: Geometry): string[] {
  const [stem, ...branches] = geometry.boxes;
  const last = branches[branches.length - 1];
  if (!stem || !last) return [];

  const spineTop = stem.top + stem.height + 2;
  // The final branch is drawn as one elbow off the spine rather than a tick crossing
  // it, so the spine ends in a turn instead of a stub hanging past the last branch.
  const paths = [
    roundedPath(
      [
        [CHANNEL, spineTop],
        [CHANNEL, firstLine(last)],
        [last.left - STANDOFF, firstLine(last)],
      ],
      CORNER,
    ),
  ];
  for (const box of branches.slice(0, -1)) {
    paths.push(`M ${CHANNEL} ${firstLine(box)} L ${box.left - STANDOFF} ${firstLine(box)}`);
  }
  return paths;
}

/**
 * Pinned to the first line of a card rather than its centre, so a branch whose
 * sub-label wraps to three lines keeps its arrow next to the condition it points at.
 */
function firstLine(box: Box): number {
  return box.top + Math.min(box.height / 2, 18);
}
