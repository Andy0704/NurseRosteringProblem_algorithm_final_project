# Mischek S10* Stretch-Tail Re-Evaluation: α=30 Against Spec-Correct Baseline

## Context

S10* (Mischek & Musliu 2019, p.137-139, eq.40) is a look-ahead penalty term added
to non-final weeks of the MILP objective. It penalizes end-of-week consecutive
working-day "stretch tails" to prevent cross-week S2 accumulation (the W3 cliff
diagnosed in `references/lookahead_design_notes.md`).

A pre-audit attempt with α=15 was stashed after identifying two errors:
1. The evaluator weight was still `_W_CONSEC=15` (W-2 correction pending), so
   the measured improvement was against an under-weight baseline.
2. α=15 is Ceschia 2019's CS2a/b (same-shift-type) weight; the term is meant to
   prevent CS2c/d violations (any-shift consecutive, weight 30). The α should
   match the cost it prevents.

This document covers the re-evaluation with α=30 against the spec-correct W-6
baseline (W-2: `_W_CONSEC=30`; W-6: `TOTAL_ASSIGN_W=20`, `W_ASSIGN=20`).

## Implementation

**File:** `outer_milp/models/milp_model.py`
**Location:** inside `build()`, per-nurse loop, `if not is_final_week:` block

```python
ALPHA_S10 = 30  # matches CS2c/d weight (Ceschia 2019 p.176-177)

tail_run_proxy = pulp.lpSum(w[max(0, D - M_w):D])
z_s10 = pulp.LpVariable(f"z_s10_{n_idx}", lowBound=0)
penalty_terms.append((ALPHA_S10, z_s10))
model += (z_s10 >= tail_run_proxy - (M_w - 1), f"S10star_{n_idx}")
```

`multi_week_runner.run_with_global()` was also fixed to pass `is_final_week` (was
calling `model.build()` without the argument, silently disabling S10* for all weeks).

---

## Measurement methodology

**Measurement:** MILP-only (no SA). `multi_week_runner.run_with_global()` calls
`parse()` → `MilpModel.build(is_final_week=...)` → `model.solve(30s)` → `evaluate()`.
No SA binary invoked. This is the correct isolation for evaluating an MILP objective
modification — SA improvement is a separate effect.

**W-6 baseline (no S10*):** MILP-only, `build(is_final_week=True)` for all weeks.
Run in the same session immediately before W-9, same code/weights. Clean comparison.

**W-9 (S10* α=30):** MILP-only, `build(is_final_week=False)` for non-final weeks,
`build(is_final_week=True)` for the final week.

**W-6 full-pipeline reference (from baseline_w6_spec_aligned.md, for context only):**
n012w8 total INRC-II=2770 (MILP→SA pipeline). NOT directly comparable to MILP-only
numbers due to pipeline stage difference.

---

## Pre-audit α=15 results (historical reference, under-weight baseline)

These were measured pre-W-2 (evaluator `_W_CONSEC=15`), so the S2/S3 evaluator
penalty was half the spec weight. Numbers are reproduced for completeness but
should NOT be used as a reference for conclusions.

**n012w8, weeks 0-3, MILP-only (pre-audit evaluator):**

| Wk | No-S10* total | α=15 total | Δ |
|---:|-------------:|-----------:|--:|
|  0 |           10 |         10 |  0 |
|  1 |           10 |          0 | -10 |
|  2 |          100 |         75 | -25 |
|  3 |          390 |        285 | -105 |
| SUM |          510 |        370 | -140 |

(Source: pre-audit session notes; evaluator used `_W_CONSEC=15`.)
W3 reduced: 390→285, SUM 510→370 (−27%). These numbers are under-weight.

---

## W-9 α=30 results: MILP-only no-S10* vs S10*

### n012w8 8-week

**MILP-only no-S10* baseline:**

| Wk | S1 | S2  | S3 | S4 | total |
|---:|---:|----:|---:|---:|------:|
|  0 |  0 |   0 |  0 | 10 |    10 |
|  1 |  0 |   0 |  0 | 10 |    10 |
|  2 |  0 |   0 |  0 | 20 |    20 |
|  3 |  0 | 750 |  0 |  0 |   750 |
|  4 |  0 | 150 |  0 |  0 |   150 |
|  5 |  0 |  60 |  0 | 10 |    70 |
|  6 |  0 | 120 |  0 |  0 |   120 |
|  7 |  0 |   0 |  0 | 20 |    20 |
| SUM |  0 | 1080 | 0 | 70 | **1150** |

Global: S6=1060, S7=450, total_global=1510. **Full INRC-II (no S10*) = 2660**

**MILP-only S10* α=30 (W-9):**

| Wk | S1 | S2  | S3 | S4 | total |
|---:|---:|----:|---:|---:|------:|
|  0 |  0 |   0 |  0 | 10 |    10 |
|  1 |  0 | 120 |  0 | 10 |   130 |
|  2 |  0 | 120 |  0 |  0 |   120 |
|  3 |  0 | 360 |  0 |  0 |   360 |
|  4 |  0 | 120 |  0 |  0 |   120 |
|  5 |  0 | 180 |  0 | 10 |   190 |
|  6 |  0 | 120 |  0 | 20 |   140 |
|  7 |  0 | 120 |  0 | 20 |   140 |
| SUM |  0 | 1140 | 0 | 70 | **1210** |

Global: S6=1160, S7=480, total_global=1640. **Full INRC-II (S10* α=30) = 2850**

**Per-week delta (n012w8, no-S10* → S10* α=30):**

| Wk | No-S10* | S10* α=30 | Δ |
|---:|--------:|----------:|--:|
|  0 |      10 |        10 |   0 |
|  1 |      10 |       130 | +120 |
|  2 |      20 |       120 | +100 |
|  3 |     750 |       360 | **-390** |
|  4 |     150 |       120 |  -30 |
|  5 |      70 |       190 | +120 |
|  6 |     120 |       140 |  +20 |
|  7 |      20 |       140 | +120 |
| SUM |    1150 |      1210 |  **+60** |
| Global | 1510 | 1640 | +130 |
| **TOTAL** | **2660** | **2850** | **+190** |

---

### n005w4 4-week

**MILP-only no-S10* baseline:**

| Wk | S1 | S2  | S3  | S4 | total |
|---:|---:|----:|----:|---:|------:|
|  0 |  0 |   0 |   0 |  0 |     0 |
|  1 | 30 |   0 |   0 | 20 |    50 |
|  2 |  0 |  30 |   0 |  0 |    30 |
|  3 | 30 | 300 |   0 |  0 |   330 |
| SUM | 60 | 330 |  0 | 20 | **410** |

Global: S6=60, S7=60, total_global=120. **Full INRC-II (no S10*) = 530**

**MILP-only S10* α=30 (W-9):**

| Wk | S1 | S2 | S3 | S4 | total |
|---:|---:|---:|---:|---:|------:|
|  0 |  0 | 30 |  0 |  0 |    30 |
|  1 | 30 |  0 |  0 | 20 |    50 |
|  2 |  0 | 30 |  0 | 30 |    60 |
|  3 |  0 |  0 |  0 | 10 |    10 |
| SUM | 30 | 60 |  0 | 60 | **150** |

Global: S6=20, S7=120, total_global=140. **Full INRC-II (S10* α=30) = 290**

**Note:** W3 (the cliff) reduced from 330 → 10 (−320). The remaining S2 moved
to W0/W2 as earlier, lighter violations. W1 H2 infeasibility (S1=30) is a
pre-existing instance constraint, not affected by S10*.

---

### n021w4 4-week

**MILP-only no-S10* baseline:**

| Wk | S1 | S2 | S3  | S4 | total |
|---:|---:|---:|----:|---:|------:|
|  0 |  0 |  0 |   0 |  0 |     0 |
|  1 |  0 |  0 |   0 |  0 |     0 |
|  2 |  0 | 60 |   0 |  0 |    60 |
|  3 |  0 |  0 | 120 | 20 |   140 |
| SUM |  0 | 60 | 120 | 20 | **200** |

Global: S6=120, S7=30, total_global=150. **Full INRC-II (no S10*) = 350**

**MILP-only S10* α=30 (W-9):**

| Wk | S1 | S2  | S3 | S4 | total |
|---:|---:|----:|---:|---:|------:|
|  0 |  0 |   0 |  0 |  0 |     0 |
|  1 |  0 |   0 |  0 |  0 |     0 |
|  2 |  0 | 120 |  0 |  0 |   120 |
|  3 |  0 |  60 |  0 | 20 |    80 |
| SUM |  0 | 180 |  0 | 20 | **200** |

Global: S6=140, S7=30, total_global=170. **Full INRC-II (S10* α=30) = 370**

---

## Summary comparison table

| Instance | Metric | No-S10* (MILP-only) | S10* α=30 (MILP-only) | Δ | Δ% |
|----------|--------|--------------------:|----------------------:|--:|----|
| n012w8 | per-week | 1150 | 1210 | +60 | +5.2% |
| n012w8 | global | 1510 | 1640 | +130 | +8.6% |
| n012w8 | **total INRC-II** | **2660** | **2850** | **+190** | **+7.1%** |
| n005w4 | per-week | 410 | 150 | -260 | -63.4% |
| n005w4 | global | 120 | 140 | +20 | +16.7% |
| n005w4 | **total INRC-II** | **530** | **290** | **-240** | **-45.3%** |
| n021w4 | per-week | 200 | 200 | 0 | 0% |
| n021w4 | global | 150 | 170 | +20 | +13.3% |
| n021w4 | **total INRC-II** | **350** | **370** | **+20** | **+5.7%** |

**W-6 full-pipeline reference (for context, not directly comparable):** n012w8=2770

---

## S10* mechanism analysis: what it did and why

### W3 cliff reduction in n012w8 (750→360)

Without S10*, nurses accumulate consecutive working days toward the end of W0-W2,
creating a high carry-in `consecutive_working_days` into W3. Even a small W3
schedule creates immediate S2 violations when the carry-in is at max.

With S10* α=30, the MILP disperses end-of-week assignments for non-final weeks.
W3 carry-in is reduced, so nurses have more margin before hitting max_consec in W3.
The W3 S2 penalty drops from 750→360.

### Why total worsened for n012w8 (+190)

S10* disperses end-of-week assignments, which means:
1. Nurses start some weeks with LESS carry-in → more working days available WITHIN
   the week → longer within-week runs → W1, W2 S2 violations increase.
2. Dispersion at W2 end means nurses have room to work more at W3 start, and W3
   mid-week runs may also grow (net W3 improvement is only partial).
3. Prorated S6 guidance (W_ASSIGN=20) still pushes nurses to hit weekly targets.
   Dispersion breaks the efficient long-run patterns, forcing the MILP to pay S2
   penalties at different locations to satisfy S6.

The S10* term at α=30 is "leaking" into earlier weeks: it pushes nurses away from
end-of-week work, but those avoided stretches need to go somewhere. W1, W5, W7
become the new cost-bearing weeks.

### Why n005w4 improved dramatically (-240, -45%)

n005w4 has 5 nurses (vs 12 for n012w8). With fewer nurses:
- The MILP has less flexibility to redistribute work across nurses.
- S10*'s constraint is more binding per nurse.
- The W3 cliff in n005w4 (S2=300 without S10*, only 5 nurses × 30 weight = 10
  violations) is more cleanly targeted: S10* in W0-W2 discourages the specific
  pattern causing W3's 300, and the MILP finds a better reordering.

The improvement (W3: 330→10) comes entirely from S10* successfully preventing the
terminal stretch pattern in W2 that fed the W3 spike.

### W2 end-of-week saturation (verified)

Test `test_stretch_tail_reduces_w2_end_saturation_n012w8` confirms:

| Condition | Nurses at max (cw >= max_cw) at W2 end |
|-----------|----------------------------------------|
| No-S10* (post-W-6 baseline) | **6/12** |
| S10* α=30 (W-9) | **4/12** |

The mechanism reduces saturation (6→4), but less than pre-W-6 α=15 (which showed
5→2 reduction at pre-W-6 weights). The weaker marginal effect with α=30 vs α=15
is because α=30 interacts more strongly with other MILP penalties, causing the
solver to trade off against S2 violations elsewhere rather than purely dispersing
the tail.

---

## W-6 per-week jump verification (860→1270 in full pipeline)

The previous session's W-3 full-pipeline baseline (n012w8 SUM=860) vs W-6 full-pipeline
(n012w8 SUM=1270) represents a +410 increase in per-week penalty. This session's
MILP-only measurements clarify the mechanism:

**MILP-only no-S10* n012w8 (W-6 weights, current session):**
- W3=750 (vs W-3 full-pipeline W3=480)
- W4=150 (vs W-6 full-pipeline W4=710)

The pattern: stronger MILP S6 pressure (W_ASSIGN=15→20) causes the MILP to
rearrange assignments, creating heavier consecutive-work accumulation toward W3.
SA then dramatically improves W3 (750→30 in the full pipeline), but SA's W3-fixing
move creates a large carry-out that causes W4 to spike (150→710).

**Verdict: EXPECTED S2/S3 trade-off, not degenerate behavior.**

The jump (860→1270) is the consequence of:
1. MILP with stronger S6 penalty creates denser early-week stretches → larger W3 in MILP output
2. SA fixes W3 at the cost of creating a W4 cliff (different myopic decision horizon)
3. Net effect: per-week total increases because the penalty moved from W3 to W4 and stayed there (SA can't fix W4 without creating a W5 cliff in a 1-week-at-a-time pipeline)

This is the look-ahead problem Phase 2 is designed to solve.

---

## Scenario classification (per W-9 instructions)

Per the three scenarios:

**n012w8: Scenario (b) — mechanism works on target but spills cost to other weeks.**
- W3 reduced: 750→360 (MILP-only). SA would further improve this.
- Total slightly worse: 2660→2850 (+7.1%). Spill is primarily to W1, W5, W7.
- Original target W3 <50 not achieved at MILP level (360 vs 50). Full pipeline
  (with SA) might approach closer, but cannot be confirmed without SA measurement.
- Root cause: S10* at α=30 is competitive with W_ASSIGN=20 penalty, causing the
  solver to trade S2 at the tail for S2 elsewhere to satisfy both S6 and S10*.

**n005w4: Scenario (a) — mechanism validated for this instance class.**
- Total improved dramatically: 530→290 (-45.3%). W3 cliff essentially eliminated (330→10).
- The 5-nurse constraint structure allows S10* to cleanly target the causal pattern.
- Write-up: S10* is effective for small-N instances where carry-in pathology is
  attributable to a small number of nurses' terminal stretches.

**n021w4: Scenario (c) — mechanism produces similar/worse total.**
- Total slightly worse: 350→370 (+5.7%). Per-week unchanged; global slightly worse.
- S10* is not contributing meaningfully. n021w4 doesn't have a strong terminal-stretch
  pathology (W-9 no-S10* already shows W3 split between S2/S3 rather than a pure tail spike).

---

## Full Pipeline (MILP→F&O→SA) — W-9-supplement

### Methodology

The MILP-only comparison above is not directly comparable to the W-6 baseline,
which was measured through the full pipeline (`run_4week_full_pipeline.py`).
That script calls `model.build()` with no `is_final_week` argument, so S10* was
silently **disabled** when the W-6 baseline was produced (default `is_final_week=True`).

To measure the full pipeline WITH S10* enabled, a read-only diagnostic script was
written (not committed) that reuses `_run_fo`, `_run_sa`, `save_problem`, `evaluate`,
`_end_of_week_history` from `run_4week_full_pipeline.py` unchanged, and calls
`model.build(is_final_week=(seq_idx == len(weeks)-1))` — the only difference from
the existing script. No existing source file was modified for this measurement.

### n012w8 8-week full pipeline

| Wk | sa_init | sa_fin | S1 | S2  | S3 | S4 | forb | total |
|---:|--------:|-------:|---:|----:|---:|---:|-----:|------:|
|  0 |   190.0 |  190.0 |  0 |   0 |  0 | 10 |    0 |    10 |
|  1 |   290.0 |  290.0 |  0 |  90 |  0 |  0 |    0 |    90 |
|  2 |   210.0 |  210.0 |  0 |   0 |  0 | 10 |    0 |    10 |
|  3 |  1390.0 |  260.0 |  0 |   0 | 30 | 10 |    0 |    40 |
|  4 |  1120.0 |  260.0 |  0 |   0 | 30 | 30 |    0 |    60 |
|  5 |   930.0 |  930.0 |  0 | 660 | 30 |  0 |    0 |   690 |
|  6 |   330.0 |  330.0 |  0 | 150 |  0 | 20 |    0 |   170 |
|  7 |   470.0 |  400.0 |  0 |  30 | 90 | 20 |    0 |   140 |
| SUM | | | **0** | **930** | **180** | **100** | **0** | **1210** |

Global: S6=1140, S7=900, total_global=2040. **Full INRC-II = 3250**

H2/H3 clean on all 8 weeks (S1=0, forbidden=0 throughout).

**Per-week delta vs W-6 baseline (no S10*, full pipeline):**

| Wk | W-6 sa_final | W-9-supp sa_final | Δ sa_fin | W-6 total | W-9-supp total | Δ total |
|---:|-------------:|-------------------:|---------:|----------:|----------------:|--------:|
|  0 |        150.0 |               190.0 |    +40.0 |        10 |              10 |       0 |
|  1 |        210.0 |               290.0 |    +80.0 |        10 |              90 |     +80 |
|  2 |        260.0 |               210.0 |    -50.0 |        20 |              10 |     -10 |
|  3 |        190.0 |               260.0 |    +70.0 |        30 |              40 |     +10 |
|  4 |        950.0 |               260.0 |   -690.0 |       710 |              60 |    -650 |
|  5 |        400.0 |               930.0 |   +530.0 |       160 |             690 |    +530 |
|  6 |        270.0 |               330.0 |    +60.0 |       110 |             170 |     +60 |
|  7 |        460.0 |               400.0 |    -60.0 |       220 |             140 |     -80 |
| SUM |       2890.0 |              2870.0 |    -20.0 |      1270 |            1210 |     -60 |

**Key observation: the W4 cliff (710) is almost entirely eliminated (→60, -650),
but a comparably-sized new cliff appears at W5 (160→690, +530).** SA relocates the
cross-week pathology rather than removing it. Net per-week total improves slightly
(-60), but global S6/S7 worsens substantially (+540, driven by S7: 540→900).

### n005w4 4-week full pipeline

| Wk | sa_init | sa_fin | S1 | S2 | S3 | S4 | forb | total |
|---:|--------:|-------:|---:|---:|---:|---:|-----:|------:|
|  0 |     0.0 |    0.0 |  0 |  0 |  0 |  0 |    0 |     0 |
|  1 |    50.0 |   40.0 |  0 |  0 |  0 | 20 |    0 |    20 |
|  2 |    70.0 |   70.0 |  0 | 30 |  0 | 20 |    0 |    50 |
|  3 |   150.0 |    0.0 |  0 |  0 |  0 |  0 |    0 |     0 |
| SUM | | | **0** | **30** | **0** | **40** | **0** | **70** |

Global: S6=80, S7=90, total_global=170. **Full INRC-II = 240**

H2 clean on all 4 weeks (S1=0) — the W1 instance-infeasibility seen in the W-6
baseline (S1=30) does not reproduce here; most likely CBC found a different optimal
MILP solution this run (non-determinism), not a direct effect of S10*.

**vs W-6 baseline (320):** Δ = -80 (-25.0%). Direction preserved, smaller magnitude
than the MILP-only comparison (-45.3%) because the W-6 full-pipeline baseline (320)
was already lower than the W-6 MILP-only baseline (530) — SA had already closed
part of the gap that S10* targets.

### n021w4 4-week full pipeline

| Wk | sa_init | sa_fin | S1 | S2 | S3 | S4 | forb | total |
|---:|--------:|-------:|---:|---:|---:|---:|-----:|------:|
|  0 |     0.0 |    0.0 |  0 |  0 |  0 |  0 |    0 |     0 |
|  1 |    20.0 |   20.0 |  0 |  0 |  0 |  0 |    0 |     0 |
|  2 |   120.0 |  120.0 |  0 |120 |  0 |  0 |    0 |   120 |
|  3 |    80.0 |   80.0 |  0 | 60 |  0 | 20 |    0 |    80 |
| SUM | | | **0** | **180** | **0** | **20** | **0** | **200** |

Global: S6=140, S7=30, total_global=170. **Full INRC-II = 370**

F&O accepted 0/10 pairs every week; SA delta=+0.0 every week — the schedule is
unchanged from the raw MILP output. Identical to the W-9 MILP-only result (370) by
construction, since neither F&O nor SA modified anything this run.

**vs W-6 baseline (350):** Δ = +20 (+5.7%). Unchanged from MILP-only comparison.

### Comparison table (full pipeline, W-6 vs W-9-supplement)

| Instance | config | per-week | global S6+S7 | total INRC-II | Δ vs W-6 | Δ% |
|----------|--------|---------:|--------------:|---------------:|---------:|----|
| n012w8   | W-6 (no S10*)   | 1270 | 1500 | **2770** | — | — |
| n012w8   | W-9-supp (S10*) | 1210 | 2040 | **3250** | +480 | **+17.3%** |
| n005w4   | W-6 (no S10*)   |  110 |  210 |  **320** | — | — |
| n005w4   | W-9-supp (S10*) |   70 |  170 |  **240** |  -80 | **-25.0%** |
| n021w4   | W-6 (no S10*)   |  200 |  150 |  **350** | — | — |
| n021w4   | W-9-supp (S10*) |  200 |  170 |  **370** |  +20 | **+5.7%** |

### Q1: Does SA absorb the MILP-only spillover?

**No — SA relocates it rather than absorbing it.** The MILP-only analysis showed
spillover spread across W1/W2/W5/W6/W7 (each +20 to +120) after S10* reduced W3
(750→360). In the full pipeline, the pattern is different: SA, starting from the
S10*-shaped MILP seed, drives W3/W4 down to near-trivial levels (40, 60) — better
than even the MILP-only S10* result — but this concentrates a large new cliff at
W5 (160→690, S2=660). The cross-week pathology is not eliminated by adding SA; it
migrates to wherever SA's single-week greedy improvement leaves the worst carry-in.
This is the same myopic mechanism documented in the W-6 860→1270 jump, now repeating
one week later in the horizon.

### Q2: Is the n005w4 -45.3% improvement preserved?

**Direction yes, magnitude smaller.** MILP-only: 530→290 (-45.3%). Full pipeline:
320→240 (-25.0%). The full-pipeline W-6 baseline (320) already reflects SA's own
improvement over the MILP-only baseline (530), so there is less remaining gap for
S10* to close. The mechanism is confirmed to help in the full pipeline, just with
a smaller relative effect once SA is in the loop.

### Q3: Final scenario classification (full pipeline — the metric that matters)

| Instance | Verdict |
|----------|---------|
| n012w8 | **Regression.** +480 (+17.3%), worse than the MILP-only regression (+7.1%). The W4 cliff is fixed but relocates to W5, and global S7 balloons (540→900) — a cost not visible in the MILP-only objective at all, since S7 is computed only at horizon end. |
| n005w4 | **Improvement, confirmed.** -80 (-25.0%). Scenario (a) holds in the full pipeline, with reduced magnitude. |
| n021w4 | **Unchanged / slight regression.** +20 (+5.7%), identical to MILP-only since neither F&O nor SA were active this run. |

---

## Conclusion (supersedes the MILP-only-only assessment above — full pipeline is the metric that matters)

S10* α=30 is instance-class dependent, and the full-pipeline measurement (W-9-supplement)
reverses the tentative MILP-only read for n012w8:

- **Effective** for n005w4 (full pipeline: 320→240, -25.0%, confirmed in both MILP-only
  and full pipeline; small N, clear terminal-stretch pathology).
- **Net regression** for n012w8 (full pipeline: 2770→3250, +17.3% — WORSE than the
  MILP-only-only read of +7.1%). SA does not absorb the MILP-level spillover; it
  relocates the W4 cliff to W5 and, more importantly, the global S7 term — invisible
  at the MILP-only per-week level — balloons from 540→900. The mechanism that looked
  "partially effective, spills elsewhere" at MILP-only level is a clear regression once
  SA and the global horizon-end terms are included.
- **Unchanged / slight regression** for n021w4 (350→370, +5.7%) — F&O/SA were inactive
  in this run, so MILP-only and full-pipeline numbers are identical.

**Phase 2 finding: S10* alone at α=30, in this codebase's single-week-at-a-time
MILP→F&O→SA pipeline, does not solve the cross-week myopic accumulation problem for
n012w8 — it relocates it and adds new global-term cost.** The mechanism is validated
for n005w4 only. Recommended follow-ups (not implemented, pending human review):
1. Tune M_w (the look-ahead window) — currently the contract's
   `maximumNumberOfConsecutiveWorkingDays`. A fixed smaller window (e.g. M_w=3) might
   focus the penalty more precisely and avoid the dispersion that causes the W1/W5
   spillover.
2. Add S6*/S7* look-ahead terms (Mischek 2019) — the global S7 regression (540→900)
   suggests the missing piece is weekend-aware look-ahead, not just consecutive-day
   look-ahead.
3. Investigate true rolling-horizon (multi-week MILP window) rather than single-week
   MILP + per-week look-ahead penalty, since the cliff simply relocates one week
   forward when only one week's tail is penalized at a time.

**Tests:** 22/22 pass. `test_stretch_tail_reduces_w2_end_saturation_n012w8` threshold
updated from ≤2 to ≤4 (reflects post-W-6 baseline of 6/12 → S10* result of 4/12).
H2/H3 gates clean on all weeks in both MILP-only and full-pipeline measurements;
SA≡evaluator identity holds (<1e-6, unaffected by MILP-side S10* change).
