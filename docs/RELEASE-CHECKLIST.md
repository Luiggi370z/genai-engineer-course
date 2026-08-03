# Release checklist

Everything below has to pass, in this order, before `./package.sh` runs and the
`dist/` folder goes anywhere. The order is not decorative: the cheap gates fail
in seconds and the expensive one takes an hour, and there is no reason to spend
the hour on a tree that cannot lint.

Push CI runs steps 1–4 on every commit. Steps 5–7 are the ones a human has to
start, and step 6 is the one this checklist exists for — the only measurement in
the repo taken against the system that actually ships.

---

## 1. The fast gates (CI runs these; run them anyway before you tag)

```bash
python3 src/verify-parity.py          # before/after structure and identical tests
./src/verify-lessons.sh               # every after/ lesson: lint, types, fast tests
./src/verify-lessons.sh --before      # every before/ scaffold: green lint, red tests
cd app && pnpm lint && pnpm test && pnpm build && pnpm check-a11y
```

`pnpm build` runs the three content gates (alignment, integrity, density) plus
`check-claims`, `check-doc-links` and `check-effort`; content that fails them cannot
bundle. `check-effort` holds each workshop estimate inside the range its measured
proxies span, so rewriting a brief can invalidate a number and say so — run
`node scripts/check-effort.mjs --report` to see the evidence behind all nine.
`check-claims` also fails on a library pinned two ways or a CI-tier model tag
outside the files that registered it. `check-doc-links` fails when anything in
`src/` points at a document `git archive` would not carry — the check that was
missing when this file's capstone counterpart was ignored by `.gitignore` and left
out of every release while seven references told students to read it.

## 2. The capstone, on its own terms

```bash
cd src/workshops/assistant/after
make check                            # ruff + pyright + the fast test tier
make defect-lab                       # every seeded defect is caught; the fix is green
make gate                             # generate the report, then run the four merge gates
```

## 3. The browser accessibility lane

```bash
cd app && pnpm check-a11y:browser
```

Chromium, both viewports, both themes, full ruleset including `color-contrast`
and `scrollable-region-focusable`. The JSDOM gate in step 1 cannot see either of
those — it has no layout.

## 4. The release artifact builds

```bash
./src/verify-release-build.sh         # `git archive` still `docker compose build`s
```

## 5. End to end, cold, on the real model

```bash
./src/verify-e2e.sh                   # no flags: in-stack ollama, the 9B, ~18 minutes
```

**No flags.** `--host-model` is the local development loop and `--ci` is the
nightly wiring check; neither is the release claim. The claim is that a stranger
clones this repo, runs one command with nothing installed and no keys, and gets a
working system — and only the unqualified lane proves it. Run it against empty
volumes (`docker compose down -v` first) so check 1 measures a first boot rather
than a warm one.

## 6. Full-fidelity evidence

```bash
cd src/phase8-deploy/01-compose/after
docker compose down -v                          # step 5 left a corpus behind
docker compose -f docker-compose.yml -f docker-compose.release.yml up -d
cd ../../../workshops/assistant/after && make release-evidence
```

**`down -v` first, and it is not tidiness.** Step 5 runs `verify-e2e.sh` against
this same Qdrant, and that script ingests a refund policy, an expenses page, an
escalation page, and the poisoned document from the injection check. Anything left
in the collection is part of the corpus the recall number is measured over, which
makes a release metric partly a measurement of the previous test run. `make
release-evidence` also writes to `assistant-release` rather than the shared
`assistant` collection, so the two lanes cannot contaminate each other even when
somebody skips the `down -v`.

This is the measurement a release quotes. It runs against the deployed stack —
Qdrant with the semantic embedder, hybrid retrieval, **reranking on**, a RAGAS
0.4 judge on a pinned model, and all 58 rows of the versioned Phase 6 red-team
dataset including the eleven benign controls. It refuses to run if any component
has fallen back, because a release number produced against the offline proxy is
not a weaker measurement — it is a different one wearing the same heading.

It also refuses to run without `ASSISTANT_MIN_SCORE`. A store with no relevance
floor returns its three nearest rows for every question and never abstains, so
retrieval metrics gathered against it are measuring a system that cannot do the
thing they are scoring. The `make` target defaults it to the deployed value.

It writes two files:

- `evidence/RELEASE-EVIDENCE.md` — the page, opening with a provenance block
  naming every instrument
- `evidence/release-report.json` — the same run in the gate's shape

Both are gitignored where they land, because `evidence/` belongs to whoever ran it.
Publication needs them committed, so copy them out:

```bash
mkdir -p ../../../../release/evidence
cp evidence/RELEASE-EVIDENCE.md evidence/release-report.json ../../../../release/evidence/
```

**This copy is not bookkeeping — it is the release gate.** `release.yml` cannot run
this step itself: a hosted runner has four cores and no GPU, which is why the
nightly e2e lane is called *wiring, small model*. So it reads
`versions.source` out of the committed report and refuses to publish a tag unless
that value equals what the tagged tree answers to. Ask the tree yourself with:

```bash
cd src/workshops/assistant/after
PYTHONPATH=src python3 -c 'import assistant.provenance as p; print(p.source_id())'
```

A bare hash means a clean checkout. `dirty-…` means the measurement covers
uncommitted changes and will be refused; `unbound` means it is tied to nothing at
all. Commit the code first, then measure, then commit the evidence — the id is a
hash of the measured trees rather than of `HEAD`, so committing the evidence does
not invalidate it.

Read both before you believe either. Specifically:

- **`bypasses` must be 0.** One attack reaching a gated tool is a blocking
  finding, not a note.
- **Look at the false positives too.** They do not block, and they are the number
  that tells you whether containment was earned or bought by refusing everything.
  A jump here between releases means the guardrails got scared.
- **Compare against the previous release's JSON**, not against the bars. The bars
  catch a system that is not good enough; a delta catches a system that got
  worse, and slow rot never trips a bar.

Copy `evidence/RELEASE-EVIDENCE.md` into the release notes. A number without the
run that produced it goes back to being a claim.

## 7. Package and verify the artifact

```bash
./package.sh                          # dist/: README, course.html, the src zip, BUILD.json
./verify-dist.sh                      # the ZIP is HEAD, builds, and E2Es without a .git
```

`verify-dist.sh` extracts the archive somewhere with no repository above it and
checks that `verify-e2e.sh` still resolves the release commit from the stamp
`package.sh` baked in. That path had a real bug: the old resolver produced an
empty string outside a checkout and compared it against `dev`.

---

## What each lane is allowed to claim

| lane | runs | measures | may be quoted as |
|---|---|---|---|
| push CI | every commit | structure, types, fast tests, content gates, image builds | "the tree is coherent" |
| `make report` | every commit, one second | an offline proxy: in-memory retrieval, lexical judge, 3 probes | "the harness works" |
| `e2e (wiring, small model)` | nightly | the composed stack end to end on a 1.7B | "the wiring holds" |
| `verify-e2e.sh` | before a release | the same, on the real model, from cold | "one command, no keys, it works" |
| `make release-evidence` | before a release | the deployed stack, RAGAS judge, the whole red team | **the release numbers** |

The row that matters is the last one, and the reason the table exists is that the
second row is the one people quote. `make report` produces a page with the word
"faithfulness" on it in under a second, and for a long time that page was the
only measurement anybody had. Both tiers now print a provenance block naming
their own instruments, in the header rather than the footnotes, so a number
copied out of one cannot be mistaken for a number from the other.
