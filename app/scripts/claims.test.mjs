import assert from "node:assert/strict";
import test from "node:test";
import {
  MARKER,
  modelFindings,
  parseIsoDate,
  priceFindings,
  STALE_DAYS,
  sourceFindings,
  tableFindings,
} from "./lib/claims.mjs";

const TODAY = new Date("2026-08-01T00:00:00Z");
const ok = {
  id: "mcp-servers",
  claim: "~10,000 public MCP servers",
  source: {
    label: "MCP servers directory",
    url: "https://github.com/modelcontextprotocol/servers",
  },
  verifiedOn: "2026-07-28",
};

const errorsFor = (claim) => sourceFindings({ claims: [claim], today: TODAY }).errors;

test("a real date parses and an impossible one does not", () => {
  assert.ok(parseIsoDate("2026-08-01"));
  assert.equal(parseIsoDate("2026-02-31"), null);
  assert.equal(parseIsoDate("1 Aug 2026"), null);
  assert.equal(parseIsoDate(undefined), null);
});

test("a sourced, dated claim passes", () => {
  assert.deepEqual(errorsFor(ok), []);
});

test("a claim with no source is a rumour with a decimal point", () => {
  const [finding] = errorsFor({ ...ok, source: undefined });
  assert.match(finding.message, /no source/);
});

test("an unopenable source is caught", () => {
  assert.equal(errorsFor({ ...ok, source: { label: "notes", url: "internal-wiki" } }).length, 1);
});

test("a bare link with no label is caught", () => {
  const [finding] = errorsFor({ ...ok, source: { url: "https://example.com" } });
  assert.match(finding.message, /no label/);
});

test("a future verified-on date is the tell that it was typed, not looked up", () => {
  const [finding] = errorsFor({ ...ok, verifiedOn: "2026-12-25" });
  assert.match(finding.message, /in the future/);
});

test("a malformed date fails once, not twice", () => {
  const findings = errorsFor({ ...ok, verifiedOn: "soon" });
  assert.equal(findings.length, 1);
  assert.match(findings[0].message, /not a YYYY-MM-DD date/);
});

test("an old claim is reported as stale, never failed", () => {
  const old = { ...ok, verifiedOn: "2025-01-01" };
  const { errors, stale } = sourceFindings({ claims: [old], today: TODAY });
  // Failing here would break a build nobody touched, on a date nobody chose, and
  // the cheapest way to green would be editing the date rather than the number.
  assert.deepEqual(errors, []);
  assert.equal(stale.length, 1);
  assert.ok(stale[0].age > STALE_DAYS);
});

test("a table that matches the registry passes; one that drifted does not", () => {
  const expected = "| Tier |\n| --- |\n| 16 GB |";
  const good = `intro\n${MARKER.open}\n${expected}\n${MARKER.close}\nrest`;
  assert.deepEqual(tableFindings({ file: "README.md", markdown: good, expected }), []);

  const drifted = `intro\n${MARKER.open}\n| Tier |\n| --- |\n| 8 GB |\n${MARKER.close}`;
  const [finding] = tableFindings({ file: "README.md", markdown: drifted, expected });
  assert.match(finding.message, /has drifted/);
  // The fix is printed, because a gate that only says "wrong" gets worked around.
  assert.ok(finding.message.includes(expected));
});

test("a file with no markers cannot be checked, and says so", () => {
  const [finding] = tableFindings({ file: "README.md", markdown: "no table here", expected: "x" });
  assert.match(finding.message, /cannot be checked/);
});

test("a price that disagrees with the registry is caught, with its line", () => {
  const source = ["PRICE = {", '    "gpt-5.5": (5.00, 42.00),', "}"].join("\n");
  const [finding] = priceFindings({
    file: "meter.py",
    source,
    prices: { "gpt-5.5": { in: 5.0, out: 30.0 } },
  });
  assert.equal(finding.subject, "meter.py:2");
  assert.match(finding.message, /\$42.*\$30/s);
});

test("a matching price is silent, whatever the decimal spelling", () => {
  assert.deepEqual(
    priceFindings({
      file: "meter.py",
      source: '"gpt-5.5": (5, 30.0)',
      prices: { "gpt-5.5": { in: 5.0, out: 30.0 } },
    }),
    [],
  );
});

test("illustrative tiers are left alone, because they are not quotes", () => {
  // The crew and cost-model lessons price made-up tiers on purpose. Forcing them
  // onto vendor numbers would teach that an invented tier is a quote.
  assert.deepEqual(
    priceFindings({
      file: "crew.py",
      source: '"local": (0.0, 0.0), "cheap": (1.0, 5.0), "frontier": (5.0, 25.0)',
      prices: { "gpt-5.5": { in: 5.0, out: 30.0 } },
    }),
    [],
  );
});

test("a second model for a role that already has one is caught", () => {
  const roles = [{ role: "judge", tag: "qwen3-coder:30b", rivals: ["qwen3.6:27b"] }];
  const [finding] = modelFindings({
    files: [{ file: "ragas_eval.py", source: 'def local_judge(model="qwen3.6:27b"):' }],
    roles,
  });
  assert.match(finding.message, /course-wide judge is qwen3-coder:30b/);
});

test("the canonical tag itself is not a rival of itself", () => {
  const roles = [{ role: "judge", tag: "qwen3-coder:30b", rivals: ["qwen3.6:27b"] }];
  assert.deepEqual(
    modelFindings({ files: [{ file: "judge.py", source: 'DEFAULT = "qwen3-coder:30b"' }], roles }),
    [],
  );
});
