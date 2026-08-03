import { useMemo, useRef, useState } from "react";
import type { Phase } from "../../data/types";
import {
  buildCompletion,
  type EvidenceManifest,
  parseEvidence,
  renderCompletion,
} from "../../lib/manifest.ts";
import type { Progress } from "../../lib/progress";

interface ManifestPanelProps {
  phases: Phase[];
  progress: Progress;
}

const STANDING_COPY = {
  "self-reported": {
    label: "self-reported",
    tone: "var(--color-graphite)",
    say: "Everything below is a claim you made about your own work. Attach an evidence file and the ones a command can prove will say so.",
  },
  "partly-evidenced": {
    label: "partly evidenced",
    tone: "var(--color-graphite)",
    say: "Some claims are backed by artifacts your own commands produced. The rest are listed with the command that would close them.",
  },
  // Named for what it can actually check. The previous label was
  // "evidence-backed" and the line under it said every claim here is backed by a
  // file — but the two halves of this standing are unconnected: the workbook items
  // are your own ticks and the manifest proves the COURSE's claims about its own
  // reference implementation. No item on this page maps to a claim in that file, so
  // "every claim here is backed" was overstating a real thing into a false one.
  "course-evidence-attached": {
    label: "course evidence attached",
    tone: "var(--color-ink)",
    say: "Every item is ticked — your claims about your own work — and the course's evidence manifest is attached and complete. Those are two separate facts: the manifest proves the reference implementation's claims, not your items.",
  },
} as const;

/**
 * The manifest, and the reason it is not just a progress bar with a border.
 *
 * Ticking a box is a claim. A page built only from claims reads identically for
 * someone who did the work and someone who clicked through, so the standing line
 * at the top can only be lifted by attaching `evidence/manifest.json` from
 * `make evidence` — never by ticking more boxes.
 */
export function ManifestPanel({ phases, progress }: ManifestPanelProps) {
  const [evidence, setEvidence] = useState<EvidenceManifest | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const completion = useMemo(
    () => buildCompletion(phases, progress, evidence),
    [phases, progress, evidence],
  );
  const copy = STANDING_COPY[completion.standing];

  const attach = (file: File) => {
    void file.text().then((raw) => {
      const parsed = parseEvidence(raw);
      if (!parsed) {
        setProblem("That is not an evidence manifest. Look for evidence/manifest.json.");
        return;
      }
      setProblem(null);
      setEvidence(parsed);
    });
  };

  const download = () => {
    const blob = new Blob([renderCompletion(completion)], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "COMPLETION.md";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section aria-labelledby="manifest-heading" className="mt-10">
      <h2 id="manifest-heading" className="text-[15px] font-semibold text-ink">
        Completion manifest
      </h2>
      <p className="mt-1 max-w-[68ch] text-[13px] leading-[1.7] text-graphite">
        One page for a reader who was not here: what you finished, and how much of it a stranger can
        verify. Those are separate columns on purpose — a manifest that merged them would be a
        certificate you issued to yourself.
      </p>

      <div className="mt-3 rounded-lg border border-line bg-card p-4">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span
            className="font-mono text-[12px] uppercase tracking-[0.14em]"
            style={{ color: copy.tone }}
          >
            {copy.label}
          </span>
          <span className="font-mono text-[12px] text-graphite">
            {completion.ticked}/{completion.total} workbook items
          </span>
          {evidence && (
            <span className="font-mono text-[12px] text-graphite">
              {evidence.proven}/{evidence.total} claims proven
            </span>
          )}
        </div>
        <p className="mt-2 max-w-[68ch] text-[12.5px] leading-relaxed text-ink/80">{copy.say}</p>

        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => fileInput.current?.click()}
            className="rounded border border-line px-3 py-1.5 font-mono text-[12px] text-ink hover:bg-ink/4"
          >
            Attach evidence/manifest.json
          </button>
          <input
            ref={fileInput}
            type="file"
            accept="application/json,.json"
            className="sr-only"
            aria-label="Attach the evidence manifest written by make evidence"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) attach(file);
              event.target.value = "";
            }}
          />
          <button
            type="button"
            onClick={download}
            className="rounded border border-line px-3 py-1.5 font-mono text-[12px] text-ink hover:bg-ink/4"
          >
            Download COMPLETION.md
          </button>
          <button
            type="button"
            onClick={() => {
              void navigator.clipboard?.writeText(renderCompletion(completion)).then(() => {
                setCopied(true);
                window.setTimeout(() => setCopied(false), 2000);
              });
            }}
            className="rounded border border-line px-3 py-1.5 font-mono text-[12px] text-ink hover:bg-ink/4"
          >
            {copied ? "Copied" : "Copy as markdown"}
          </button>
        </div>

        <p aria-live="polite" className="mt-2 text-[12px] text-graphite">
          {problem ??
            (evidence
              ? `Evidence generated ${evidence.generated_on}.`
              : "No evidence attached. Run `make evidence` in workshops/assistant/after.")}
        </p>
      </div>
    </section>
  );
}
