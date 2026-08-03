import { InlineText } from "../../lib/markdown";
import { ScrollRegion } from "../ui/ScrollRegion";

interface DataTableProps {
  headers: string[];
  rows: string[][];
  accent: string;
}

export function DataTable({ headers, rows, accent }: DataTableProps) {
  return (
    // Named after its first column, which is what a table in this workbook is
    // keyed by — "Table: model" tells a screen-reader user which of the four
    // tables on the page they just tabbed into.
    <ScrollRegion
      label={`Table: ${headers[0] || "data"}`}
      className="my-4 overflow-x-auto rounded-md border border-line"
    >
      <table className="w-full border-collapse text-left">
        <thead>
          <tr style={{ background: `color-mix(in oklab, ${accent} 8%, transparent)` }}>
            {headers.map((header) => (
              <th
                key={header}
                className="whitespace-nowrap px-3 py-2 font-mono text-[11px] uppercase tracking-[0.1em]"
                style={{ color: accent }}
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r} className={r % 2 ? "bg-ink/[0.02]" : "bg-card"}>
              {row.map((cell, c) => (
                <td
                  key={c}
                  className={`border-t border-line/70 px-3 py-2 text-[12.5px] leading-snug ${
                    c === 0 ? "font-semibold text-ink" : "text-ink/80"
                  }`}
                >
                  <InlineText text={cell} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </ScrollRegion>
  );
}
