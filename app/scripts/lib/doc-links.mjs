/**
 * Every document the course points at is a document the course ships.
 *
 * The companion zip is `git archive HEAD -- src`, so "shipped" has an exact
 * meaning: tracked by git, under `src/`. Nothing else reaches a student. That
 * makes a dangling reference a packaging fact rather than a matter of taste, and
 * this file is the arithmetic over it.
 *
 * The bug it exists for: `.gitignore` held a bare `docs/`, which matches a
 * directory at any depth, so `src/workshops/assistant/{before,after}/docs/` was
 * ignored along with the repo's own working notes. The capstone's release
 * checklist was therefore never tracked and never packaged, while seven places
 * inside `src/` — both Makefiles, `release.py`'s failure message, two READMEs —
 * told the student to go read it. The instruction survived the file.
 *
 * Kept as pure functions over strings so the rules can be tested on fixtures
 * instead of on the repo, which is the only way to prove the gate fails when it
 * should.
 */

/**
 * Documents the course *produces* rather than ships, by basename.
 *
 * These are outputs, and requiring them to exist would be requiring the course
 * to hand over work it asks the learner to do. Each one is written by a command
 * the material names, at the point the material names it:
 *
 *   - `PORTFOLIO.md`, `EVIDENCE.md` — `make report` in the capstone.
 *   - `RELEASE-EVIDENCE.md` — `make evidence`, into `evidence/`.
 *   - `mock-01.md`, `mock-02.md` — the learner's own copies of
 *     `DESIGN-MOCK-RUBRIC.md`, one per recorded mock interview.
 *
 * A name here that is *also* tracked is a contradiction, and a name here that
 * nothing mentions is dead weight; `producedFindings` reports both, so the list
 * cannot quietly drift out of agreement with the tree.
 */
export const PRODUCED = new Set([
  "PORTFOLIO.md",
  "EVIDENCE.md",
  "RELEASE-EVIDENCE.md",
  "mock-01.md",
  "mock-02.md",
]);

/** A markdown link whose target is a document: `[text](path.md)`, anchor optional. */
const LINK = /\]\(\s*([^)\s]+?\.md)(#[^)\s]*)?\s*\)/g;

/** A path in backticks, the way this material names a file in prose. */
const TICKED = /`([^`\s]+?\.md)`/g;

/**
 * A bare path with a directory in it. Two of the three real dangling references
 * were this shape — a Makefile comment and a Python error message — so prose
 * conventions are not enough to find them.
 *
 * Bare *basenames* outside backticks are deliberately not collected: in code,
 * `"README.md"` is as likely to be a variable's value as a citation, and the
 * material backticks the documents it cites.
 *
 * `$` is in the lookbehind, not just in `addressesSomethingElse`: the capture
 * would start after the sigil and arrive looking like a clean relative path, so
 * `"$BASE/corpus/priority.md"` has to be refused here or not at all.
 */
const BARE_PATH = /(?<![`$\w./-])((?:\.{1,2}\/|[\w.-]+\/)[\w./-]*?\.md)(?![\w-])/g;

/**
 * Shapes that end in `.md` and are still not references to a course document.
 *
 * Each is a path in some *other* namespace, and resolving it against the repo
 * would be a category error:
 *
 *   - `http:`/`https:`/`mailto:` — somewhere else entirely.
 *   - a leading `/` — an HTTP route. `DELETE /corpus/r.md` in the reliability
 *     tests addresses a document in the running assistant's corpus, not a file.
 *   - a leading `~` — outside the checkout by construction:
 *     `cp METRICS-WORKSHEET.md ~/job-search/metrics.md`.
 *   - `$`, `{`, `}` — interpolated at run time, so the literal is not a path:
 *     `"$BASE/corpus/priority.md"` in `verify-e2e.sh`.
 *   - `*` — a glob standing for a set, as in `workshops/assistant/WORKSHOP-*.md`.
 */
function addressesSomethingElse(path) {
  return (
    /^(?:https?|mailto):/.test(path) ||
    path.startsWith("/") ||
    path.startsWith("~") ||
    /[${}*]/.test(path)
  );
}

/** Every document reference in one file, deduplicated, in first-seen order. */
export function referencesIn(file, source) {
  const seen = new Map();
  for (const pattern of [LINK, TICKED, BARE_PATH]) {
    // `matchAll` on a shared global regex is safe — it clones the lastIndex.
    for (const [, path] of source.matchAll(pattern)) {
      if (addressesSomethingElse(path)) continue;
      if (!seen.has(path)) seen.set(path, { file, path });
    }
  }
  return [...seen.values()];
}

/** Files whose presence marks a directory as somewhere a student runs commands. */
const RUN_ROOT = new Set(["pyproject.toml", "Makefile"]);

/**
 * The nearest ancestor of `file` that a student would have as their working
 * directory, or `null` if there is none.
 *
 * Derived from the shipped set rather than assumed, so it tracks the lesson
 * layout instead of a copy of it.
 */
function runRoot(file, shipped) {
  const parts = file.split("/");
  for (let cut = parts.length - 1; cut > 0; cut--) {
    const dir = parts.slice(0, cut).join("/");
    for (const marker of RUN_ROOT) if (shipped.has(`${dir}/${marker}`)) return dir;
  }
  return null;
}

/**
 * Where a reference is allowed to resolve from.
 *
 * Three bases, because the material legitimately writes paths from three
 * different places and all three are correct for the reader who meets them:
 *
 *  1. The file's own directory — what a relative path means in a rendered
 *     markdown link, and what someone browsing the tree will do.
 *  2. The nearest run root, because *a path written inside a program is relative
 *     to where the program runs*. `release.py` lives at `after/src/assistant/`
 *     and says `docs/RELEASE-CHECKLIST.md`; the student reading that message ran
 *     `make evidence` from `after/`, where it is exactly right. The same holds
 *     for the lesson docstring that points at `../after/README.md` from
 *     `before/src/rag.py` — from `before/`, where `make test` is run, it lands.
 *  3. `src/`, for cross-lesson paths written from the source root, which is also
 *     the zip's root: `workshops/assistant/after/docs/RELEASE-CHECKLIST.md`,
 *     cited from a lesson three directories away.
 */
function candidates(file, path, shipped) {
  const from = file.slice(0, file.lastIndexOf("/"));
  const root = runRoot(file, shipped);
  const bases = root && root !== from ? [from, root, "src"] : [from, "src"];
  return [...new Set(bases.map((base) => normalise(`${base}/${path}`)))];
}

/** Resolve `.` and `..` without touching the filesystem. */
function normalise(path) {
  const out = [];
  for (const part of path.split("/")) {
    if (part === "" || part === ".") continue;
    if (part === ".." && out.length && out.at(-1) !== "..") out.pop();
    else out.push(part);
  }
  return out.join("/");
}

/**
 * References that point at nothing a student will have.
 *
 * `shipped` is the set of repo-relative paths that reach the zip, which the
 * caller reads from git rather than from the filesystem. The distinction is the
 * whole point: the checklist existed on disk the entire time it was missing from
 * every release.
 */
export function referenceFindings(files, shipped) {
  const names = basenames(shipped);
  const out = [];
  for (const { file, source } of files) {
    for (const { path } of referencesIn(file, source)) {
      const basename = path.slice(path.lastIndexOf("/") + 1);
      if (PRODUCED.has(basename)) continue;

      // A bare name is a name, not a route. "diagrams in `ARCHITECTURE.md`" and
      // "a `VERIFIED.md` stamp saying when it last passed" are prose about a
      // document — in the second case about eleven of them, one per phase — and
      // demanding they resolve from the mentioning file would be demanding they
      // be rewritten as links they were never trying to be. What is still worth
      // failing on is naming a document that ships nowhere at all.
      if (!path.includes("/")) {
        if (names.has(basename)) continue;
        out.push({
          rule: "doc-name",
          subject: file,
          message:
            `names "${basename}", and no file in the zip is called that. Either ` +
            "the name is wrong, or the document is untracked and `git archive` " +
            "will skip it.",
        });
        continue;
      }

      const tried = candidates(file, path, shipped);
      if (tried.some((candidate) => shipped.has(candidate))) continue;
      out.push({
        rule: "doc-link",
        subject: file,
        message:
          `points at "${path}", which does not reach the zip — tried ` +
          `${tried.map((t) => `"${t}"`).join(", ")}. Either the path is wrong, ` +
          "or the file is untracked and `git archive` will skip it.",
      });
    }
  }
  return out;
}

/** Every filename in the zip, without its directory. */
function basenames(shipped) {
  return new Set([...shipped].map((p) => p.slice(p.lastIndexOf("/") + 1)));
}

/** The `PRODUCED` list, held to its own claims. */
export function producedFindings(files, shipped) {
  const mentioned = new Set();
  for (const { file, source } of files) {
    for (const { path } of referencesIn(file, source)) {
      mentioned.add(path.slice(path.lastIndexOf("/") + 1));
    }
  }
  const tracked = basenames(shipped);

  const out = [];
  for (const name of PRODUCED) {
    if (tracked.has(name))
      out.push({
        rule: "produced",
        subject: name,
        message:
          "is listed as a document the course produces, but it is tracked and " +
          "shipped — drop it from PRODUCED so real breakage in it is caught.",
      });
    else if (!mentioned.has(name))
      out.push({
        rule: "produced",
        subject: name,
        message: "is listed in PRODUCED but nothing under src/ mentions it — stale entry.",
      });
  }
  return out;
}
