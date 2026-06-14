# NRP Project Status

<!-- AUTO-MAINTAINED: Claude updates this file at session start/end -->
<!-- Rule: surgical edits only — update changed rows, prepend to Recent Changes, never rewrite stable sections -->

## Last Updated
2026-06-04 — SA≡evaluator cost identity COMPLETE (段1–3 all passed, 800 random schedules per-item clean)
2026-06-10 — Professor feedback addressed; multi-objective literature review complete; look-ahead confirmed as Phase 2
2026-06-13 — SA big-M coverage penalty fix (no longer frozen); S4 weight 5→10; H2-feasibility gate (19/19 tests)

## Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| outer_milp/models/milp_model.py | ✅ Complete | H2 skill-specific soft coverage; build/solve/fix_and_optimize/fix_nurses |
| outer_milp/main.py | ⚠️ Runs | MILP→F&O→C++ loop runs without error; single-week n021w4 output verified (total=0); cross-week full-pipeline output NOT yet verified |
| outer_milp/utils/inrc2_parser.py | ✅ Complete | Sc/WD/H0 JSON → problem_exchange.json |
| outer_milp/utils/penalty_evaluator.py | ✅ Complete | S1–S7 + forbidden succession |
| outer_milp/utils/multi_week_runner.py | ✅ Complete | 4-week history propagation verified (MYOPIC MILP ONLY — does not invoke F&O or C++ heuristic) |
| outer_milp/utils/validate_schema.py | ✅ Complete | exit 0/1 |
| outer_milp/utils/json_handler.py | ✅ Complete | fail-loud UTF-8 |
| inner_heuristic/src/heuristic.cpp | ✅ SA homologous + big-M + 3 ops | SA+LA; consec cost identical to evaluator (SD-1/2/3); big-M H2 penalty (p0=0.05, M≈3·T0); S4=10; best_sched H2 gate; 3 operators (TwoWaySwap 70% / RandomDayOff 15% / ShiftTypeChange 15%, Knust 2019); M_COVER bookkeeping baseline correct for H2-infeasible seeds; 20/20 tests |
| inner_heuristic/build/nrp_heuristic | ✅ Built | recompiled 2026-06-14 |
| tests/ (all) | ✅ 20/20 PASS | test_pipeline (7) + test_sa_carryin (10) + test_sa_identity (3: 800 random + no-bigM-leak + H2 repair from infeasible seed) |
| docker/Dockerfile | ❌ Not started | Phase 4 |


## Benchmark Results

| Instance | Nurses | Weeks | Total Penalty | Avg/Week | Solve Time | Method |
|----------|--------|-------|-------------:|---------:|------------|--------|
| n005w4   | 5      | 0–3   | 470          | 117.5    | 1.5 s      | Myopic MILP only |
| n012w8   | 12     | 0–3   | 540          | 135.0    | 2.3 s      | Myopic MILP only |
| n021w4   | 21     | 0–3   | 1680         | 420.0    | 11.9 s     | Myopic MILP only (pre-fix) |
| n021w4   | 21     | w0 only | 0            | —        | ~60 s      | MILP+F&O+SA, 3 iter (post-fix, SINGLE WEEK) |

See `references/benchmark_results.md` for full per-week breakdown.

## Recent Changes

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
- [ ] Investigate why MILP/F&O occasionally produces H2-infeasible seeds (n005w4 W1/W3 surfaced during 段3 verification of ShiftTypeChange on 2026-06-14; fail-loud WARNING fires correctly, SA repairs it now, but root cause in MILP/F&O is unverified)
- [ ] Normalized weight as SA search surrogate (NOT scoring function)— implement after hard coverage fix so SA is actually searching
- [ ] **[Phase 2 — research contribution]** Look-ahead mechanism in multi_week_runner.py
      — Mischek & Musliu (2019) 14-day rolling horizon; this is the correct fix for cross-week constraint accumulation (n012w8 W3 penalty 60→300)
- [ ] Benchmark n021w4 + n012w8 full 4-week MILP+F&O+SA (cross-week not yet verified)
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

- **[Open — MILP/F&O produces H2-infeasible seed in some weeks]** Surfaced 2026-06-14 during 段3 ShiftTypeChange verification: n005w4 W1/W3 fed SA a schedule with totalH2Units==1; fail-loud WARNING fires correctly. SA now repairs it via ShiftTypeChange + M_COVER bookkeeping fix. Root cause in MILP/F&O is unverified; investigate as separate task.

## Design Decisions (永久性決策，非待辦事項)

| 決策 | 結論 | 依據 |
|---|---|---|
| Normalized weight | SA 搜索引導用（intentional surrogate），評分維持 INRC-II 官方權重 | 改動評分權重會破壞 benchmark 可比性；Rule 11 in CLAUDE.md |
| Multi-objective | 不在 INRC-II 框架下實作 Pareto | 文獻查證 0 篇在 INRC-II 上做 MO 對照；7 目標規模下 Pareto 收斂困難（Li et al. 2015）；主要衝突是跨週時間維度而非同週 MO 衝突 |
| 跨週衝突解法 | Look-ahead（Phase 2），不是 multi-objective | Mischek & Musliu 2019；myopic baseline 實測 n012w8 W3 懲罰 60→300 |
| INRC-II benchmark | 繼續使用，不更換 | 2025 年仍有新方法以其為對照；真實醫院資料因隱私無法公開 |
| weighted-sum 理論基礎 | Goal programming（Charnes & Cooper 1961）a priori aggregation，合法但數字本身是領域知識判斷 | 回應老師質疑的標準答法 |

老師反饋已於 2026-06-10 以信件回覆，策略說明同上表。