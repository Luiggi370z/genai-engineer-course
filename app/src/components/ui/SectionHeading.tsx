interface SectionHeadingProps {
  kicker: string;
  title: string;
  accent: string;
  /** Anchor target for the phase table of contents; also its scroll-spy sentinel. */
  id?: string;
}

export function SectionHeading({ kicker, title, accent, id }: SectionHeadingProps) {
  return (
    <div id={id} className="mt-12 mb-4 scroll-mt-6">
      <div
        className="mb-1 font-mono text-[11px] uppercase tracking-[0.16em]"
        style={{ color: accent }}
      >
        {kicker}
      </div>
      <h2 className="text-[19px] font-bold tracking-tight text-ink">{title}</h2>
    </div>
  );
}
