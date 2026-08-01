# 9.2 Funnel tracker

**Goal.** Instrument the job search as a four-stage funnel — applications →
screens → technicals → onsites → offers — then find the stage leaking furthest
below its healthy floor and prescribe exactly one fix. Debug the search like a
pipeline: one variable at a time, then re-measure.
**Prerequisite.** None — standalone tool; the mindset is Phase 3's eval loop
applied to your own pipeline.
**Effort.** ~20 min · gentle.

## Do this

```bash
make setup && make test     # 3 failing tests — read them, they are the spec
$EDITOR src/funnel.py       # TODOs 1-3: rates, leaking_stage, prescription
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_identifies_top_of_funnel_leak` fails because nothing is built: 100
applications collapsing to 3 screens must flag `applications->screens` and
prescribe the resume fix. `rates()` computes the conversion at each stage;
`leaking_stage()` compares each rate against its `HEALTHY` floor *proportionally*
(furthest below wins, not lowest raw rate) and ignores any stage whose input
volume is under 5 — two data points are noise, not a diagnosis.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] A healthy funnel returns `None` from `leaking_stage()` and a prescription
      containing "healthy".
- [ ] The onsite-leak case (10 onsites, 0 offers) flags `onsites->offers`, not an
      earlier stage.

## Stuck?

1. Each rate is downstream count over upstream count. The leak is the stage with
   the smallest `rate / floor` ratio below 1.0 — a 0.05 rate against a 0.10 floor
   is a worse leak than 0.25 against 0.30.
2. Apply the volume guard to the stage's *input* count (`applications` for the
   first rate, `screens` for the second, and so on); if every trusted stage meets
   its floor, return `None` and let `prescription()` say the funnel is healthy.

No integration lane: pure arithmetic over five integers — there is nothing to call.
The integration test is your next twenty applications.
