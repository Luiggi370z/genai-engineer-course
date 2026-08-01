import { useCallback, useEffect, useRef, useState } from "react";

export interface Box {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface Geometry {
  width: number;
  height: number;
  boxes: Box[];
}

function sameGeometry(a: Geometry | null, b: Geometry): boolean {
  if (!a || a.width !== b.width || a.height !== b.height || a.boxes.length !== b.boxes.length) {
    return false;
  }
  return a.boxes.every((box, i) => {
    const next = b.boxes[i];
    if (!next) return false;
    return (
      box.top === next.top &&
      box.left === next.left &&
      box.width === next.width &&
      box.height === next.height
    );
  });
}

/**
 * Where the node cards actually landed, in pixels relative to their container.
 *
 * Read from the DOM rather than authored in the data files, and re-read on every
 * resize. That is the whole reason the shaped diagrams can hold a wrapping text
 * label and still be drawn with real arrows: hand-placed coordinates would have to
 * assume a viewport and a font, and would be wrong on the first phone that opened
 * the page. The connector layer is absolutely positioned, so measuring cannot feed
 * back into layout and loop.
 */
export function useFlowGeometry(count: number) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [geometry, setGeometry] = useState<Geometry | null>(null);

  const setCardRef = useCallback(
    (index: number) => (el: HTMLDivElement | null) => {
      cardRefs.current[index] = el;
    },
    [],
  );

  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;

    const measure = () => {
      const base = root.getBoundingClientRect();
      const cards = cardRefs.current.slice(0, count);
      if (cards.length < count || cards.some((el) => el === null)) return;
      const next: Geometry = {
        width: base.width,
        height: base.height,
        boxes: cards.map((el) => {
          const rect = (el as HTMLDivElement).getBoundingClientRect();
          return {
            top: rect.top - base.top,
            left: rect.left - base.left,
            width: rect.width,
            height: rect.height,
          };
        }),
      };
      setGeometry((prev) => (sameGeometry(prev, next) ? prev : next));
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(root);
    for (const el of cardRefs.current) {
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [count]);

  return { containerRef, setCardRef, geometry };
}

type Point = readonly [number, number];

/**
 * An orthogonal polyline with the corners rounded off, so a return path reads as
 * one continuous route rather than a stack of separate strokes.
 */
export function roundedPath(points: readonly Point[], radius: number): string {
  const first = points[0];
  const last = points[points.length - 1];
  if (!first || !last) return "";

  const d = [`M ${first[0]} ${first[1]}`];
  for (let i = 1; i < points.length - 1; i += 1) {
    const prev = points[i - 1];
    const corner = points[i];
    const next = points[i + 1];
    if (!prev || !corner || !next) continue;

    const inLength = Math.hypot(corner[0] - prev[0], corner[1] - prev[1]);
    const outLength = Math.hypot(next[0] - corner[0], next[1] - corner[1]);
    const r = Math.min(radius, inLength / 2, outLength / 2);
    const entry = towards(corner, prev, r);
    const exit = towards(corner, next, r);
    d.push(`L ${entry[0]} ${entry[1]}`, `Q ${corner[0]} ${corner[1]} ${exit[0]} ${exit[1]}`);
  }
  d.push(`L ${last[0]} ${last[1]}`);
  return d.join(" ");
}

function towards(from: Point, to: Point, distance: number): Point {
  const length = Math.hypot(to[0] - from[0], to[1] - from[1]);
  if (length === 0) return from;
  return [
    from[0] + ((to[0] - from[0]) / length) * distance,
    from[1] + ((to[1] - from[1]) / length) * distance,
  ];
}
