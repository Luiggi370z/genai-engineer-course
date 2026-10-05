# How to work with workshops

Every phase ends in a workshop. The lessons above it are short and standalone:
each one has its own `before/` and its own `after/`. Workshops 2 through 8 are
different. They are one assistant that grows. You finish with one system, and
each phase adds the next piece of it.

Each phase folder has a `WORKSHOP.md` that names the one place you open for
that phase. Start there if you are browsing by phase. This page is the map.

## The folders

| You open this | What it is |
|---|---|
| `workshops/model-bench/before` | Workshop 1. Its own project. |
| `workshops/assistant/phases/<id>/before` | Workshops 2–8. One folder per step. This is where you edit. |
| `workshops/assistant/phases/<id>/after` | The same folder with your files finished. Diff against it when you are stuck. |
| `workshops/assistant/after` | The finished assistant. Compose builds this. The defect lab runs here, and only then. |
| `workshops/assistant/generator` | Tooling that writes `phases/`. Leave it alone. |
| `workshops/interview-loop` | Workshop 9. No code. |

`phases/README.md` is the index: one row per folder, the files you edit, and
the test that fails first.

## The flow

1. Finish the lessons in the phase. A lesson `before/` is a small exercise. A workshop `before/` is the next piece of the assistant.
2. Open the phase's `WORKSHOP.md`, then the folder it names.
3. Read that folder's `README.md`. It names the files you edit and the first test that fails.
4. Read the brief beside that folder (`WORKSHOP-*.md`). It is the longer assignment: what you are building, what you are skipping, and when you are done. The course page already contains the steps.
5. From that `before/` folder, run `make setup`, then `make test`.
6. `make test` runs only the tests in that folder. From the eval workshop on, earlier workshops' tests are included and they stay green. A failure in a file the README does not name means you are in the wrong folder.
7. Fix the files the README names. When `make test` is green, or you are stuck, diff only those files against the same paths in that folder's `after/`.
8. Go to the next phase folder. You do not copy the tree forward. The next `before/` already contains the earlier work as finished code.
9. Phase 8 is six folders, in the order `WORKSHOP.md` lists: trace, corpus, reliability, service, auth, evidence. Then the defect lab.
10. The defect lab runs in `workshops/assistant/after`. Copy `phases/09-defect-lab/test_regressions.py` over the reference tests and run `make defect-lab`. The first run is not green. Do not edit `variants.py`.

## Workshops 1 and 9

Workshop 1, the model bench, is the tool you measure the assistant with. It
lives in `workshops/model-bench/` and has its own `before/` and `after/`.

Workshop 9, the interview loop, has no tests. The artifact is a schedule, a
recorded mock, and a metrics sheet. It lives in `workshops/interview-loop/`.
