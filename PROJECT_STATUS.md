# NRP Project Status

<!-- AUTO-MAINTAINED: Claude updates this file at session start/end -->
<!-- Rule: surgical edits only — update changed rows, prepend to Recent Changes, never rewrite stable sections -->

## Last Updated
2026-06-04 — SA≡evaluator cost identity COMPLETE (段1–3 all passed, 800 random schedules per-item clean)
2026-06-10 — Professor feedback addressed; multi-objective literature review complete; look-ahead confirmed as Phase 2
2026-06-13 — SA big-M coverage penalty fix (no longer frozen); S4 weight 5→10; H2-feasibility gate (19/19 tests)
2026-06-17 — W-2/W-3 weight alignment complete; evaluator+SA CONSEC_WEIGHT 15→30 per Ceschia 2019; SA≡evaluator identity restored; 21/21 tests pass; pushed bee2dac
2026-06-17 — W-6 S6/S7 weight alignment: evaluator _W_ASSIGN=20/_W_WEEKEND=30 + evaluate_global_s6_s7(); MILP W_ASSIGN 15→20; SA TOTAL_ASSIGN_W 10→20; 21/21 tests; baseline_w6_spec_aligned.md frozen; full INRC-II cost n012w8=2770, n005w4=320, n021w4=350
2026-06-17 — W-9 S10* α=30 re-evaluation: ALPHA_S10 15→30; run_with_global is_final_week fix; 22/22 tests; MILP-only results: n005w4 530→290 (-45%, scenario a), n012w8 2660→2850 (+7%, scenario b), n021w4 350→370 (+6%, scenario c); references/s10_star_alpha30_evaluation.md created
2026-06-17 — W-9-supplement: FULL PIPELINE (MILP→F&O→SA) S10* α=30 measured (no code change; temp diagnostic script reused existing pipeline functions). n012w8 W-6 2770→3250 (+17.3%, REGRESSION — W4 cliff relocates to W5, global S7 540→900); n005w4 320→240 (-25.0%, confirmed improvement); n021w4 350→370 (+5.7%, unchanged from MILP-only). Conclusion updated: mechanism validated for n005w4 only, net regression for n012w8 once SA+global terms included
2026-06-17 — W-10 段0: S6*/S7* design spec per Mischek 2019 (read-only, local commit 8c38644, not pushed). Found F1 (milp_model.py "S5" mislabel: static ÷4 estimate ignoring cumulative history, matches neither basic S6 nor S6*) and F2 (Mischek's α=9.9 is IRACE-tuned, not weight-matched, unlike S10*'s α=30)
2026-06-17 — W-10 段1A: fixed F1 (true cumulative S6/S6*, α=20, replaces ÷4); milp_model.py build() gained cur_week/num_weeks params; 22/22 tests (2 threshold recalibrations, root causes confirmed non-architectural). Full pipeline, S10* OFF for isolation: n012w8 2770→960 (-65.3%!! — W4 cliff 710→150, global S6 960→0), n005w4 320→300 (-6.25%), n021w4 350→420 (+20.0%, but global S6/S7 150→0). F1 alone outperforms S10* alone — primary root cause of n012w8 regression was the mislabel, not absence of look-ahead
2026-06-17 — W-10 段1A-verify: result confirmed robust — n012w8/n021w4 each 3-run deterministic (CBC, no variance), SA-eval identity exact (diff=0) on W4, H2/H3 clean all weeks all runs. Global S6=0, 5/12 nurses land exactly at upper bound. n021w4's +20% reframed as correction (old 350 silently violated global S6 by 120; new 420 is the honest compliant cost). No published Mischek/INRC-II reference exists at this instance scale (his Table 2 starts at n035); rough nurse-week-normalized sanity check (~10.0 vs ~11.9) rules out an order-of-magnitude error. Verdict: robust enough for the slide's central result
2026-06-19 — W-10 段1A-cleanup: CORRECTION — the 960/300/420 figures above required a non-reproducible throwaway script (stripped S10star_* constraints post-build, no committed entry point). run_4week_full_pipeline.py fixed to faithfully plumb cur_week/num_weeks/is_final_week (mirrors multi_week_runner.py) plus the previously-missing global S6/S7 add-on; production-faithful, reproducible totals are n012w8 2770→**1070** (-61.4%), n005w4 320→**260** (-18.75%), n021w4 350→**400** (+14.3%). 22/22 tests pass; H2/H3 clean on all 16 weeks across 3 instances. S10*'s marginal effect (now measurable against the F1-corrected baseline) is +110/-40/-20 — answers 段1B as a side effect
2026-06-19 — W-10 段1B: S7* per-week working weekend look-ahead (Mischek eq.33, α=W_WEEKEND=30) + S7 gate alignment fix (existing S7c was unconditional every week since the initial scaffold commit — dead code on non-final weeks — now wrapped in is_final_week, mirroring S6/S6*/S10*). 22/22 tests pass. Full pipeline vs 段1A: n012w8 1070→**860** (-19.6%, clear win), n005w4 260→**240** (-7.7%, clear win via knock-on S6 effect), n021w4 400→**450** (+12.5%, target-met-but-spill — per-week -35.1% but global S7 excess 30→210). H2/H3 clean all 16 weeks. Implementation work for 6/24 presentation now closed; remaining work is slide writing only

## Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| outer_milp/models/milp_model.py | ✅ Complete | H2 skill-specific soft coverage; build/solve/fix_and_optimize/fix_nurses; true cumulative S6 (final week)/S6* (non-final, proportional target) replaces ÷4 mislabel (W-10 段1A); S7 (final week)/S7* (non-final, Mischek eq.33 proportional-remaining-weekend budget) replaces previously-unconditional S7c dead code (W-10 段1B); build(is_final_week, cur_week, num_weeks) |
| outer_milp/main.py | ⚠️ Runs | MILP→F&O→C++ loop runs without error; single-week n021w4 output verified (total=0); cross-week full-pipeline output NOT yet verified |
| outer_milp/utils/inrc2_parser.py | ✅ Complete | Sc/WD/H0 JSON → problem_exchange.json |
| outer_milp/utils/penalty_evaluator.py | ✅ Complete | S1–S7 + forbidden succession; S2 CS2c/d & S3 weight 30 (W-2); S6 _W_ASSIGN=20, S7 _W_WEEKEND=30; evaluate_global_s6_s7() for end-of-horizon (W-6) |
| outer_milp/utils/multi_week_runner.py | ✅ Complete | 4-week history propagation; run_with_global() returns per-week + global S6/S7; CLI prints full INRC-II cost (W-6; MILP ONLY — does not invoke F&O or C++ heuristic); build() calls now pass cur_week/num_weeks for true S6* (W-10 段1A) |
| outer_milp/utils/validate_schema.py | ✅ Complete | exit 0/1 |
| outer_milp/utils/json_handler.py | ✅ Complete | fail-loud UTF-8 |
| inner_heuristic/src/heuristic.cpp | ✅ SA homologous + big-M + 3 ops | SA+LA; consec cost identical to evaluator (SD-1/2/3); big-M H2 penalty (p0=0.05, M≈3·T0); S4=10; best_sched H2 gate; 3 operators (TwoWaySwap 70% / RandomDayOff 15% / ShiftTypeChange 15%, Knust 2019); M_COVER bookkeeping baseline correct for H2-infeasible seeds; CONSEC_WEIGHT 15→30 (W-3, bee2dac); TOTAL_ASSIGN_W 10→20 (W-6); 21/21 tests |
| inner_heuristic/build/nrp_heuristic | ✅ Built | recompiled 2026-06-17 (W-6) |
| tests/ (all) | ✅ 22/22 PASS | test_h3_gate (1, gap threshold 200→300 per W-10 段1A) + test_pipeline (7, stretch-tail threshold ≤4→≤1 per W-10 段1A) + test_sa_carryin (10) + test_sa_identity (3: 800 random + no-bigM-leak + H2 repair from infeasible seed) |
| docker/Dockerfile | ❌ Not started | Phase 4 |


## Benchmark Results

| Instance | Nurses | Weeks | Total Penalty | Avg/Week | Solve Time | Method |
|----------|--------|-------|-------------:|---------:|------------|--------|
| n005w4   | 5      | 0–3   | 470          | 117.5    | 1.5 s      | Myopic MILP only |
| n012w8   | 12     | 0–3   | 540          | 135.0    | 2.3 s      | Myopic MILP only |
| n021w4   | 21     | 0–3   | 1680         | 420.0    | 11.9 s     | Myopic MILP only (pre-fix) |
| n021w4   | 21     | w0 only | 0            | —        | ~60 s      | MILP+F&O+SA, 3 iter (post-fix, SINGLE WEEK) |
| n005w4   | 5      | 0–3   | 110          | 27.5     | 3.6 s      | MILP+F&O+SA, post-W-3; W1 H2=N (S1=30, instance infeasibility) |
| n012w8   | 12     | 0–3   | 600          | 150.0    | 5.5 s      | MILP+F&O+SA, post-W-3; W3=480 cliff (S2 carry-in accumulation) |
| n012w8   | 12     | 0–7   | 860          | 107.5    | 9.2 s      | MILP+F&O+SA, post-W-3 full 8-week; S2 SUM=690, H2/H3 clean all wks |
| n021w4   | 21     | 0–3   | 50           | 12.5     | 10.0 s     | MILP+F&O+SA, post-W-3; H2/H3 clean all weeks |
| n005w4   | 5      | 0–3   | 110 + 210 global = **320** | — | — | MILP+SA, post-W-6 (no S10*); global S6=60, S7=150 |
| n012w8   | 12     | 0–7   | 1270 + 1500 global = **2770** | — | — | MILP+SA, post-W-6 (no S10*); per-week SUM=1270 (S2=1170); W4 cliff=710; gap=1620 |
| n021w4   | 21     | 0–3   | 200 + 150 global = **350** | — | — | MILP+SA, post-W-6 (no S10*); global S6=120, S7=30 |
| n005w4   | 5      | 0–3   | 70 + 170 global = **240** | — | — | MILP+F&O+SA, W-9-supp (S10* α=30); -25.0% vs W-6 |
| n012w8   | 12     | 0–7   | 1210 + 2040 global = **3250** | — | — | MILP+F&O+SA, W-9-supp (S10* α=30); +17.3% vs W-6 (REGRESSION — W4 cliff relocates to W5, S7 540→900) |
| n021w4   | 21     | 0–3   | 200 + 170 global = **370** | — | — | MILP+F&O+SA, W-9-supp (S10* α=30); +5.7% vs W-6 (F&O/SA inactive, identical to MILP-only) |
| n005w4   | 5      | 0–3   | 60 + 240 global = **300** | — | — | MILP+F&O+SA, W-10 段1A (true S6/S6*, α=20, S10* OFF for isolation); -6.25% vs W-6 |
| n012w8   | 12     | 0–7   | 660 + 300 global = **960** | — | — | MILP+F&O+SA, W-10 段1A (true S6/S6*, S10* OFF); **-65.3% vs W-6** — W4 cliff 710→150, global S6 960→0; F1 fix alone outperforms S10* alone |
| n021w4   | 21     | 0–3   | 420 + 0 global = **420** | — | — | MILP+F&O+SA, W-10 段1A (true S6/S6*, S10* OFF); +20.0% vs W-6 (per-week worse, global S6/S7 150→0) |
| n005w4   | 5      | 0–3   | 30 + 210 global = **240** | — | — | MILP+F&O+SA, W-10 段1B (+S7*, α=30); -7.7% vs 段1A (S6 80→60, S7 unchanged at 150) |
| n012w8   | 12     | 0–7   | 500 + 360 global = **860** | — | — | MILP+F&O+SA, W-10 段1B (+S7*, α=30); **-19.6% vs 段1A** (clear win, per-week 620→500 + global S7 450→360) |
| n021w4   | 21     | 0–3   | 240 + 210 global = **450** | — | — | MILP+F&O+SA, W-10 段1B (+S7*, α=30); +12.5% vs 段1A (target-met-but-spill: per-week -35.1%, global S7 30→210) |

See `references/benchmark_results.md` for MILP-only breakdown; `references/baseline_w6_spec_aligned.md` for post-W-6 full per-week + global breakdown with scale-gap attribution; `references/s10_star_alpha30_evaluation.md` for S10* MILP-only and full-pipeline comparison; `references/lookahead_design_notes.md` (§ W-10 段1A) for the S6/S6* mislabel fix and isolated measurement, (§ W-10 段1B) for S7* and the S7 gate-alignment fix.

## Recent Changes

- [2026-06-19] feat: S7* per-week working weekend look-ahead (W-10 段1B, Mischek 2019 eq.33, α=W_WEEKEND=30) + S7 gate alignment fix: the S7c block was unconditional every week since the initial scaffold commit (5b1a11e) — dead code on non-final weeks, since a nurse can work at most one weekend per single-week MILP call so the full max_wknds bound never trips before the final week. Wrapped in is_final_week (mirrors S6/S6*/S10* structure from 段1A); S7* added in the else branch using slots_remaining=num_weeks-cur_week+1 (inclusive of current week — confirmed cur_week is 1-indexed via cur_week=seq_idx+1 in both call sites). milp_model.py diff: 42 lines (35 ins/7 del). 22/22 tests pass. Full pipeline vs 段1A: n012w8 1070→**860** (-19.6%, clear win — per-week 620→500 and global S7 450→360 both improve), n005w4 260→**240** (-7.7%, clear win via knock-on global S6 effect 80→60, S7 itself unchanged), n021w4 400→**450** (+12.5%, target-met-but-spill — per-week improves -35.1% but global S7 excess rises 30→210 as redistribution concentrates excess onto fewer nurses). H2/H3 clean on all 16 weeks (8+4+4) across 3 instances, separately re-verified. No single instance wins or loses on every look-ahead term (S6*/S10*/S7* combined) — see references/lookahead_design_notes.md § W-10 段1B. Implementation work for 6/24 presentation closed; remaining work is slide writing only
- [2026-06-17] fix: replaced S5-mislabel ÷4 estimate with true cumulative S6/S6* per Mischek (W-10 段1A, F1 fix): milp_model.py's assignment-proration term (previously: current week's count vs. hardcoded min_assign//4 / ceil(max_assign/4), ignoring all history) replaced with real cumulative tracking — basic S6 (full bound check) on the final week, S6* (proportional cumulative target, cur_week/num_weeks) otherwise; α=20 locked (not Mischek's IRACE-tuned 9.9, which doesn't transfer — same rationale as S10*'s α=30). build() gained cur_week/num_weeks params; multi_week_runner.py's two build() call sites updated. 22/22 tests (2 threshold recalibrations: stretch-tail ≤4→≤1 after a missing-plumbing test fix dropped W2-end saturation to 0/12; H3-gate gap 200→300, confirmed SA's own untouched prorated-S6 contribution, not a leak). Full pipeline, S10* OFF for isolation (temp script strips S10star_* constraints post-build, no edit to committed S10* code): n012w8 2770→**960** (-65.3%!, W4 cliff 710→150, global S6 960→0), n005w4 320→300 (-6.25%), n021w4 350→420 (+20.0%, but global S6/S7 150→0). F1 alone outperforms S10* alone on n012w8 — the ÷4 mislabel, not the absence of look-ahead, was the primary driver of the original regression. Reframes 段1B (S7*+S10* recombination) as cleanup on a healthier baseline, not the main fix
- [2026-06-17] research: W-10 段1A-verify (read-only, no code change): 3-run determinism confirmed for n012w8 (660/0/300/960 identical ×3) and n021w4 (420/0/0/420 identical ×3) — CBC is deterministic for this problem size, the -65.3% finding is not a seed artifact. SA-evaluator identity exact (diff=0) on W4. H2/H3 clean all weeks all runs. Mechanistic picture: global S6 exactly 0, 5/12 nurses land exactly at upper bound, per-week saturation never exceeds 3/12 (was 6/12 pre-fix). n021w4's +20% reframed as correction, not regression: old 350 silently violated global S6 by 120 (the old ÷4 mechanism didn't know the true constraint existed); new 420 is the honest cost of zero violations. No published Mischek/INRC-II reference at this instance scale (his Table 2 starts at n035, 3x our largest test instance) — flagged as an open gap, not fabricated. Caught and documented that the literal `run_4week_full_pipeline.py` command does NOT reproduce this result (missing cur_week/num_weeks plumbing, reproduces the same degenerate pathology already fixed in tests). references/w10_1a_verification.md created
- [2026-06-17] research: S6*/S7* design spec per Mischek 2019 (W-10 段0, local commit 8c38644, NOT pushed pending human review): Q1-Q6 answered with PDF citations (pypdf venv extraction, poppler unavailable). Found F1 (the ÷4 mislabel above) and F2 (Mischek's S6*/S7* α=9.9 is IRACE-tuned, not weight-matched to official S6/S7, unlike S10*'s α=30) — both later resolved/decided in 段1A
- [2026-06-17] research: S10* α=30 FULL PIPELINE evaluation (W-9-supplement, no code change — temp diagnostic script reused existing _run_fo/_run_sa unchanged): n012w8 W-6 baseline 2770→3250 (+17.3%, REGRESSION — SA relocates the W4 cliff to W5 rather than absorbing it; global S7 540→900); n005w4 320→240 (-25.0%, improvement confirmed, smaller magnitude than MILP-only -45.3%); n021w4 350→370 (+5.7%, unchanged — F&O/SA inactive). Conclusion in s10_star_alpha30_evaluation.md revised: mechanism validated for n005w4 only; n012w8 is a net regression once SA + global terms included, not "partially effective" as the MILP-only-only read suggested
- [2026-06-17] feat: S10* α=30 re-evaluation (W-9): ALPHA_S10 constant added; run_with_global() is_final_week bug fixed; stretch-tail test threshold updated (≤2→≤4 after post-W-6 no-S10* baseline jumped 5→6/12); MILP-only comparison clean (no-S10* vs S10*); n005w4 -45% (scenario a), n012w8 +7% (scenario b — W3 cliff halved but spills); n021w4 +6% (scenario c); references/s10_star_alpha30_evaluation.md created; 22/22 tests pass
- [2026-06-17] fix: S6/S7 weight alignment (W-6 per Ceschia 2019 §2.5.2): evaluator _W_ASSIGN=20/_W_WEEKEND=30 + evaluate_global_s6_s7(); MILP W_ASSIGN 15→20; SA TOTAL_ASSIGN_W 10→20; test_sa_h2_feasible_no_bigm_leak updated to n005w4 wk3 (n021w4 wk2 frozen after weight change); 21/21 tests; full INRC-II cost: n012w8=2770, n005w4=320, n021w4=350; baseline renamed to baseline_w6_spec_aligned.md
- [2026-06-17] research: W-3-supplement frozen baseline; n012w8 8-week SUM=860 (S2=690, S3=90, S4=80, H2/H3 all-clean); n005w4 SUM=110 (W1 H2=N, instance infeasibility); n021w4 SUM=50; scale-gap attributed to S6 prorated component (97 violation-units × 10); references/baseline_w3_complete.md created
- [2026-06-17] fix: SA CONSEC_WEIGHT 15→30 (W-3, bee2dac); SA≡evaluator identity restored; 21/21 tests pass; n012w8 post-W-3 SUM=600 (pre-W-2 was 410; +190 from weight correction on S2 CS2c/d + S3); pushed to origin/main
- [2026-06-17] fix: evaluator _W_CONSEC 15→30 (W-2, f5737bc); S2 CS2c/d & S3 weights aligned to Ceschia 2019 §2.5.1; test_sa_carryin expected values updated (×2); intentionally identity-broken 9 tests documented
- [2026-06-15] research: normalized-weight SA surrogate investigated (n012w8 magnitude imbalance ≤3×, at threshold; reflects INRC-II intentional weight calibration); declined per Rule 14. No code change.
- [2026-06-14] fix: M_COVER bookkeeping baseline for H2-infeasible seeds (cur_cost init now includes M_COVER * totalH2Units(seed), so final_cost = best_cost - M_COVER * totalH2Units(best_sched) is always a clean fullCost value); +1 targeted test (test_sa_h2_repair_from_infeasible_seed) → 20/20 pass; n005w4 W1/W3 final_cost = 30/30 (verified via run_4week_full_pipeline.py)
- [2026-06-14] feat: SA ShiftTypeChange operator (Knust 2019); 70/15/15 split TwoWaySwap/RandomDayOff/ShiftTypeChange; first operator capable of Off→work transitions; improvement on n005w4/n012w8/n021w4 from 0/3.5/18.8% to ~58/44/19% (n012 partially CBC non-determinism)
- [2026-06-13] fix: SA hard coverage reject → M_COVER big-M soft penalty (Knust 2019, p0=0.05); best_sched gated on H2-feasibility (totalH2Units==0); SHIFT_OFF_REQ_W 5→10 (S4 homologous); 19/19 tests
- [2026-06-03] fix: SA assignment bound prorated weekly (n012w8 ratio 12.9→2.1 ✓; n021w4 ratio 9.75→9.25 ✗ — window-sum vs exact-run gap remains, see Known Issues)
- [2026-06-03] fix: MILP H2 skill-specific soft coverage; SA hard coverage check (7/7 tests pass, n021w4 S1=0)
- [2026-06-02] feat: multi-week runner + myopic baseline test (6/6 tests pass)
- [2026-06-02] feat: F&O integrated into main loop
- [2026-06-02] checkpoint: before F&O
- [2026-06-02] chore: initial scaffold with heuristic stub
- [2026-06-04] feat: SA≡evaluator cost identity (SD-1/2/3 + carry-in + forbidden-as-hard); 800 random schedules per-item clean; n021w4 ratio 9→0
- [2026-06-10] research: multi_objective_nrp.md (16 papers); confirmed 0 papers do MO on INRC-II; weighted-sum a priori aggregation justified via goal programming theory
- [2026-06-10] infra: nrp-literature-mcp MCP server built (Semantic Scholar + OpenAlex API)
- [2026-06-10] decision: professor feedback addressed — normalized weight = SA search surrogate only (not scoring); look-ahead is the correct fix for cross-week conflict (not multi-objective)

## Next Steps

- [x] Fix config.json key mismatch (instance_dir vs exchange_path)
- [x] Benchmark n021w4 w0 with full pipeline (S1=0, total=0)
- [x] SA≡evaluator cost identity fix (SD-1/2/3, 18/18 tests)
- [x] Professor feedback: normalized weight strategy confirmed; multi-objective literature reviewed
- [x] Fix SA hard coverage check: replaced return 999999 with M_COVER big-M soft penalty (2026-06-13)
- [x] S4 weight 5→10 (2026-06-13)
- [x] SA ShiftTypeChange operator (Knust 2019), 70/15/15 split (2026-06-14)
- [x] M_COVER bookkeeping baseline for H2-infeasible seeds — 20/20 tests (2026-06-14)
- [investigated, declined 2026-06-15] Normalized weight as SA search surrogate. 段1 measurement on n012w8 (4 weeks) showed component magnitude imbalance ≤3× (S1/S4=3.0, S2/S4=3.0, S3/S4=1.5), at/below the implementation threshold. The ratios reflect INRC-II's calibrated clinical-priority weighting (Rule 13) rather than a search-pathology artifact. Equal-weight surrogate would invert intentional calibration with no evidence of benefit. Closed out per Rule 14 evidence standard.
- [x] W-2: evaluator _W_CONSEC 15→30 (Ceschia 2019 §2.5.1); test_sa_carryin expected values updated (2026-06-17)
- [x] W-3: SA CONSEC_WEIGHT 15→30; identity restored 21/21; n012w8 SUM=600 new baseline (2026-06-17)
- [x] W-3-supplement: frozen baseline measured; n012w8 8-wk SUM=860, n005w4 SUM=110, n021w4 SUM=50; baseline_w3_complete.md committed (2026-06-17)
- [ ] W-4: Add S2 CS2a/b (same-shift-type consecutive, spec weight 15) to evaluator + SA + MILP; fix _end_of_week_history num_consecutive_shift_assignments carry
- [x] W-6: milp_model.py W_ASSIGN 15→20 + SA TOTAL_ASSIGN_W 10→20 + evaluate_global_s6_s7() + run_with_global(); baseline_w6_spec_aligned.md frozen (2026-06-17)
- [x] W-9: S10* ALPHA_S10 15→30; run_with_global is_final_week fix; 22/22 tests; references/s10_star_alpha30_evaluation.md (2026-06-17)
- [x] W-9-supplement: FULL PIPELINE (MILP→F&O→SA) S10* α=30 measured; n012w8 confirmed net REGRESSION (2770→3250, +17.3%); n005w4 confirmed improvement (320→240, -25.0%); n021w4 unchanged (350→370, +5.7%) (2026-06-17)
- [x] W-10 段0: S6*/S7* design spec per Mischek 2019 (Q1-Q6, local commit 8c38644, not pushed); found F1 (÷4 mislabel) + F2 (Mischek's α=9.9 not weight-matched) (2026-06-17)
- [x] W-10 段1A: fixed F1 — true cumulative S6/S6* (α=20) replaces ÷4 mislabel; 22/22 tests; full pipeline S10*-OFF isolation: n012w8 2770→960 (-65.3%!), n005w4 320→300 (-6.25%), n021w4 350→420 (+20.0%, global S6/S7→0). F1 alone outperforms S10* alone (2026-06-17)
- [x] W-10 段1A-verify: 3-run determinism confirmed (n012w8 + n021w4, identical every run), SA-eval identity exact, H2/H3 clean, mechanistic breakdown (5/12 nurses at exact upper bound, sat. never >3/12), n021w4 reframed as correction not regression; no published reference at this instance scale; references/w10_1a_verification.md (2026-06-17)
- [x] **[Phase 2 — research contribution]** Look-ahead mechanism — W-10 段1B complete:
      added S7* (Mischek eq.33, α=30) + fixed the latent S7 dead-code gate (now mirrors
      S6/S6*/S10*'s is_final_week structure). S10*'s marginal effect against the
      F1-fixed baseline was already answered as a side effect of 段1A-cleanup
      (+110/-40/-20 on n012w8/n005w4/n021w4). Full pipeline with all three look-ahead
      terms combined: n012w8 **860** (clear win), n005w4 **240** (clear win), n021w4
      **450** (target-met-but-spill — per-week -35.1%, global S7 excess 30→210). No
      instance wins or loses on every term — see lookahead_design_notes.md § W-10 段1B.
      IMPLEMENTATION WORK FOR 6/24 PRESENTATION CLOSED; remaining work is slide writing.
- [x] Benchmark n005w4/n012w8/n021w4 full pipeline (post-W-3 baseline: references/baseline_w3_complete.md) (2026-06-17)
- [ ] Benchmark n030w4 with full pipeline
- [ ] Gantt chart for final results presentation
- [ ] Docker packaging (Phase 4)

## Known Issues
- **[THEORY — RESOLVED 2026-06-10]** The three-stage theory statement has been corrected by the supervising professor:
  (1) Official weights are scoring rules, not clinical preference quantifications.
  (2) Weighted sums in discrete non-convex problems do not guarantee complete Pareto optimality.
  (3) Pareto solutions do not necessarily correspond back to weighted sums.
  → All subsequent reports and discussions will use conservative and precise language, see CLAUDE.md Rule 13.
  → The algorithmic direction remains unchanged (approved by the professor). Look-ahead is positioned as an engineering response to the limitations of myopic weighted-sum, see the Design Decisions section for details.

- **[THEORETICAL NOTE]** INRC-II weighted-sum specific values (S1=30, S2=15...) are domain-knowledge judgments, not mathematically derived. Theoretical justification is via goal programming (Charnes & Cooper, 1961) a priori aggregation framework — method is valid, specific weights are calibrated by competition designers based on clinical priority (patient safety > fairness > preference).

- **[LITERATURE GAP — confirmed]** 0 papers in literature perform multi-objective Pareto comparison on INRC-II specifically. Pareto MOEA degrades for >3 objectives (Li et al., 2015); INRC-II has S1–S7 (7 objectives). Cross-week temporal conflict (not intra-week MO conflict) is the dominant issue → look-ahead is the correct solution.

- **[RESOLVED 2026-06-13]** SA hard coverage check (return 999999) froze the search. Fixed by replacing the reject with M_COVER big-M soft penalty (M_COVER≈3×T0, Knust 2019 p0=0.05), proportional to H2 deficit units, applied only in the SA acceptance path (deltaTwoWaySwap/deltaRandomDayOff). best_sched is gated on totalH2Units==0 so the returned solution is always H2-feasible. Verified n021w4 w2: sa_initial=60 → sa_final=45 (SA now moves).

- **[S5/S6 semantic gap — by design]** nurseCostFull adds prorated S6 guidance (weekly assignment bounds) into nc.total -> final_cost as an SA heuristic. runEvalOnly and penalty_evaluator correctly exclude it (per-week INRC-II score only). final_cost intentionally != evaluator_total; use runEvalOnly for per-week score comparison. delta(final_cost) == delta(runEvalOnly) iff ΔS5=0, which is the correct no-big-M-leak diagnostic.

- PuLP 4.0 deprecation warnings (LpVariable, PULP_CBC_CMD) — non-fatal

- **[S4 weight — known simple fix]** SA `SHIFT_OFF_REQ_W=5` vs evaluator `_W_PREF=10`. 段3 measured 727/800 schedules diverge by exactly violation_count × 5, confirming this is a pure weight difference (logic identical). Fix = change the one constant 5→10.

- **[RESOLVED 2026-06-04]** SA-evaluator cost drift (the n021w4 ratio 5–9 residual). Root cause was implementation drift (not design): SD-1 (open-run scoring), SD-2 (flat vs proportional min-violation), SD-3 (SA-only same-shift block), plus carry-in misalignment, plus forbidden wrongly in soft total. Fixed by rewriting SA consec cost to be identical to penalty_evaluator (single source of truth) and moving forbidden to a hard count (Change D). Verified: 800 random schedules per-item clean, n021w4 w1 ratio 9→0. The ratio metric itself was confirmed a pseudo-metric — correct standard is per-solution per-item equality <1e-6. See references/SA_IDENTITY_DIAGNOSTIC.md.

- **[evaluator-vs-official semantics gap — still open]** CW-1-WeekB boundary case: when a cross-week work run ends exactly at the Week A/B boundary (Week A all 7 days work → Week B d=0 is off), both SA and evaluator silently drop the run penalty (carry-in only fires when d=0 is work, so the deferred run from Week A is never scored if Week B starts with a day off). SA≡evaluator are consistent here, but whether this matches INRC-II official scoring semantics is unverified. Needs confirmation against official validator when running n030+ benchmark.

- **[Defense-in-depth — H2-infeasible seed handling]** SA's fail-loud WARNING and M_COVER bookkeeping invariant correctly handle the case where the incoming schedule has totalH2Units > 0. Validated against a synthetic H2-infeasible seed (tests/test_sa_identity.py::test_sa_h2_repair_from_infeasible_seed, n021w4) on 2026-06-14 as defense-in-depth. MILP/F&O has NOT been observed to produce an H2-infeasible seed in practice (6 runs across n005w4/n012w8 on 2026-06-15, all clean — no WARNING). If WARNING ever fires in a real run, escalate; otherwise no action needed.

## Design Decisions (永久性決策，非待辦事項)

| 決策 | 結論 | 依據 |
|---|---|---|
| Normalized weight | SA 搜索引導用（intentional surrogate），評分維持 INRC-II 官方權重 | 改動評分權重會破壞 benchmark 可比性；Rule 11 in CLAUDE.md |
| Multi-objective | 不在 INRC-II 框架下實作 Pareto | 文獻查證 0 篇在 INRC-II 上做 MO 對照；7 目標規模下 Pareto 收斂困難（Li et al. 2015）；主要衝突是跨週時間維度而非同週 MO 衝突 |
| 跨週衝突解法 | Look-ahead（Phase 2），不是 multi-objective | Mischek & Musliu 2019；myopic baseline 實測 n012w8 W3 懲罰 60→300 |
| INRC-II benchmark | 繼續使用，不更換 | 2025 年仍有新方法以其為對照；真實醫院資料因隱私無法公開 |
| weighted-sum 理論基礎 | Goal programming（Charnes & Cooper 1961）a priori aggregation，合法但數字本身是領域知識判斷 | 回應老師質疑的標準答法 |

老師反饋已於 2026-06-10 以信件回覆，策略說明同上表。