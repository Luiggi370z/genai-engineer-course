# The GenAI Engineer Workbook — course app

The interactive course. Builds to **one self-contained `course.html`** a student can
open straight from disk: no server, no network (fonts aside), progress in
`localStorage`.

## Commands

```bash
pnpm install
pnpm dev            # dev server with HMR
pnpm build          # -> dist/course.html (single file, JS + CSS inlined)
pnpm verify         # build, then the unit tests, then the a11y gate on the artifact
pnpm lint           # biome (lint + format check)
pnpm format         # biome --write
pnpm typecheck      # tsc --noEmit
pnpm test           # node --test: every gate rule, each proved to fire
pnpm check-alignment          # does the phase teach what it tests
pnpm check-integrity          # is the data well-formed
pnpm check-density            # can a human read it
pnpm check-claims             # do the perishable numbers still agree with each other
pnpm check-a11y               # axe + a keyboard journey through the built page
pnpm check-parity --bundle path/to/course.html   # src/data == a reference bundle
node scripts/screenshot.mjs   # every block kind, light and dark (see below)
```

Releases are cut from the repo root, not from here: `../package.sh` builds the workbook,
cuts the source zip from HEAD and stamps `dist/BUILD.json` with the commit, so all three
artifacts a student receives come from one place.

Every checker takes `--report` to print its measurements rather than just a verdict.
`pnpm build` runs the first four before Vite, so content that is unaligned, malformed,
unreadable or contradicted by its own sources cannot reach a bundle. `check-a11y` runs
after, because it mounts the bundle it is checking.

## Stack

Vite · React 19 · TypeScript (strict) · Tailwind CSS v4 (CSS-first `@theme`) ·
Biome · Hugeicons · `vite-plugin-singlefile`. pnpm only.

## Layout

```
src/
  data/                  all editable content — no JSX in here
    types.ts             the content model (block kinds live here)
    intro.ts             prerequisites, myths, milestones
    dashboard.ts         dashboard copy
    phases/<slug>.ts     one file per phase, keyed by slug
    phases/index.ts      COURSE ORDER — phase numbers derive from this list
  components/
    blocks/              one renderer per block kind + the BlockList dispatcher
    phase/               phase page: concepts, exercises, workshop, questions
    layout/              sidebar, dashboard
    ui/                  progress ring, checkbox row, section heading
  lib/                   inline markdown, progress + theme storage
  styles/index.css       design tokens, dark mode, the paper grid
scripts/
  extract-data.mjs       one-shot recovery of content from a shipped bundle
  check-parity.mjs       proves src/data still matches a reference bundle
  check-alignment.mjs    gate: does the phase teach what it tests
  check-integrity.mjs    gate: is the data well-formed
  check-density.mjs      gate: can a human read it
  screenshot.mjs         photographs every block kind in light and dark
  *.test.mjs             one test per rule, each proving the rule fires
  lib/*.mjs              the rules, as pure functions over course data
  lib/load-data.mjs      compiles src/data with esbuild so scripts read real values
```

## Editing content

Content lives in `src/data/`. Two rules:

1. **Phase numbers are derived from `phases/index.ts` order.** To insert a phase,
   add its file and put it in the list — never hand-edit a number. `id` stays
   stable forever because progress is stored against ids.
2. **Adding a block kind means adding a renderer *and* telling the budget about
   it.** Extend the `Block` union in `types.ts`, add a case in
   `components/blocks/BlockList.tsx` and one in `lib/reading-time.ts` — both are
   exhaustive switches, so TypeScript fails if you forget either. Then add it to
   `PROSE_OF` in `scripts/lib/density.mjs`, which is plain JS and cannot lean on
   the compiler; the `block-kind-known` integrity rule fails the build until you
   do, because a kind the density walk does not know measures as zero and slips
   the budget in silence.

3. **Every card declares what it teaches; every task declares what it tests.**
   `Concept.teaches` and `Exercise.assesses` / `Workshop.assesses` hold objective
   ids, and `needs` names objectives borrowed from *earlier* phases. Both fields
   are required, so a new unannotated card fails `tsc` and a card teaching
   something no exercise tests (or worse, an exercise testing something no card
   taught) fails `pnpm build`.

Text fields support `**bold**`, `*emphasis*` and `` `code` `` and nothing else —
see `lib/markdown.tsx`.

## Three gates, three questions

They are separate scripts because they are separate concerns, and mixing them
would mean a readability complaint blocking a pedagogy fix.

**Alignment — does the phase teach what it tests?** A phase's **objectives are its
spine**: cards teach them, exercises and workshops test them. Objectives open with
a **bolded Bloom verb** because the level decides what counts as assessment —
anything at *apply* or above needs an artifact the student builds, while
*explain*-level objectives can rest on a checkpoint question. The gate also
enforces the worked → faded → independent ladder, and that a prerequisite always
comes from an earlier phase.

**Mastery — does the assessment reach the level the verb promises?** Every
exercise and workshop declares `proves: understand | implement | integrate |
operate`, and each objective verb carries a floor in `MASTERY_FLOOR`. An
objective reading "**Deploy** to a real host" whose only assessment proves
`implement` fails the build — that is the course promising a level it never asks
for. Two details are load-bearing. The floor is keyed by **verb, not Bloom
level**, because the axes come apart at the top: "design out loud" is Bloom's
*create* and produces an argument, so demanding a deploy for a whiteboard
exercise would be the gate being wrong in a way that teaches authors to game it.
And a verb missing from `MASTERY_FLOOR` is itself a failure, since an
unclassified verb would exempt every objective using it — a gate with a silent
pass is not a gate. Exceeding a floor is fine and common: an objective is a
minimum, not a ceiling.

**Integrity — is the data well-formed?** Id uniqueness (ids are `localStorage`
progress keys, so a duplicate silently ties two checkboxes together), ids prefixed
by the phase they live in, `repo:` paths that exist on disk, rectangular tables,
resource urls a browser will actually follow, and content that is not empty behind
a satisfied type. It walks the q-bank, the prerequisites and the electives, which
the alignment gate never had reason to visit.

It also enforces the **checkpoint rubric.** Each spoken checkpoint declares which of
`alternatives`, `constraints`, `evidence` and `failure-modes` its answer has to name,
shown to the student *before* the answer opens — a bar you meet afterwards is one you
grade yourself against. Two elements minimum per question, because one is an
explanation rather than a defense; all four across each phase's set, because the
element candidates omit is `failure-modes`, and a phase that never asks for it is a
phase where the omission gets practised. Not four per question: a rubric that reads
the same on every card stops being read by the third one.

**Density — can a human read it?** Caps on paragraph length, visible prose and
blocks per card, with deep dives as the pressure valve and their own limits so
that valve is not abused.

There is **no escape-hatch list on any of them.** `KNOWN_GAPS` in
`check-alignment.mjs` exists and is empty; a stale entry fails the build too, which
is what stops it becoming a permanent excuse file. Keep it that way — content that
needs an exemption needs an edit.

What the gates cannot check is prose. A card saying "the Phase 5 catalog" is
invisible to all three, so after any renumbering, grep the content for
`Phase [0-9]` and read the hits. Nor can they see colour: a block kind can pass
everything and still be unreadable in dark mode, which is what `screenshot.mjs` is
for.

## Screenshots

`node scripts/screenshot.mjs` drives the built bundle and photographs every block
kind into `screenshots/<theme>/`. Coverage is derived from the course data rather
than listed, and keyed on what actually renders differently — a `flow` is three
renderers and a `callout` is three colour treatments — so a new variant is
photographed without editing the script, and a kind no card uses is reported.

Playwright is deliberately **not** a dependency, since it drags a browser download
behind it and nobody editing content should pay that on `pnpm install`:

```bash
pnpm add -D playwright && pnpm exec playwright install chromium
```

## Provenance

The React source of the original bundle was lost, so the content was recovered
from the shipped `course.html` with `scripts/extract-data.mjs` and the UI rebuilt
from it. `scripts/check-parity.mjs` deep-compares `src/data/` against a reference
bundle and was used to prove the rebuild kept every character of content; run it
against an older `course.html` any time you want that assurance again.

Both take `--bundle` and no longer default to a path, because the repo keeps no
reference bundle: `course.html` is a build output now, and `lib/bundle-data.mjs`
parses only the original minified format, which a current build is not. Point them
at an archived copy of the original.
