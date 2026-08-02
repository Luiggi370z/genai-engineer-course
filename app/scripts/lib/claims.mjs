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
 * No file names a model tag that competes with the canonical one for its role.
 *
 * `rivals` is authored rather than inferred: only a human knows that
 * `qwen3.6:27b` and `qwen3-coder:30b` are two answers to the same question,
 * while `gemma4:e2b` is a different question entirely. The check catches the
 * case that actually happened — a second judge quietly in use in one lesson,
 * making its scores incomparable with everyone else's.
 */
export function modelFindings({ files, roles }) {
  const out = [];
  for (const { file, source } of files) {
    for (const role of roles) {
      for (const rival of role.rivals ?? []) {
        if (!source.includes(rival)) continue;
        const line = source.slice(0, source.indexOf(rival)).split("\n").length;
        out.push({
          rule: "model-drift",
          subject: `${file}:${line}`,
          message: `uses ${rival} as the ${role.role} model; the course-wide ${role.role} is ${role.tag}`,
        });
      }
    }
  }
  return out;
}
