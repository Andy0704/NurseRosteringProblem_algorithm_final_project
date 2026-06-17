# Spec-aligned baseline (post-W-6)

## Commit reference

| Component | Commit | Change |
|-----------|--------|--------|
| `penalty_evaluator.py` | f5737bc (W-2) | `_W_CONSEC` 15→30 |
| `heuristic.cpp` | bee2dac (W-3) | `CONSEC_WEIGHT` 15→30 |
| `penalty_evaluator.py` | W-6 | `_W_ASSIGN=20`, `_W_WEEKEND=30`; `evaluate_global_s6_s7()` added |
| `milp_model.py` | W-6 | `W_ASSIGN` 15→20 |
| `heuristic.cpp` | W-6 | `TOTAL_ASSIGN_W` 10→20 |
| `multi_week_runner.py` | W-6 | `run_with_global()` added; CLI reports global S6/S7 |

All weights now match Ceschia 2019 §2.5.1–2.5.2 for implemented components.
21/21 pytest pass.

## Coverage scope

**Implemented and spec-aligned:**
- S1 — coverage (weight 30)
- S2 CS2c/d — any-shift consecutive working days (weight 30)
- S3 — consecutive days off (weight 30)
- S4 — shift-off preferences (weight 10)
- S6 — total assignments: per-week prorated in MILP/SA (weight 20, correct);
  global end-of-horizon via `evaluate_global_s6_s7()` (weight 20)
- S7 — total working weekends: per-week penalty in MILP (weight 30);
  global end-of-horizon via `evaluate_global_s6_s7()` (weight 30)
- H3 — forbidden successions (hard count)

**Missing / not yet implemented:**
- S2 CS2a/b — same-shift-type consecutive (spec weight 15) — W-4 scope
- S5 — complete weekends — W-5 scope

## Reproducible commands

```
# Per-week (MILP-only, from NRP_Claude_Agent/):
python3 outer_milp/utils/multi_week_runner.py \
    --instance data/raw_inrc2/testdatasets_json/n012w8 --weeks 0 1 2 3 4 5 6 7
python3 outer_milp/utils/multi_week_runner.py \
    --instance data/raw_inrc2/testdatasets_json/n005w4 --weeks 0 1 2 3
python3 outer_milp/utils/multi_week_runner.py \
    --instance data/raw_inrc2/testdatasets_json/n021w4 --weeks 0 1 2 3

# Full pipeline + global S6/S7:
# Use run_with_global() via multi_week_runner __main__ (prints global S6/S7)
```

Measurement scripts (not committed): used inline via `run_with_global()` CLI.

---

## n012w8 8-week per-week baseline

**Instance:** n012w8 (12 nurses, 8 planning weeks)
**Pipeline:** MILP (30s) → SA

| Wk | sa_init | sa_fin | S1 | S2  | S3 | S4 | forb | total | gap | H2 | H3 |
|---:|--------:|-------:|---:|----:|---:|---:|-----:|------:|----:|:--:|:--:|
|  0 |   150.0 |  150.0 |  0 |   0 |  0 | 10 |    0 |    10 | 140 | Y  | Y  |
|  1 |   210.0 |  210.0 |  0 |   0 |  0 | 10 |    0 |    10 | 200 | Y  | Y  |
|  2 |   260.0 |  260.0 |  0 |   0 |  0 | 20 |    0 |    20 | 240 | Y  | Y  |
|  3 |   990.0 |  190.0 |  0 |  30 |  0 |  0 |    0 |    30 | 160 | Y  | Y  |
|  4 |   950.0 |  950.0 |  0 | 690 |  0 | 20 |    0 |   710 | 240 | Y  | Y  |
|  5 |   400.0 |  400.0 |  0 | 150 |  0 | 10 |    0 |   160 | 240 | Y  | Y  |
|  6 |   270.0 |  270.0 |  0 |  90 |  0 | 20 |    0 |   110 | 160 | Y  | Y  |
|  7 |   460.0 |  460.0 |  0 | 210 |  0 | 10 |    0 |   220 | 240 | Y  | Y  |
|**SUM**| | | **0** | **1170** | **0** | **100** | **0** | **1270** | **1620** | Y | Y |

**Observations:**
- H2/H3 all-clean on all 8 weeks.
- W3 cliff (480 at W-3) is **resolved**: W3 now = 30. SA made a large improvement
  on W3 (sa_init=990 → sa_fin=190, Δ=−800), driven by doubled S6 prorated penalty.
- **New cliff at W4**: S2=690, total=710. The stronger W_ASSIGN=20 in MILP caused
  nurses to be assigned fewer days/week in early weeks, but accumulated history by
  W4 produces a large S2 burst (consecutive working days).
- Scale gap = sa_fin − eval_total = 1620 over 8 weeks. Attribution:
  gap/TOTAL_ASSIGN_W = 1620/20 = 81 S6 violation units (prorated weekly S6 in SA
  that per-week evaluator correctly excludes per Rule 12).

## n012w8 global end-of-horizon

| Constraint | Value | Interpretation |
|------------|------:|----------------|
| S6_total_assignments | 960 | 48 viol-units × weight 20 |
| S7_total_weekends | 540 | 18 viol-units × weight 30 |
| **total_global** | **1500** | |

**Full INRC-II cost (n012w8, 8-week):** per-week 1270 + global 1500 = **2770**

S7=540 reflects that 8 consecutive weekends cause nurses to exceed
`maximumNumberOfWorkingWeekends` contract limits; no weekend-management mechanism
(S5 complete-weekend, W-5 scope) is active yet.

---

## n005w4 4-week per-week baseline

**Instance:** n005w4 (5 nurses, 4 planning weeks)
**Pipeline:** MILP (30s) → SA

| Wk | sa_init | sa_fin | S1 | S2 | S3 | S4 | forb | total | gap | H2 | H3 |
|---:|--------:|-------:|---:|---:|---:|---:|-----:|------:|----:|:--:|:--:|
|  0 |     0.0 |    0.0 |  0 |  0 |  0 |  0 |    0 |     0 |   0 | Y  | Y  |
|  1 |    70.0 |   70.0 | 30 |  0 |  0 | 20 |    0 |    50 |  20 | **N** | Y  |
|  2 |    50.0 |   50.0 |  0 | 30 |  0 |  0 |    0 |    30 |  20 | Y  | Y  |
|  3 |   330.0 |   30.0 |  0 |  0 | 30 |  0 |    0 |    30 |   0 | Y  | Y  |
|**SUM**| | | **30** | **30** | **30** | **20** | **0** | **110** | **40** | **N** | Y |

W1 H2_clean=N (S1=30): persistent instance infeasibility in n005w4 week 1
(pre-existing, not introduced by W-6).

## n005w4 global end-of-horizon

| Constraint | Value |
|------------|------:|
| S6_total_assignments | 60 |
| S7_total_weekends | 150 |
| **total_global** | **210** |

**Full INRC-II cost (n005w4, 4-week):** per-week 110 + global 210 = **320**

---

## n021w4 4-week per-week baseline

**Instance:** n021w4 (21 nurses, 4 planning weeks)
**Pipeline:** MILP (30s) → SA

| Wk | sa_init | sa_fin | S1 | S2 | S3  | S4 | forb | total | gap | H2 | H3 |
|---:|--------:|-------:|---:|---:|----:|---:|-----:|------:|----:|:--:|:--:|
|  0 |     0.0 |    0.0 |  0 |  0 |   0 |  0 |    0 |     0 |   0 | Y  | Y  |
|  1 |     0.0 |    0.0 |  0 |  0 |   0 |  0 |    0 |     0 |   0 | Y  | Y  |
|  2 |    80.0 |   80.0 |  0 | 60 |   0 |  0 |    0 |    60 |  20 | Y  | Y  |
|  3 |   140.0 |  140.0 |  0 |  0 | 120 | 20 |    0 |   140 |   0 | Y  | Y  |
|**SUM**| | | **0** | **60** | **120** | **20** | **0** | **200** | **20** | Y | Y |

**Observations (vs W-3 baseline where n021w4 SUM=50):**
- SUM increased 50→200 (+150). Stronger MILP W_ASSIGN=20 pushes nurses toward
  fewer days/week, creating more on/off transitions → more S2/S3 violations.
- W2: S2=60 (was 0 at W-3). W3: S3=120 (was 30 at W-3).
- H2/H3 all-clean.

## n021w4 global end-of-horizon

| Constraint | Value |
|------------|------:|
| S6_total_assignments | 120 |
| S7_total_weekends | 30 |
| **total_global** | **150** |

**Full INRC-II cost (n021w4, 4-week):** per-week 200 + global 150 = **350**

---

## W-3 → W-6 comparison

### Per-week totals

| Instance | W-3 per-week SUM | W-6 per-week SUM | Δ |
|----------|-----------------:|-----------------:|--:|
| n012w8 (0-7) | 860 | **1270** | +410 |
| n005w4 (0-3) | 110 | **110** | 0 |
| n021w4 (0-3) | 50 | **200** | +150 |

n012w8 +410: cliff shifted W3→W4 (W3: 480→30; W4: new 710). Stronger S6 prorated
signal rearranges MILP's assignment distribution across weeks.

n021w4 +150: S6 prorated pressure compressed per-week workloads → more S2/S3 violations.

### Full INRC-II headline cost (per-week + global S6/S7)

| Instance | Per-week | Global S6+S7 | **Total** |
|----------|---------:|-------------:|----------:|
| n005w4   | 110      | 210          | **320**   |
| n012w8   | 1270     | 1500         | **2770**  |
| n021w4   | 200      | 150          | **350**   |

### Scale gap attribution

| Baseline | TOTAL_ASSIGN_W | n012w8 gap | gap/TOTAL_ASSIGN_W |
|----------|--------------:|-----------:|-------------------:|
| W-3 | 10 | 970 | 97 viol-units |
| W-6 | 20 | 1620 | 81 viol-units |

Gap grew ≈1.67× (not 2×) because MILP with W_ASSIGN=20 changed schedule patterns,
reducing some assignment violations while shifting accumulation to other weeks.

### Pre-audit MILP-only reference (weight-15 eval, for historical comparison)

Source: `references/benchmark_results.md`, "Myopic MILP Baseline" section.
These mix two factors (pipeline + weight) and are NOT isolated comparisons.

| Instance | MILP-only SUM (wt=15 eval) | Full-pipeline W-6 per-week |
|----------|--------------------------:|---------------------------:|
| n005w4   | 470 | 110 |
| n012w8   | 540 (wks 0-3) | 1270 (wks 0-7) |
| n021w4   | 1680 | 200 |
