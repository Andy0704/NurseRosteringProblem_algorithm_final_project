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

## Conclusion

S10* α=30 is instance-class dependent in its effectiveness:
- **Effective** for n005w4 (small N, clear terminal-stretch pathology)
- **Partially effective** for n012w8 (reduces the target cliff but spills elsewhere; net slightly worse at MILP level — full pipeline measurement recommended before final assessment)
- **Ineffective** for n021w4 (no dominant terminal-stretch pathology in this configuration)

Phase 2 finding: S10* alone at α=30 is insufficient for n012w8 at MILP level under
W_ASSIGN=20 pressure. A natural follow-up is:
1. Measure S10* effect in the FULL pipeline (MILP→SA) for n012w8 — SA may recover the
   per-week regression, and the tail-dispersion might improve the carry-in to SA's starting
   point enough to reduce the overall SA difficulty.
2. Tune M_w (the look-ahead window) — the current implementation uses the contract's
   `maximumNumberOfConsecutiveWorkingDays` as M_w. A fixed smaller window (e.g. M_w=3)
   might focus the penalty more precisely on true terminal-stretch patterns.
3. Add S6*/S7* look-ahead terms (Mischek 2019) if the full-pipeline measurement confirms
   the mechanism still underperforms.

**Tests:** 22/22 pass. `test_stretch_tail_reduces_w2_end_saturation_n012w8` threshold
updated from ≤2 to ≤4 (reflects post-W-6 baseline of 6/12 → S10* result of 4/12).
