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

## Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| outer_milp/models/milp_model.py | ✅ Complete | H2 skill-specific soft coverage; build/solve/fix_and_optimize/fix_nurses; W_ASSIGN=20 (S6, Ceschia 2019 §2.5.2, W-6) |
| outer_milp/main.py | ⚠️ Runs | MILP→F&O→C++ loop runs without error; single-week n021w4 output verified (total=0); cross-week full-pipeline output NOT yet verified |
| outer_milp/utils/inrc2_parser.py | ✅ Complete | Sc/WD/H0 JSON → problem_exchange.json |
| outer_milp/utils/penalty_evaluator.py | ✅ Complete | S1–S7 + forbidden succession; S2 CS2c/d & S3 weight 30 (W-2); S6 _W_ASSIGN=20, S7 _W_WEEKEND=30; evaluate_global_s6_s7() for end-of-horizon (W-6) |
| outer_milp/utils/multi_week_runner.py | ✅ Complete | 4-week history propagation; run_with_global() returns per-week + global S6/S7; CLI prints full INRC-II cost (W-6; MILP ONLY — does not invoke F&O or C++ heuristic) |
| outer_milp/utils/validate_schema.py | ✅ Complete | exit 0/1 |
| outer_milp/utils/json_handler.py | ✅ Complete | fail-loud UTF-8 |
| inner_heuristic/src/heuristic.cpp | ✅ SA homologous + big-M + 3 ops | SA+LA; consec cost identical to evaluator (SD-1/2/3); big-M H2 penalty (p0=0.05, M≈3·T0); S4=10; best_sched H2 gate; 3 operators (TwoWaySwap 70% / RandomDayOff 15% / ShiftTypeChange 15%, Knust 2019); M_COVER bookkeeping baseline correct for H2-infeasible seeds; CONSEC_WEIGHT 15→30 (W-3, bee2dac); TOTAL_ASSIGN_W 10→20 (W-6); 21/21 tests |
| inner_heuristic/build/nrp_heuristic | ✅ Built | recompiled 2026-06-17 (W-6) |
| tests/ (all) | ✅ 21/21 PASS | test_h3_gate (1) + test_pipeline (7) + test_sa_carryin (10) + test_sa_identity (3: 800 random + no-bigM-leak + H2 repair from infeasible seed) |
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
| n005w4   | 5      | 0–3   | 110 + 210 global = **320** | — | — | MILP-only, post-W-6; global S6=60, S7=150 |
| n012w8   | 12     | 0–7   | 1270 + 1500 global = **2770** | — | — | MILP-only, post-W-6; per-week SUM=1270 (S2=1170); W4 cliff=710; gap=1620 |
| n021w4   | 21     | 0–3   | 200 + 150 global = **350** | — | — | MILP-only, post-W-6; global S6=120, S7=30 |

See `references/benchmark_results.md` for MILP-only breakdown; `references/baseline_w6_spec_aligned.md` for post-W-6 full per-week + global breakdown with scale-gap attribution.

## Recent Changes

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
- [ ] **[Phase 2 — research contribution]** Look-ahead mechanism — follow-up from W-9:
      Measure S10* α=30 in FULL PIPELINE (MILP→SA) for n012w8 before final assessment.
      If per-week regression recovers under SA, mechanism is viable with caveats.
      If not, investigate: smaller M_w window or add S6*/S7* look-ahead terms (Mischek 2019).
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