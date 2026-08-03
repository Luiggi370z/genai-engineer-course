/**
 * Rules for the perishable numbers: hardware tiers, token prices, model tags and
 * the handful of claims that are observations of a moving world.
 *
 * `src/data/reference.ts` is the canonical copy. These rules check that every
 * other statement of the same fact — the two README tables, the `PRICE` dicts in
 * the Python lessons, the model tags in forty-odd defaults — still agrees with
 * it, and that nothing perishable ships without a source and a date.
 *
 * All pure: they take already-read strings, so `claims.test.mjs` can drive them
 * on fixtures and `check-claims.mjs` can feed them the real repo.
 */

/** ISO `YYYY-MM-DD`, and a real date rather than 2026-02-31. */
export function parseIsoDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value ? null : date;
}

/**
 * A `verifiedOn` older than this is reported, not failed.
 *
 * Failing would be worse than useless: it would break the build of a repo nobody
 * changed, on a date nobody chose, and the cheapest way to make it green would be
 * to edit the date rather than re-check the number — which converts an honest
 * staleness signal into a lie. Reporting it puts the work where it belongs.
 */
export const STALE_DAYS = 180;

/**
 * Every claim in the registry has a real source and a real date, and no date is
 * in the future.
 *
 * The future check is not pedantry. A verified-on date ahead of today means the
 * number was typed rather than looked up — it is the single most reliable tell
 * that a citation is decorative.
 */
export function sourceFindings({ claims, today = new Date() }) {
  const out = [];
  const fail = (subject, message) => out.push({ rule: "sourced", subject, message });
  const stale = [];

  for (const claim of claims) {
    const label = claim.id ?? claim.tag ?? claim.vendor ?? "claim";
    const url = claim.source?.url ?? "";
    if (!url) {
      fail(label, "no source — a number without a page to check it against is a rumour");
    } else if (!/^https:\/\/\S+$/.test(url)) {
      fail(label, `source url ${url} is not an https link a reader can open`);
    }
    if (!claim.source?.label) {
      fail(
        label,
        "the source has a url but no label — a bare link says nothing about what it proves",
      );
    }

    const date = parseIsoDate(claim.verifiedOn);
    if (!date) {
      fail(label, `verifiedOn ${JSON.stringify(claim.verifiedOn)} is not a YYYY-MM-DD date`);
      continue;
    }
    if (date.getTime() > today.getTime()) {
      fail(
        label,
        `verifiedOn ${claim.verifiedOn} is in the future — that date was typed, not looked up`,
      );
      continue;
    }
    const age = Math.floor((today.getTime() - date.getTime()) / 86_400_000);
    if (age > STALE_DAYS) stale.push({ label, age, claim: claim.claim ?? claim.vendor ?? label });
  }

  return { errors: out, stale };
}

/**
 * A markdown table between the canonical markers matches the table the registry
 * generates.
 *
 * Regenerating the file would be easier and is deliberately not what happens: a
 * README that a script rewrites is a README nobody reads before committing. This
 * fails with the exact block to paste, which keeps the edit in the author's hands
 * and still makes drift impossible to miss.
 */
export const MARKER = {
  open: "<!-- canonical:hardware -->",
  close: "<!-- /canonical:hardware -->",
};

export function tableFindings({ file, markdown, expected }) {
  const start = markdown.indexOf(MARKER.open);
  const end = markdown.indexOf(MARKER.close);
  if (start === -1 || end === -1) {
    return [
      {
        rule: "canonical-table",
        subject: file,
        message: `no ${MARKER.open} … ${MARKER.close} block — the hardware table here cannot be checked`,
      },
    ];
  }
  const found = markdown.slice(start + MARKER.open.length, end).trim();
  if (found !== expected.trim()) {
    return [
      {
        rule: "canonical-table",
        subject: file,
        message: `the hardware table has drifted from src/data/reference.ts. Replace the block with:\n\n${expected}\n`,
      },
    ];
  }
  return [];
}

/**
 * The `PRICE`-style dicts in the Python lessons agree with `TOKEN_PRICES`.
 *
 * Matches `"model-name": (3.00, 15.00)` — the shape every price table in `src/`
 * uses. A model this does not recognise is ignored rather than failed: the crew
 * and cost-model lessons price illustrative tiers on purpose, and forcing them
 * onto vendor numbers would teach that a made-up tier is a quote.
 */
export function priceFindings({ file, source, prices }) {
  const out = [];
  for (const match of source.matchAll(
    /"([a-z0-9.\-_]+)":\s*\((\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\)/gi,
  )) {
    const [, model, inPrice, outPrice] = match;
    const canonical = prices[model];
    if (!canonical) continue;
    const line = source.slice(0, match.index).split("\n").length;
    if (Number(inPrice) !== canonical.in || Number(outPrice) !== canonical.out) {
      out.push({
        rule: "price-drift",
        subject: `${file}:${line}`,
        message:
          `${model} is priced ($${inPrice}, $${outPrice}) here but ` +
          `($${canonical.in}, $${canonical.out}) in src/data/reference.ts`,
      });
    }
  }
  return out;
}

/**
 * A library the course teaches is pinned to one version range everywhere, and
 * nothing imports the surface that range replaced.
 *
 * The case this exists for: lesson 2.1 pinned `ragas>=0.2,<1` and wrote against
 * `evaluate()` + `EvaluationDataset`, lesson 3.2 pinned `ragas>=0.4,<0.5` and
 * wrote against `ragas.metrics.collections`. Both ran. RAGAS kept the old import
 * path alive behind a DeprecationWarning, so nothing failed — the course simply
 * taught two APIs for one library and gave the reader no way to tell which half
 * was current. A pin that only one lesson respects is not a pin.
 *
 * `retired` is authored per package: it lists import paths the pinned range has
 * moved on from. Substring matching is deliberate — these are import statements
 * in lesson source, not arbitrary prose, and a near-miss here is still a reader
 * copying the wrong API.
 */
export function pinFindings({ manifests, sources = [], packages }) {
  const out = [];
  for (const pkg of packages) {
    const seen = new Map(); // specifier -> [file, ...]
    for (const { file, source } of manifests) {
      // A dependency entry is a quoted string: "ragas>=0.4,<0.5". Anything after
      // the name up to the closing quote is the specifier, empty if unpinned.
      const quoted = source.match(/"[^"]+"/g) ?? [];
      const entry = quoted
        .map((raw) => raw.slice(1, -1))
        .find(
          (dep) =>
            dep.startsWith(pkg.name) &&
            // `ragas` must not match `ragas-experimental`: the next character has
            // to start a version specifier or extra, not more of a name.
            (dep === pkg.name || /^[^A-Za-z0-9._-]/.test(dep.slice(pkg.name.length))),
        )
        ?.slice(pkg.name.length);
      if (entry === undefined) continue;
      seen.set(entry.trim(), [...(seen.get(entry.trim()) ?? []), file]);
    }
    if (seen.size > 1) {
      const shown = [...seen.entries()]
        .map(([spec, files]) => `  ${pkg.name}${spec || " (unpinned)"} — ${files.join(", ")}`)
        .join("\n");
      out.push({
        rule: "pin-drift",
        subject: pkg.name,
        message:
          `pinned ${seen.size} different ways; these lessons teach the same library ` +
          `and must agree:\n${shown}`,
      });
    }

    for (const path of pkg.retired ?? []) {
      for (const { file, source } of sources) {
        if (!source.includes(path)) continue;
        const line = source.slice(0, source.indexOf(path)).split("\n").length;
        out.push({
          rule: "pin-drift",
          subject: `${file}:${line}`,
          message:
            `imports \`${path}\`, which ${pkg.name} ${pkg.pin} has moved on from` +
            (pkg.replacement ? ` — use \`${pkg.replacement}\`` : ""),
        });
      }
    }
  }
  return out;
}

/**
 * No file names a model tag that competes with the canonical one for its role.
 *
 * `rivals` is authored rather than inferred: only a human knows that
 * `qwen3.6:27b` and `qwen3-coder:30b` are two answers to the same question,
 * while `gemma4:e2b` is a different question entirely. The check catches the
 * case that actually happened — a second judge quietly in use in one lesson,
 * making its scores incomparable with everyone else's.
 *
 * A rival can carry an `exempt` list of files. That is how a deliberate second
 * tag stays deliberate: the scheduled E2E lane runs a 1.7B because a hosted
 * runner cannot finish a 9B generation, and the registry says exactly which
 * three files may say so. Name it anywhere else and it is drift again.
 */
export function modelFindings({ files, roles }) {
  const out = [];
  for (const { file, source } of files) {
    for (const role of roles) {
      for (const rival of role.rivals ?? []) {
        const tag = typeof rival === "string" ? rival : rival.tag;
        if (!source.includes(tag)) continue;
        if ((rival.exempt ?? []).includes(file)) continue;
        const line = source.slice(0, source.indexOf(tag)).split("\n").length;
        out.push({
          rule: "model-drift",
          subject: `${file}:${line}`,
          message:
            `uses ${tag} as the ${role.role} model; the course-wide ${role.role} is ${role.tag}` +
            (rival.exempt ? ` (registered for ${rival.exempt.join(", ")} only)` : ""),
        });
      }
    }
  }
  return out;
}

/**
 * Every count of the red-team dataset is the count the dataset has.
 *
 * The number was written into prose in nine places and into the dataset in one,
 * and by round 3 they disagreed twice over: a report still described a 45-case
 * suite that had grown to 58, and three READMEs read "58 rows ... plus 11
 * benign controls" when the 58 already included the controls. Both are the same
 * defect — a number nobody can check without opening a `.jsonl` file.
 *
 * So the dataset is the claim and the prose is a copy. `dataset` carries the
 * totals read off the file; anything restating them has to agree.
 */
export function datasetFindings({ files, dataset }) {
  const expected = {
    rows: dataset.rows,
    attacks: dataset.attacks,
    controls: dataset.controls,
    families: dataset.families,
  };
  // Each pattern names the quantity it is reading, so the failure can say which
  // number is wrong rather than that some number is.
  const patterns = [
    [/(\d+)\s+rows\b/i, "rows", /red.?team|redteam|phase 6 (?:versioned )?dataset/i],
    // The exact shape of the stale claim the round-3 audit found: "45-case".
    [/(\d+)-case\b/i, "rows", /red.?team|redteam|dataset|suite/i],
    [/suite of (?:\*\*)?(\d+) rows/i, "rows", null],
    [/(\d+)\s+benign controls?\b/i, "controls", null],
    [/(\d+)\s+attacks?\s+(?:across|rows)/i, "attacks", null],
    [/(\d+)\s+attack families\b/i, "families", null],
  ];
  const out = [];
  for (const { file, source } of files) {
    source.split("\n").forEach((text, index) => {
      for (const [pattern, quantity, context] of patterns) {
        if (context && !context.test(text)) continue;
        const found = text.match(pattern);
        if (!found) continue;
        const claimed = Number(found[1]);
        if (claimed === expected[quantity]) continue;
        out.push({
          rule: "dataset-drift",
          subject: `${file}:${index + 1}`,
          message:
            `claims ${claimed} ${quantity}; the dataset has ${expected[quantity]} ` +
            `(${dataset.rows} rows = ${dataset.attacks} attacks across ` +
            `${dataset.families} families + ${dataset.controls} benign controls)`,
        });
      }
    });
  }
  return out;
}

/** The totals, read off the dataset itself. `category: "benign"` is a control. */
export function readDataset(jsonl) {
  const rows = jsonl
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line));
  const controls = rows.filter((row) => row.category === "benign");
  return {
    rows: rows.length,
    controls: controls.length,
    attacks: rows.length - controls.length,
    families: new Set(rows.filter((r) => r.category !== "benign").map((r) => r.category)).size,
  };
}
