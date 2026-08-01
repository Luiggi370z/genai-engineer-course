import { Fragment, type ReactNode } from "react";

const PYTHON_KEYWORDS =
  /\b(def|class|return|if|else|elif|for|while|import|from|in|not|and|or|None|True|False|with|as|try|except|raise|async|await|lambda|assert|pass)\b/g;

/**
 * A deliberately small highlighter — strings, keywords, comments.
 *
 * A real tokeniser would add ~40 KB to a bundle whose whole point is being one
 * portable file, and the snippets are short and mostly Python.
 */
function highlightKeywords(fragment: string, key: number): ReactNode {
  const parts = fragment.split(PYTHON_KEYWORDS);
  return (
    <Fragment key={key}>
      {parts.map((part, i) =>
        // split() with a capturing group puts the matches at the odd indices.
        i % 2 === 1 ? (
          <span key={i} className="text-terminal-keyword">
            {part}
          </span>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        ),
      )}
    </Fragment>
  );
}

function highlightStrings(line: string): ReactNode[] {
  const out: ReactNode[] = [];
  let rest = line;
  let key = 0;
  while (rest.length > 0) {
    const match = rest.match(/("[^"]*"|'[^']*')/);
    if (!match || match.index === undefined) {
      out.push(highlightKeywords(rest, key++));
      break;
    }
    if (match.index > 0) out.push(highlightKeywords(rest.slice(0, match.index), key++));
    out.push(
      <span key={key++} className="text-terminal-string">
        {match[0]}
      </span>,
    );
    rest = rest.slice(match.index + match[0].length);
  }
  return out;
}

function isInsideQuotes(line: string, index: number): boolean {
  let quotes = 0;
  for (let i = 0; i < index; i++) {
    if (line[i] === '"' || line[i] === "'") quotes++;
  }
  return quotes % 2 === 1;
}

function highlightLine(line: string): ReactNode {
  const hash = line.indexOf("#");
  if (hash < 0 || isInsideQuotes(line, hash)) return highlightStrings(line);
  return (
    <>
      {highlightStrings(line.slice(0, hash))}
      <span className="text-terminal-comment italic">{line.slice(hash)}</span>
    </>
  );
}

interface CodeBlockProps {
  code: string;
  title?: string | undefined;
  accent: string;
}

export function CodeBlock({ code, title, accent }: CodeBlockProps) {
  return (
    <div className="my-4 overflow-hidden rounded-md border border-line shadow-sm">
      {title && (
        <div className="flex items-center gap-2 border-b border-white/10 bg-terminal-bar px-3.5 py-2">
          <span className="h-2 w-2 rounded-full" style={{ background: accent }} />
          <span className="font-mono text-[11px] tracking-wide text-white/60">{title}</span>
        </div>
      )}
      <pre className="overflow-x-auto bg-terminal-bg px-4 py-3.5 font-mono text-[12.5px] leading-[1.65] text-terminal-fg">
        {code.split("\n").map((line, i) => (
          <div key={i} className="whitespace-pre">
            {highlightLine(line)}
          </div>
        ))}
      </pre>
    </div>
  );
}
