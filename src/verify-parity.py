#!/usr/bin/env python3
"""Structural parity gate for the companion lessons.

`verify-lessons.sh` proves each lesson *runs* (after green, before red). This proves
each lesson is *shaped* like a lesson, catching the drift that a test run can't:

  1. before/after test files are byte-identical — the scaffold and the reference are
     judged against the same tests, so "make it green" means the same thing on both.
  2. every after/ solution module has a before/ scaffold counterpart, and the before
     tree is not a copy of after (the judgement was actually removed).
  3. every before/ scaffold is genuinely incomplete — it carries TODOs and at least
     one `NotImplementedError`, so a student has something to do.
  4. every `make <target>` a committed workflow invokes actually exists in the
     Makefile that workflow would run against (base targets from _lesson.mk plus the
     lesson's own).

Stdlib only. Exit 0 = clean, 1 = at least one parity violation. Fast: no venvs, no
network, pure file inspection.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_TARGETS = {"setup", "lint", "type", "test", "check", "clean", "test-integration"}
TARGET_RE = re.compile(r"^([A-Za-z0-9_-]+):", re.MULTILINE)
# Only count `make <target>` where it's actually a command: right after `run:`,
# at the start of a (stripped) line, or chained with && / |. This keeps prose like
# "someone would eventually make it optional" out of the target set.
MAKE_INVOKE_RE = re.compile(r"(?:run:\s*|^\s*|&&\s*|\|\s*)make\s+([a-z0-9_-]+)", re.MULTILINE)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def py_files(base: Path) -> set[str]:
    """Paths (relative to `base`) of tracked .py files, ignoring caches."""
    return {
        str(p.relative_to(base))
        for p in base.rglob("*.py")
        if "__pycache__" not in p.parts
    }


def find_lesson_pairs() -> list[Path]:
    """Lesson dirs that hold both a before/ and an after/."""
    pairs = []
    for after in sorted(ROOT.rglob("after")):
        if not after.is_dir() or ".venv" in after.parts:
            continue
        if (after.parent / "before").is_dir():
            pairs.append(after.parent)
    return pairs


def check_tests_match(lesson: Path, fail) -> None:
    before_t, after_t = lesson / "before" / "tests", lesson / "after" / "tests"
    if not after_t.is_dir():
        return  # a lesson may legitimately keep tests elsewhere
    if not before_t.is_dir():
        fail(lesson, "before/tests is missing entirely")
        return
    before_files, after_files = py_files(before_t), py_files(after_t)
    for missing in sorted(after_files - before_files):
        fail(lesson, f"tests/{missing} exists in after/ but not before/")
    for extra in sorted(before_files - after_files):
        fail(lesson, f"tests/{extra} exists in before/ but not after/")
    for name in sorted(before_files & after_files):
        if (before_t / name).read_bytes() != (after_t / name).read_bytes():
            fail(lesson, f"tests/{name} differs between before/ and after/")


def check_scaffold(lesson: Path, fail) -> None:
    before_src, after_src = lesson / "before" / "src", lesson / "after" / "src"
    if not after_src.is_dir() or not before_src.is_dir():
        return
    after_mods = {m for m in py_files(after_src) if not m.endswith("__init__.py")}
    before_mods = py_files(before_src)
    for missing in sorted(after_mods - before_mods):
        fail(lesson, f"src/{missing} has no before/ scaffold")

    identical = all(
        (before_src / m).exists()
        and (before_src / m).read_bytes() == (after_src / m).read_bytes()
        for m in after_mods
    )
    if after_mods and identical:
        fail(lesson, "before/src is byte-identical to after/src — no judgement removed")

    blob = "\n".join(
        (before_src / m).read_text(errors="ignore")
        for m in py_files(before_src)
        if (before_src / m).exists()
    )
    if "TODO" not in blob:
        fail(lesson, "before/src carries no TODO for the student")
    if "NotImplementedError" not in blob:
        fail(lesson, "before/src never raises NotImplementedError — nothing left undone")


def nearest_makefile(start: Path) -> Path | None:
    for parent in [start, *start.parents]:
        if (parent / "Makefile").is_file():
            return parent / "Makefile"
        if parent == ROOT:
            break
    return None


def makefile_targets(makefile: Path) -> set[str]:
    targets = set(BASE_TARGETS)  # every lesson Makefile includes _lesson.mk
    targets |= set(TARGET_RE.findall(makefile.read_text(errors="ignore")))
    return targets


def check_workflow_make_targets(fail) -> None:
    for wf in sorted(ROOT.rglob("*.yml")):
        if ".venv" in wf.parts or "node_modules" in wf.parts:
            continue
        text = wf.read_text(errors="ignore")
        invoked = set(MAKE_INVOKE_RE.findall(text))
        if not invoked:
            continue
        makefile = nearest_makefile(wf.parent)
        if makefile is None:
            fail(wf.parent, f"{rel(wf)} runs make but no Makefile is reachable")
            continue
        available = makefile_targets(makefile)
        for target in sorted(invoked - available):
            fail(
                makefile.parent,
                f"{rel(wf)} runs `make {target}` but {rel(makefile)} defines no such target",
            )


def main() -> int:
    problems: list[tuple[str, str]] = []

    def fail(where: Path, message: str) -> None:
        problems.append((rel(where) if isinstance(where, Path) else str(where), message))

    pairs = find_lesson_pairs()
    exempt = 0
    for lesson in pairs:
        # Diagnosis ("break-and-fix") lessons ship a planted bug and a regression
        # test the reference adds, not TODOs — so before/after tests differ and the
        # scaffold has no NotImplementedError by design. They opt out with a marker.
        if (lesson / ".parity-diagnosis").is_file():
            exempt += 1
            continue
        check_tests_match(lesson, fail)
        check_scaffold(lesson, fail)
    check_workflow_make_targets(fail)

    print(f"parity: inspected {len(pairs)} lesson pairs ({exempt} diagnosis-exempt)")
    if not problems:
        print("parity: OK")
        return 0
    print(f"parity: {len(problems)} violation(s)\n")
    for where, message in problems:
        print(f"  {where}\n      {message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
