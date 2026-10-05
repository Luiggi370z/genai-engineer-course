# Changelog

The course version is the `version` field in [`app/package.json`](app/package.json). A release is that number on one commit. When that commit is tagged `vX.Y.Z`, `./package.sh` uses the tag. Otherwise it uses `package.json`.

This file is the record of what changed between those versions. Add new work under **Unreleased**. When you cut a release, give that section the new number and the date, bump `app/package.json`, and commit them together.

## Unreleased

Workshops 2–8 are one assistant, split into phase folders, and the workbook explains that tree on the page.

### Changed

- Workshops 2–8 live in `src/workshops/assistant/phases/`. Each phase has its own `before/` and `after/`. Work in `before/`. Diff that folder's `after/`. `src/workshops/assistant/after` is still the assistant Docker builds.
- `src/workshops/assistant/generator/` writes the phase folders. Students do not work there.
- Each phase folder has a `WORKSHOP.md` that names the one directory for that phase. The assignment brief sits beside that directory.
- Workshop steps are lists in the HTML book: the folder, the files, the command, and what the first failure means.
- The home page has the same on-this-page index as a phase. The order is Prerequisites, How this course works, How to work with workshops, Move on when you clear the bar, Four myths, then What this course does not teach.
- How to work with workshops is highlighted on the home page and linked from every workshop.
- The honesty note under the move-on gates spans the content column.

### Removed

- The pointer `WORKSHOP-*.md` files at `src/workshops/assistant/`. Each brief already lives next to its phase.
- The completion manifest on the home page, and the workbook code that only existed to download `COMPLETION.md`. `make evidence` is unchanged. That command is the Phase 8 workshop log.

### Fixed

- Lesson corrections in the token-cost meter, the CI regression gate, the agent loop, the compose preflight, and the release script.

## 1.0.0 — 2026-08-03

The first complete course: nine phases, nine workshops, and one assistant a student can defend end to end. Audit rounds through round 9 are closed on this commit. The number is `1.0.0` in `app/package.json`. There is no git tag.
