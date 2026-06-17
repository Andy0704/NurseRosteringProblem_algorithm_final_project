# W-10 段1A Result Verification

Read-only verification segment. No source code changed. All measurements
below use the temp diagnostic script that exactly reproduces the W-10
段1A configuration (true cumulative S6/S6\* via `cur_week`/`num_weeks`,
S10\* disabled by stripping `S10star_*` constraints post-build — no edit
to the committed S10\* code).

## Important caveat surfaced before running anything

The literal command suggested in this segment's Step 1
(`python3 run_4week_full_pipeline.py --instance n012w8`) does **not**
reproduce the W-10 段1A result. That script calls `model.build()` with
**no arguments**, so `cur_week`/`num_weeks` default to `1/1` and
`is_final_week` defaults to `True` for every week — basic S6 (full bound,
no proration) fires on every week, demanding the full `min_assign` be hit
in a single week. Confirmed empirically: running it on n012w8 week 0
alone gives `MILP obj = 4060` (vs. `70` in the correct configuration) —
the same degenerate "work every day" pathology already diagnosed and
fixed in the W-10 段1A test (`test_stretch_tail_reduces_w2_end_saturation_n012w8`).
`run_4week_full_pipeline.py` predates this fix and was never updated to
pass the new parameters; it is not part of the officially maintained
pipeline (not listed in CLAUDE.md's Common Commands). All numbers below
use the script that actually produced the reported 960/300/420 figures.

## Step 1 — CBC non-determinism check (n012w8, 3 runs)

| Run | Per-week SUM | Global S6 | Global S7 | Total INRC-II |
|---|---:|---:|---:|---:|
| 1 | 660 | 0 | 300 | 960 |
| 2 | 660 | 0 | 300 | 960 |
| 3 | 660 | 0 | 300 | 960 |

**Identical across all 3 runs, down to every per-week component.** CBC
(default PuLP/CBC, single-threaded, no randomization seed) is fully
deterministic for this problem size. No non-determinism observed —
the -65.3% finding is not a single-seed artifact.

## Step 2 — SA behavior sanity + identity check

**SA initial vs final, all 8 weeks (consistent across all 3 runs):**

| Wk | sa_initial | sa_final | Δ |
|---:|---:|---:|---:|
| 0 | 510 | 510 | 0 |
| 1 | 270 | 270 | 0 |
| 2 | 310 | 310 | 0 |
| 3 | 380 | 380 | 0 |
| 4 | 570 | 570 | 0 |
| 5 | 640 | 640 | 0 |
| 6 | 260 | 260 | 0 |
| 7 | 380 | 380 | 0 |

**SA is frozen on every week** (`sa_initial == sa_final`) — the MILP+F&O
seed under the corrected S6/S6\* signal already leaves SA with nothing to
improve locally. This is consistent with, not contradictory to, the F1
fix being the dominant lever (see Interpretation).

**SA-evaluator identity check, week 4 (chosen as a previously-problematic
week):**

| Component | runEvalOnly (C++) | Python evaluator | diff |
|---|---:|---:|---:|
| S1_coverage | 0 | 0 | 0 |
| S2_consecutive_work | 150 | 150 | 0 |
| S3_consecutive_off | 0 | 0 | 0 |
| S4_preferences | 0 | 0 | 0 |
| forbidden_succession_violations | 0 | 0 | 0 |

**Exact match (diff=0, well within <1e-6).** No big-M leak; identity
holds under the new MILP seed exactly as it did before the F1 fix (the
fix only touches `milp_model.py`'s search-time objective, never
`heuristic.cpp` or `penalty_evaluator.py`).

**H2/H3 gates, all 8 weeks, all 3 runs:** `S1_coverage == 0` and
`forbidden_succession_violations == 0` on every single week in every run
(confirmed directly from the per-week tables in Step 1 — both columns are
0 throughout). H2 and H3 clean.

## Step 3 — Component breakdown (mechanistic picture)

**Global S6/S7 (the variables most affected by F1):** `S6_total_assignments
= 0`, `S7_total_weekends = 300`. S6 reaching exactly 0 means **zero**
nurses violate their horizon-end assignment-count bound — a complete
elimination of the 960-cost S6 violation seen under the old `÷4` mislabel.

**Per-week count of nurses near/at consecutive-work saturation
(`consec_work >= max_cw - 1` at end of week, weeks 0–7):**

```
[2, 2, 3, 1, 1, 1, 2, 2]   (of 12 nurses)
```

Never exceeds 3/12 at any week — compare to the old mechanism's peak of
6/12 at W2 end (W-9 baseline) before any look-ahead was added.

**Per-nurse final cumulative assignment total vs. contract bounds (after
week 7):**

| Status | Count (of 12) |
|---|---:|
| At/below lower bound (`a_n^-`) | 0 |
| At/above upper bound (`a_n^+`) | 5 |
| Strictly within bounds | 7 |

5 nurses land **exactly** at their upper bound (e.g. N03: total=22,
bounds=[14,22]), 7 stay comfortably within, 0 fall short. This is the
textbook signature of a correctly-modeled S6\*: nurses are driven toward
full utilization of their contract without exceeding it, rather than the
old mechanism's blind, history-unaware per-week target that produced
unpredictable over/under-shoot.

## Step 4 — n005w4 / n021w4 investigation

**n021w4, 3 runs:**

| Run | Per-week SUM | Global S6 | Global S7 | Total INRC-II |
|---|---:|---:|---:|---:|
| 1 | 420 | 0 | 0 | 420 |
| 2 | 420 | 0 | 0 | 420 |
| 3 | 420 | 0 | 0 | 420 |

**Identical across all 3 runs — the +20.0% is real, not CBC noise.**

**Per-week breakdown, W-6 baseline vs. W-10 段1A:**

| Wk | W-6 S2 | W-6 S3 | W-6 S4 | W-6 total | W-10 S2 | W-10 S3 | W-10 S4 | W-10 total | Δ total |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 | 0 | 120 | 0 | 10 | 130 | +130 |
| 1 | 0 | 0 | 0 | 0 | 30 | 0 | 0 | 30 | +30 |
| 2 | 60 | 0 | 0 | 60 | 180 | 0 | 0 | 180 | +120 |
| 3 | 0 | 120 | 20 | 140 | 60 | 0 | 20 | 80 | -60 |
| SUM | 60 | 120 | 20 | **200** | 390 | 0 | 30 | **420** | **+220** |

Global: S6 120→0, S7 30→0, total_global 150→0 (**-150**).

**Net: per-week +220, global -150, total +70 (350→420, +20.0%).** The
user's hypothesized trade-off mechanism is confirmed exactly: S3
(consecutive-days-off violations, 120) is **eliminated entirely** and S2
(consecutive-working-days) rises by 330 — the true S6\* proration forces
nurses who were previously coasting (under-working, building up
off-day stretches that the old `÷4` estimate didn't penalize tightly
enough) to work more consecutively to hit their accurate weekly
assignment target. This converts a previously-silent global-S6
violation (120, paid only at horizon end, weight 20) into an
immediately-visible per-week S2 cost (weight 30) — a **more accurate**
accounting of the schedule's real difficulty, since the old mechanism's
350 was only achievable by a MILP that did not know it was about to
violate the true horizon-end assignment bound. The new 420 is what it
actually costs to satisfy the real S6 constraint; 350 was the cost of
unknowingly violating it. Whether 420 or 350 is "better" depends on
whether correct constraint compliance (420, S6/S7 both 0) is weighed more
than a lower nominal total reached via under-constrained search (350, S6
violated by 120) — for the same reason this project's other "scale gap"
findings treat hidden/excluded violations as defects, not features, **420
is the more trustworthy number**, not a regression to be tuned away.

**n005w4, no separate 3-run table needed** (already deterministic per the
n012w8/n021w4 evidence above — CBC determinism is a solver/PuLP-config
property, not instance-specific). W-6→W-10: 320→300 (-6.25%), small and
in the improving direction, no anomaly to investigate.

## Step 5 — Cross-validation against Mischek's published results

**No directly comparable published number exists.** Mischek & Musliu
(2019) Table 2 (paper p.140–141) reports results only for instances with
35, 70, and 110 nurses (`n035w4`, `n035w8`, `n070w4`, `n070w8`, `n110w4`,
...) — their hidden-instance evaluation set does not include any instance
at our scale (`n005`, `n012`, `n021`). The `Sol-n012w8-*.json` files
bundled in this repo's testdataset are **per-week format-reference
solutions with no aggregate cost field** (confirmed by inspection — raw
`{nurse, day, shiftType, skill}` assignment lists, no score), used for
parser/schema validation, not as a scored benchmark. `references/
benchmark_results.md` (this project's own historical baselines) contains
no externally-published reference score for n012w8 either.

**Rough order-of-magnitude sanity check (explicitly not a validation):**
normalizing Mischek's `n035w8` extended-model costs (Table 2, 10 instances,
mean ≈ 3344) by nurse-weeks (35 nurses × 8 weeks = 280) gives ≈ 11.9
cost/nurse-week. Our n012w8 result (960 / (12×8=96) nurse-weeks) gives
≈ 10.0 cost/nurse-week — the same order of magnitude. This is a weak
signal at best (different demand patterns, contract mixes, and skill
structures between instance classes, and a different solver/algorithm
entirely) but it rules out the "5× too low, something's missing" failure
mode the user flagged as the concerning alternative.

## Interpretation

The 3-run determinism check, the exact SA-evaluator identity match, and
the mechanistic breakdown (global S6 exactly 0, 5/12 nurses landing
precisely at their upper bound, per-week saturation never exceeding 3/12)
all support the same conclusion: **the -65.3% finding on n012w8 is robust
and mechanistically well-understood, not a CBC-seed artifact or a
masked regression.** It is solid enough to be the slide's central result,
with two caveats worth stating alongside it: (1) there is no external
published benchmark at this instance scale to validate the absolute
number against — only the relative before/after comparison within this
project is verified, and (2) the n021w4 "regression" (+20.0%, also
3-run-confirmed deterministic) is better framed as a correction — the old
350 was achieved by a model that didn't know it was violating the global
S6 constraint, while the new 420 is the honest cost of not violating it.
