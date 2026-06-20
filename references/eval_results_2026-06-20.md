# INRC-II Public Testbed Evaluation Results

## Setup

- 14 production datasets (`n030`–`n120`, ×{4,8} weeks) + 3 testdatasets (`n005w4`, `n012w8`, `n021w4`).
- 1 finalist instance per production dataset (per `references/eval_design_notes.md` §2 recovery — the organiser's "Instance A" for each of the 28 late instances).
- 3 testdatasets: 4 instances each — the canonical instance (all 3 modes) plus 3 extras run in `full` mode only, as an SA-seed-stability proxy (the RNG seed is hardcoded, see Limitations).
- 3 ablation modes per canonical instance: `milp` (MILP only) / `fo` (MILP + Fix-and-Optimize) / `full` (MILP + F&O + C++ SA).
- 60 (instance, mode) jobs total, all completed — 0 failures, 0 truncated writes (all 60 JSON files parse cleanly).
- Wall-clock: 9h 27m for the full batch.
- MILP CBC time limit: a flat 310s/week across **all** 14 datasets (the value the Ceschia 2019 §4.2 formula gives for N=120) — not separately scaled per dataset. See Limitations.

## Plots

![P1](plots/p1_cost_by_dataset.png)

**P1.** Cost per dataset, grouped by mode (blue=milp, orange=fo, green=full), datasets ordered by N then W, log-scale Y. Most production datasets have only one run per mode, so these are single points, not real boxes — only the three testdatasets' `full` mode (4 instances) shows a real spread.

![P2](plots/p2_mean_cost_bar.png)

**P2.** Mean cost per (dataset, mode) as bars, with the organiser-validated best-known cost overlaid as a dashed horizontal marker per production dataset.

![P3](plots/p3_cost_vs_N.png)

**P3.** Cost vs. nurse count N, faceted by week count (W=4 left, W=8 right), one line per mode plus a best-known reference line/marker.

![P4](plots/p4_gap_to_best_known.png)

**P4.** `gap_pct = (our_cost − best_known) / best_known × 100`, grouped by mode. The three testdatasets have no public benchmark and are marked "no benchmark" instead of a fabricated bar.

![P5](plots/p5_wallclock_vs_N.png)

**P5.** Wall-clock per (instance, mode) vs. N, log-Y, marker shape = week count, overlaid with the Ceschia 2019 §4.2 budget formula `(10 + 3·(N−20))·W` (dashed = W4, dotted = W8). The formula is undefined below N=20, so no reference line is drawn for the three testdatasets.

## Summary table

| dataset | N | W | best-known | milp | fo | full | gap_full% |
|---|---:|---:|---:|---:|---:|---:|---:|
| n005w4 | 5 | 4 | no benchmark | 550 | 460 | 240 | — |
| n012w8 | 12 | 8 | no benchmark | 800 | 800 | 860 | — |
| n021w4 | 21 | 4 | no benchmark | 470 | 470 | 450 | — |
| n030w4 | 30 | 4 | 1755 | 620 | 620 | 2220 | +26.5% |
| n030w8 | 30 | 8 | 1900 | 1280 | 1280 | 3610 | +90.0% |
| n040w4 | 40 | 4 | 1730 | 1470 | 1470 | 1470 | -15.0% |
| n040w8 | 40 | 8 | 2700 | 3610 | 3610 | 3460 | +28.1% |
| n050w4 | 50 | 4 | 1480 | 810 | 810 | 1340 | -9.5% |
| n050w8 | 50 | 8 | 5410 | 2550 | 2550 | 5560 | +2.8% |
| n060w4 | 60 | 4 | 2815 | 2880 | 2880 | 2880 | +2.3% |
| n060w8 | 60 | 8 | 2765 | 3070 | 3070 | 4040 | +46.1% |
| n080w4 | 80 | 4 | 3535 | 4330 | 4330 | 4330 | +22.5% |
| n080w8 | 80 | 8 | 4995 | 10270 | 9120 | 9120 | +82.6% |
| n100w4 | 100 | 4 | 1445 | 3560 | 3560 | 7950 | +450.2% |
| n100w8 | 100 | 8 | 3055 | 7430 | 7430 | 7010 | +129.5% |
| n120w4 | 120 | 4 | 2435 | 4250 | 4240 | 4240 | +74.1% |
| n120w8 | 120 | 8 | 3510 | 6140 | 6160 | 6470 | +84.3% |

\* `fo` column data invalidated by a parameter-propagation bug (see Key findings #3). Provided for transparency only.

(`milp`/`fo`/`full` columns are the canonical finalist instance only — the same instance across all three modes — so `gap_full%` is a like-for-like comparison. Testdataset `full` means in P1–P3 additionally include the 3 SA-seed-stability extras and so don't always match the `full` column above exactly.)

## Key findings

- **Gap to best-known grows with N, and two negative gaps are an evaluator-coverage artifact, not real outperformance.** `n040w4` (-15.0%) and `n050w4` (-9.5%) read as *beating* the competition's organiser-validated minimum across 9 finalist teams — implausible on its face. The evaluator does not implement S2 CS2a/b or S5 (see Limitations), so `total_inrc2_cost` is missing penalty terms that the official scoring includes; these two negative numbers are undercounting, not genuine superiority. Gap should be read as a lower bound on the true gap, growing sharply for N≥80 (e.g. `n100w4` +450%, `n100w8` +130%).
- **The SA stage ("full" mode) is not a strict improvement over MILP+F&O — it's a coin flip with high variance.** Comparing `full` vs `milp` head-to-head across the 14 production datasets: 6 improve, 5 worsen, 3 unchanged. The worst regression is `n100w4` (3560 → 7950, +123% in absolute cost from a single week's SA run going from a per-week cost of 10 to 4740 while the other three weeks stayed flat or improved slightly), and `n030w8` (1280 → 3610). The best win is `n080w8` (10270 → 9120, driven by one week dropping from 1780 to 70). This is large enough, and on enough instances, to warrant treating "full" mode's local-search stage as a source of regression risk, not a guaranteed refinement — likely because the per-week SA optimizes local week cost via delta evaluation without any visibility into the global S6/S7 terms or the multi-week carry-forward effect of its own moves on neighboring weeks.
- **F&O ablation column invalidated by a parameter-propagation bug.** `fix_and_optimize()` in `milp_model.py:434-457` calls `self.build()` without forwarding `(is_final_week, cur_week, num_weeks)`, so F&O sub-problems are silently solved under the default `(True, 1, 1)` — a different objective function from the main per-week solve (which uses the real context, including the S6\*/S7\*/S10\* look-ahead terms when `is_final_week=False`). The accept/reject comparison `new_penalty < current_penalty` is then apples-to-oranges, and F&O sub-problems are rejected ~100% of the time on non-final weeks. The 11/14 datasets where `fo == milp` reflect this rejection. The 3/14 where `fo` differs from `milp` all land on or near the final week, where the buggy default coincidentally matches the actual context. Diagnosis from an `/tmp/diag_fo.py` probe (not committed). Fix is a one-line propagation: rebuilding within `fix_and_optimize` should pass through the original `(is_final_week, cur_week, num_weeks)` — deferred to post-presentation implementation work.
- **Wall-clock: only `n120w8` is genuinely budget-constrained; the rest were given more time than their own spec allows, by harness design.** The batch used a flat 310s/week CBC limit for all 14 datasets (the Ceschia value for N=120), not the size-scaled `10+3·(N−20)` formula. So `n120w8`'s milp-mode wall-clock (2481s ≈ 310s/week × 8) genuinely saturates its own spec budget (7 of 8 weeks hit the 310s cap exactly; only week 3 finished early at 58s) — but mid-size datasets like `n080w8` (2481–2541s total) appear to exceed their *own* 190s/week spec line in P5 only because they were deliberately run with the larger flat cap, not because CBC organically blew through a tighter budget. The slowest single run overall was `n080w8` full mode at 2541s.
- **H3 (forbidden succession, hard constraint) is clean on all 60 runs** — 0 violations everywhere, confirming the H3 gate holds at every scale tested. H2 (coverage, S1) is non-zero on 25 of 60 runs, which is expected since coverage shortfall is a soft-tracked cost here, not a hard ban.

## Honest limitations

- SA's RNG seed is hardcoded (`std::mt19937 rng(42)`, no CLI override — W-10 段1B note); the three testdataset "SA-seed-stability" extras are different problem instances used as an indirect proxy, not repeated trials of the same instance.
- 1 instance per dataset, vs. the INRC-II competition convention of multiple independent runs per instance for stochastic algorithms (commonly cited as up to 10) to average out SA variance — our single-run numbers, especially for `full` mode, carry whatever variance a single SA run has, which the "full" vs "milp" regression finding above suggests can be large.
- The penalty evaluator does not implement S2 CS2a/b or S5, so `total_inrc2_cost` is not the complete official INRC-II objective — direct comparison against `best_known` (which is the complete official score) understates the true gap, as seen in the two negative-gap datasets above.
- `n120w8` MILP hits the 310s/week time-limit ceiling on 7 of 8 weeks (confirmed: per-week `wall_clock_milp` = [309.9, 309.9, 310.0, 58.2, 310.0, 309.9, 309.9, 310.0]); its MILP solution at that dataset size should be read as time-limited, not necessarily CBC's best achievable bound.
- F&O sub-problem parameter-propagation bug (discovered 2026-06-21, evaluator results invalidated for the F&O column on 11/14 production datasets). MILP and Full mode results unaffected; only the F&O column ablation is invalidated. Bug logged in PROJECT_STATUS.md Known Issues; fix deferred.
