import { Fragment } from "react";

/**
 * Deliberately tiny inline renderer: `**bold**`, `*emphasis*` and `` `code` ``.
 *
 * Content is authored against exactly these three markers — anything else is
 * shown literally, which keeps the content files honest about what will render.
 * Every text field that reaches the screen goes through here, so an author never
 * has to remember which fields support the markers. Bold is matched before
 * emphasis, so `**x**` never renders as an italic `*x*` with stray asterisks.
 */
export function InlineText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`]+`)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <strong key={i} className="font-semibold text-ink">
              {part.slice(2, -2)}
            </strong>
          );
        }
        if (part.startsWith("*") && part.endsWith("*")) {
          return (
            <em key={i} className="italic">
              {part.slice(1, -1)}
            </em>
          );
        }
        if (part.startsWith("`") && part.endsWith("`")) {
          return (
            <code
              key={i}
              className="rounded border border-ink/10 bg-ink/[0.07] px-1 py-px font-mono text-[0.86em] text-ink"
            >
              {part.slice(1, -1)}
            </code>
          );
        }
        return <Fragment key={i}>{part}</Fragment>;
      })}
    </>
  );
}
