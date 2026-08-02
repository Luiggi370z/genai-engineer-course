/**
 * The citation line under a perishable claim: when it was checked, and where to
 * check it yourself.
 *
 * Rendered quietly — small, grey, no border — because it is not part of the
 * argument. But it is rendered *always*, including when it is embarrassing: a
 * price verified eleven months ago says "eleven months ago" rather than nothing,
 * and the reader gets to decide what that is worth. Hiding an old date is how a
 * workbook ends up being quoted as current.
 */
export function SourceNote({
  verifiedOn,
  items,
}: {
  verifiedOn: string;
  items: { label: string; url: string }[];
}) {
  return (
    <p className="my-2.5 text-[11.5px] leading-relaxed text-graphite">
      <span className="font-mono uppercase tracking-[0.1em]">Verified {verifiedOn}</span>
      {" · "}
      {items.map((item, i) => (
        <span key={item.url}>
          {i > 0 && " · "}
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer"
            className="underline decoration-line underline-offset-2 hover:text-ink"
          >
            {item.label}
          </a>
        </span>
      ))}
    </p>
  );
}
