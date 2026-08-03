import { formatPct } from "../../lib/progress";

interface ProgressRingProps {
  /** 0–1. */
  pct: number;
  color: string;
  size?: number;
}

export function ProgressRing({ pct, color, size = 30 }: ProgressRingProps) {
  const radius = (size - 5) / 2;
  const circumference = 2 * Math.PI * radius;
  return (
    <svg
      width={size}
      height={size}
      className="shrink-0 -rotate-90"
      role="img"
      aria-label={`${formatPct(pct)} complete`}
    >
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="var(--color-line)"
        strokeWidth="3"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth="3"
        strokeDasharray={circumference}
        strokeDashoffset={circumference * (1 - pct)}
        strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 0.4s ease" }}
      />
    </svg>
  );
}
