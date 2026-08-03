# Release checklist

Everything below has to pass, in this order, before `./package.sh` runs and the
`dist/` folder goes anywhere. The order is not decorative: the cheap gates fail
in seconds and the expensive one takes an hour, and there is no reason to spend
the hour on a tree that cannot lint.

Push CI runs steps 1–4 on every commit, and `release.yml` now depends on that same
workflow rather than running a subset of it — round 5 was tagged from a commit that
was red in two jobs. Steps 5–7 are the ones a human has to start, and step 6 is the
one this checklist exists for: the only measurement in the repo taken against the
system that actually ships. Steps 5 and 6 leave three committed files behind, and
the tag refuses to publish without all three.

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

## 4. The release artifact builds — and runs

```bash
./src/verify-release-build.sh         # `git archive` still `docker compose build`s
./src/verify-image-smoke.sh           # ...and the image it produced can actually boot
```

Both, because they answer different questions. The first proves the shipped tree
contains everything the Dockerfile needs; the second proves the application
imports and reports `/ready` inside the layout that Dockerfile creates. Round 5
passed the first and failed the second, and published anyway. Ten seconds, no
model required — the assistant answers from its rule-based tier.

## 5. End to end, on the real model — and attested

Ollama has to be running on this machine with `qwen3.5:9b` and `nomic-embed-text`
pulled. The script's preflight checks that before it builds anything and prints
the exact `ollama pull` if not.

```bash
./src/verify-e2e.sh --reset --attest release/evidence/e2e-attestation.json
```

`--attest` writes `{source, inputs, commit, lane, model, ollama_version,
model_digests, checks_run, checks_total, finished_at}` and only on a run that reached
the last check. It refuses `--from` and `--only` outright, before booting anything,
because a resumed run inherits state from an earlier one whose source may differ.
This is what turns "the deployed stack passes its end-to-end suite" from a sentence
in `RELEASE-EVIDENCE.md` into something `release.yml` can check.

**Two bindings, and `commit` is not one of them.** `source` is the tree id of what
the numbers measure; `inputs` is the tree id of everything the release is *made*
of — the workbook under `app/` and the compose stack as well. The gate compares both
and ignores `commit`, which is recorded for a reader and is useless to a gate: it is
the commit the run happened *at*, and by the time this file is committed that is the
parent commit.

That used to be the whole problem. The gate required `commit` to equal the commit
being tagged, and a tag's commit *contains* the attestation — so the file was being
asked to name a commit that did not exist when it was written. Every numeric gate
passed and publication exited 1, permanently, and no amount of re-measuring could
help. Both ids now exclude `release/evidence/`, which makes committing the evidence
unable to move the value the evidence is compared against.

**Which lane to attest.** There is one lane that can carry a release claim, and
the gate accepts only it:

| lane | costs | proves | does not prove |
|---|---|---|---|
| `--reset` — host ollama | ~50 s | every check passes against the 9B on the host's GPU, which is the tier the release ships | anything about a machine with no Ollama installed |
| `--ci` | ~10 min on a runner | the WIRING: retrieval, the gate, containment, discovery, tracing, durability | answer quality — it runs a 1.7B, and the gate refuses it for exactly that reason |

There used to be a second release lane: an in-stack Ollama, accepted as the
*stronger* claim because it needed nothing installed. Retiring it was the point of
this change. That lane ran the 9B on CPU inside a VM at 0.52 tokens/second against
a composer budget raised to fifteen minutes to accommodate it — so what it
actually measured, most of the time, was the offline fallback with a timeout
generous enough to hide the substitution. A lane whose numbers describe a tier the
release does not ship cannot carry the release claim, however self-contained it is.

`--reset` clears the two state volumes, so the durability and tenancy checks
measure this run's writes rather than the last one's. Your pulled models are not
touched: they are yours, and re-downloading six gigabytes per release would prove
nothing. The cold-start question the old lane answered is now answered earlier and
more directly — `preflight-ollama.sh` refuses to start a run whose models are
present but not warm.

## 6. Release-path smoke evidence

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
makes a release metric partly a measurement of the previous test run.

**The run no longer depends on you remembering that.** `make release-evidence` sets
neither `ASSISTANT_DB` nor `QDRANT_COLLECTION`, so `release.py` derives a pair per
run — `evidence/runs/<id>/release.db` and `assistant-release-<id>` — asserts every
stateful table and the collection start empty, refuses to run if they do not, and
removes both afterwards.

Both used to be fixed names, and a fixed name is not a fresh one. `docker compose
down -v` reaches the Qdrant volume but never a host file, so the database survived
every reset: the audited copy held **306 audit rows and 18 memories** from earlier
runs. That moved every number on the page — percentiles against a warm cache,
tenancy against other subjects' memories, containment probes against approvals
granted weeks earlier — and none of it was visible in the output.

Set either variable explicitly and you get exactly what you named, which is what
`--reuse-state` is for. It stamps `state: "reused"` into `release-report.json` and
the publication gate accepts only `"fresh"`, so a diagnosis run cannot become a
release.

This is the measurement a release quotes. It runs against the deployed stack —
Qdrant with the semantic embedder, hybrid retrieval, **reranking on**, a RAGAS
0.4 judge on a pinned model, and all 58 rows of the versioned Phase 6 red-team
dataset including the eleven benign controls. It refuses to run if any component
has fallen back, because a release number produced against the offline proxy is
not a weaker measurement — it is a different one wearing the same heading.

**The rig is full fidelity; the eval suite is not, and the page now says so.** Five
golden rows across two slices (`core`, `abstention`) against the course's own
50-row/five-slice standard, under a `0.60` collapse-detector floor rather than the
0.85 the Phase 3 milestone sets. So the report carries `evidence_class: "smoke"`,
the page is headed *Release-path smoke evidence* and opens with a "What this does not
prove" table, and `check-release-evidence.py` prints the class beside the gate
verdict. The red-team half keeps its full standing — 58 rows, controls included,
every payload delivered on its channel — so read the containment table as evidence
and the eval table as a canary.

That relabelling is the whole fix and it is deliberate. The alternative was writing 45
more golden rows to make the old heading true, which is real work on the eval suite
and not a release blocker; what *was* a defect is a page that read as a certification
while measuring a smoke test.

It also refuses to run without `ASSISTANT_MIN_SCORE`. A store with no relevance
floor returns its three nearest rows for every question and never abstains, so
retrieval metrics gathered against it are measuring a system that cannot do the
thing they are scoring. The `make` target defaults it to the deployed value.

It writes two files:

- `evidence/RELEASE-EVIDENCE.md` — the page, opening with a provenance block
  naming every instrument, and ending with the sha256 of the JSON beside it
- `evidence/release-report.json` — the same run in the gate's shape

Both are gitignored where they land, because `evidence/` belongs to whoever ran it.
Publication needs them committed, so copy them out — next to the attestation step 5
already wrote there:

```bash
mkdir -p ../../../../release/evidence
cp evidence/RELEASE-EVIDENCE.md evidence/release-report.json ../../../../release/evidence/
```

**This copy is not bookkeeping — it is the release gate.** `release.yml` cannot run
this step itself: a hosted runner has four cores and no GPU, which is why the
nightly e2e lane is called *wiring, small model*. So it carries the evidence
instead, and `.github/scripts/check-release-evidence.py` refuses to publish a tag
unless all six of these hold:

1. `versions.source` in the report equals what the tagged tree answers to;
2. the numbers clear the same four merge gates the course teaches — quality,
   safety, latency, cost — imported from `phase8-deploy/02-ci` rather than
   restated in YAML;
3. `RELEASE-EVIDENCE.md` carries the sha256 of that exact `release-report.json`,
   so a page from an older run cannot ride along with fresher numbers;
4. the attestation is bound to the same source and records **every** check run,
   none skipped;
5. the attested lane is the one that runs the real model — and the attestation
   says which Ollama and which model digests served it, since the models now run
   on the releaser's own machine and `qwen3.5:9b` is a mutable pointer;
6. the attestation's `inputs` equals what the tagged tree's release inputs answer
   to — so the workbook and the compose stack are covered too, not only the
   capstone the numbers measure.

Run it yourself before you tag — it is stdlib-only and takes the two ids:

```bash
read -r source inputs < <(cd src/workshops/assistant/after \
  && PYTHONPATH=src python3 -c 'import assistant.provenance as p; print(p.source_id(), p.release_inputs_id())')
python3 .github/scripts/check-release-evidence.py --source "$source" --inputs "$inputs"
```

Ask the tree what it answers to on its own with:

```bash
cd src/workshops/assistant/after
PYTHONPATH=src python3 -c 'import assistant.provenance as p; print(p.source_id(), p.release_inputs_id())'
```

A bare hash means a clean checkout. `dirty-…` means the measurement covers
uncommitted changes and will be refused; `unbound` means it is tied to nothing at
all. Commit the code first, then measure, then commit the evidence — both ids are
hashes of git trees rather than of `HEAD`, and both exclude `release/evidence/`, so
committing the evidence does not invalidate the evidence.

That last clause is the fix for a deadlock, not a convenience. The gate used to also
require the attestation's `commit` to equal the commit being tagged, which nothing
could satisfy: the tag's commit is the one that *adds* the attestation, so the file
had to name its own child. `commit` is still recorded for a reader and no longer
compared to anything.

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
| `e2e (wiring, small model)` | nightly | the composed stack end to end on a 1.7B, on the runner's own Ollama | "the wiring holds" — and the release gate refuses to accept its attestation |
| `verify-e2e.sh --reset` | before a release | every check against the 9B on the host's GPU | "the stack works on the real model" |
| `make release-evidence` | before a release | the deployed stack, RAGAS judge, the whole red team | **the release numbers** |

The row that matters is the last one, and the reason the table exists is that the
second row is the one people quote. `make report` produces a page with the word
"faithfulness" on it in under a second, and for a long time that page was the
only measurement anybody had. Both tiers now print a provenance block naming
their own instruments, in the header rather than the footnotes, so a number
copied out of one cannot be mistaken for a number from the other.
