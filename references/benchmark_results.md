# NRP Myopic Benchmark Results

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
