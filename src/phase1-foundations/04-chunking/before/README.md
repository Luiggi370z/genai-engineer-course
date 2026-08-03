# 1.4 Chunking

**Goal.** Build the two workhorse splitters — fixed-size word windows with overlap, and heading-aware sections — plus a worst-chunk inspector, so you see what each strategy does to a real document before Phase 2 retrieval depends on it.
**Prerequisite.** none — pure Python, no client or model involved.
**Effort.** ~20 min to green on the fast tests · no integration tier · ~35 min realistic first pass.

## Do this

```bash
make setup && make test     # 4 failing tests — read them, they are the spec
$EDITOR src/chunk.py        # fixed_size, heading_aware, worst_chunk
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_fixed_size_respects_window` fails because `fixed_size` isn't built. It feeds 2000 words and demands more than one chunk back, none longer than 512 words — a sliding word window whose step is `size - overlap`, so a sentence cut at one boundary survives whole in the next chunk.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] The last 20 words of chunk 0 reappear at the start of chunk 1 (`test_overlap_actually_overlaps`).
- [ ] `heading_aware` opens a new chunk at every markdown heading — both `# A` and `# B` start one (`test_heading_aware_starts_sections_on_headings`).

## Stuck?

1. Work in words, not characters: `text.split()`, slice windows out of the list, `" ".join` them back.
2. For `fixed_size`, advance the window start by `size - overlap` per step. For `heading_aware`, group lines into sections at each line starting with `#`, then re-apply the size cap inside any oversized section. `worst_chunk` is a `min` by word count over the non-empty chunks.

No integration lane: splitting text is pure Python, so the whole lesson runs offline with no model at all.
