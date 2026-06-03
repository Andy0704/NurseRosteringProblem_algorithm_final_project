# NRP Myopic Benchmark Results

<!-- ============================================================ -->
<!-- UPDATE 2026-06-04 — SA≡evaluator cost identity complete -->
<!-- ============================================================ -->
## Post-Identity-Fix Status (2026-06-04)

The table below is the **myopic MILP baseline** (2026-06-02), kept as the pre-fix reference.
After the SA≡evaluator cost identity fix (SD-1/2/3 + carry-in + forbidden-as-hard):

- **n021w4 week 1 full pipeline**: `sa_initial` dropped from **755 (ratio ~9)** to **0**, fully aligned with `milp_obj=0`.
- **Identity verified**: 800 random schedules (n021w4 weeks 0–3, 200 each), per-item S2/S3/forbidden all diff <1e-6.
- **Bonus finding**: S1_coverage was already homologous (0/800 diff) — the earlier known-divergent mark was conservative.
- **Known residual**: SA still frozen (delta=0) due to hard coverage check (return 999999) — next-step issue, NOT a cost-function problem.
- The `ratio` metric used in the pre-fix baseline below is now considered a **pseudo-metric**; correct standard is per-solution per-item equality.

The myopic per-week penalty breakdown below remains valid as the MILP-only baseline for measuring future look-ahead improvements.

---

# Myopic MILP Baseline (pre-fix reference)

**Method**: Myopic multi-week MILP (`multi_week_runner.py`)  
**Solver**: PuLP / CBC  
**Per-week time limit**: 60 s  
**Weeks evaluated**: 0–3 (first 4 weeks)  
**Date**: 2026-06-02

## Summary Table

| Instance | Nurses | W0 | W1 | W2 | W3 | Total Penalty | Avg/Week | Solve Time |
|----------|--------|---:|---:|---:|---:|-------------:|---------:|------------|
| n005w4   | 5      | 60 | 115 | 150 | 145 | 470 | 117.5 | 1.5 s |
| n012w8   | 12     | 10 |  40 | 100 | 390 | 540 | 135.0 | 2.3 s |
| n021w4   | 21     | 345 | 480 | 435 | 420 | 1680 | 420.0 | 11.9 s |

## Per-Instance Breakdown

### n005w4 (5 nurses, weeks 0–3)

| Week | S1_coverage | S2_consec_work | S3_consec_off | S4_preferences | Forbidden | Total |
|------|------------:|---------------:|--------------:|---------------:|----------:|------:|
| 0    | 30          | 15             | 15            | 0              | 0         | 60    |
| 1    | 30          | 30             | 15            | 40             | 0         | 115   |
| 2    | 30          | 75             | 45            | 0              | 0         | 150   |
| 3    | 60          | 45             | 30            | 10             | 0         | 145   |
| **SUM** | **150** | **165**        | **105**       | **50**         | **0**     | **470** |

### n012w8 (12 nurses, weeks 0–3)

| Week | S1_coverage | S2_consec_work | S3_consec_off | S4_preferences | Forbidden | Total |
|------|------------:|---------------:|--------------:|---------------:|----------:|------:|
| 0    | 0           | 0              | 0             | 10             | 0         | 10    |
| 1    | 30          | 0              | 0             | 10             | 0         | 40    |
| 2    | 30          | 60             | 0             | 10             | 0         | 100   |
| 3    | 90          | 300            | 0             | 0              | 0         | 390   |
| **SUM** | **150** | **360**        | **0**         | **30**         | **0**     | **540** |

### n021w4 (21 nurses, weeks 0–3)

| Week | S1_coverage | S2_consec_work | S3_consec_off | S4_preferences | Forbidden | Total |
|------|------------:|---------------:|--------------:|---------------:|----------:|------:|
| 0    | 330         | 15             | 0             | 0              | 0         | 345   |
| 1    | 480         | 0              | 0             | 0              | 0         | 480   |
| 2    | 390         | 45             | 0             | 0              | 0         | 435   |
| 3    | 390         | 30             | 0             | 0              | 0         | 420   |
| **SUM** | **1590** | **90**         | **0**         | **0**          | **0**     | **1680** |

## Observations

- **n005w4**: Penalty dominated by S2 (consecutive work) and S3 (consecutive off); no forbidden succession violations.
- **n012w8**: Week 3 spike (390) driven by S2_consec_work (300) — history carry-forward causes constraint accumulation in later weeks.
- **n021w4**: High S1_coverage penalty dominates (1590/1680); indicates insufficient staffing coverage — likely a harder instance with tighter demand.
- All three instances solved in under 12 seconds total (well within 3-minute budget).

## Interpretation

n021w4 的 S1_coverage 懲罰佔比高達 95%（1590/1680），根本原因是 myopic MILP 每週獨立求解、不考慮跨週人力佈局：21 名護士在各週的合約限制（最大連續工作天、週末配額）下，能投入的班次組合空間狹窄，當 WD 需求略高時，單週 MILP 無法在固定排班史下同時滿足所有班次最低人力需求，只能以懲罰項放鬆，導致 S1 大量累積。n012w8 的 Week 3 S2_consec_work 驟升至 300，是「myopic 累積效應」的典型呈現：前三週的排班決策各自最優化，但會留下連續工作天數接近上限的歷史狀態，到第四週時 CBC 幾乎被迫讓部分護士違反最小/最大連續工作天約束，而無前瞻機制可在早期週次預先製造緩衝。這組 baseline 資料直接指出演算法的下一個改進目標：Fix-and-Optimize（F&O）應優先以 S1_coverage 違規最嚴重的班次-天組合為分解軸（而非純粹依護士索引滑窗），同時 multi_week_runner 需引入至少一層前瞻（look-ahead），在當週排班時預扣部分人力餘裕以防止後期週次的連續天數懲罰爆炸。

<!-- Updated: 2026-06-03 — 3-sentence structured analysis -->
**[S1] n021w4 coverage penalty (95% of total):**
21 名護士在各週合約限制（連續工作天上限、週末配額）下可用的排班組合空間已被壓縮，myopic MILP 每週獨立求解、不知道未來週次的需求分佈，一旦當週 WD 需求略高就只能用懲罰項放鬆最低覆蓋，導致 S1 累積達 1590。

**[S2] n012w8 Week 3 myopic accumulation pattern:**
前三週各自最優化的排班決策會留下「連續工作天接近上限」的歷史狀態，第四週 CBC 幾乎被迫讓部分護士違反連續天數約束，因為沒有前瞻機制在早期週次預先製造緩衝，S2 懲罰因此從 Week 2 的 60 驟升至 Week 3 的 300。

**[S3] Algorithm next improvement target:**
F&O 的分解軸應從純粹的護士索引滑窗改為「S1 違規最嚴重的班次–天組合優先」，同時 multi_week_runner 需加入一層前瞻，在當週排班時預扣人力餘裕，以阻斷跨週的連續天數懲罰爆炸。

