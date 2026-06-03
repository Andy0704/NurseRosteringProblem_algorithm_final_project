# NRP Project Status

<!-- AUTO-MAINTAINED: Claude updates this file at session start/end -->
<!-- Rule: surgical edits only — update changed rows, prepend to Recent Changes, never rewrite stable sections -->

## Last Updated
2026-06-03 — SA-evaluator identity diagnostic (planning complete, execution pending)

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
| inner_heuristic/src/heuristic.cpp | ⚠️ Untested change | SA+LA; hard coverage check (return 999999) in TwoWaySwap+DayOff — NO test covers this C++ change; cross-instance side-effects unverified | PENDING identity rewrite: consec blocks (SD-1/2/3) + nurseCostFull→struct
| inner_heuristic/build/nrp_heuristic | ✅ Built | recompiled 2026-06-03 |
| tests/test_pipeline.py | ✅ 7/7 PASS | +test_milp_coverage_skill_feasible (tests MILP solve() output only). NOTE: all 7 are Python-layer; the C++ SA hard coverage check has NO test coverage |
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

- [2026-06-03] fix: SA assignment bound prorated weekly (n012w8 ratio 12.9→2.1 ✓; n021w4 ratio 9.75→9.25 ✗ — window-sum vs exact-run gap remains, see Known Issues)
- [2026-06-03] fix: MILP H2 skill-specific soft coverage; SA hard coverage check (7/7 tests pass, n021w4 S1=0)
- [2026-06-02] feat: multi-week runner + myopic baseline test (6/6 tests pass)
- [2026-06-02] feat: F&O integrated into main loop
- [2026-06-02] checkpoint: before F&O
- [2026-06-02] chore: initial scaffold with heuristic stub

## Next Steps

- [x] Fix config.json key mismatch (instance_dir vs exchange_path)
- [x] Benchmark n021w4 w0 with full pipeline (S1=0, total=0)
- [ ] Benchmark n021w4 full 4-week with MILP+F&O+SA pipeline
- [ ] Benchmark n030w4 with full pipeline
- [ ] **[NEXT]** Execute SA≡evaluator identity fix (see SA_IDENTITY_DIAGNOSTIC.md) — Perform in three stages: Stage 1 read-only confirmation + forbidden classification → Stage 2 modification + 10 deterministic carry-in cases → Stage 3 800 random solutions + pipeline  
- [ ] Re-evaluate hard coverage check (SA-frozen?) — ONLY after identity fix (currently cost is still fluctuating, cannot judge accurately)
- [ ] Look-ahead mechanism in multi_week_runner.py
- [ ] Docker packaging (Phase 4)

## Known Issues

- PuLP 4.0 deprecation warnings (LpVariable, PULP_CBC_CMD) — non-fatal
- **[ROOT CAUSE IDENTIFIED, fix planned]** 
    The residual in n021w4 is not due to assignment scaling, but rather a drift in the implementation of the SA cost function and penalty_evaluator (which was not intended by design). Three structural drifts have been identified: SD-1/2/3 plus carry-in; see references/SA_IDENTITY_DIAGNOSTIC.md for details. Conclusion: The fix will revert to the original source (using the evaluator as the single source of truth), **not** fix the MILP formulation, **not** normalize weights, and **not** accept the gap—these three previous options have all been ruled out. The ratio is a pseudo-metric; the correct standard is precise equality per solution per item within <1e-6.
- **[UNRESOLVED, must define before fix]**
    The total attribution conflict of forbidden succession: the evaluator returns the raw count but does not add it to the total, while SA uses FORBIDDEN_WEIGHT=25 to include it in the total → the two layers of total cannot structurally be equal. Before proceeding, it must be determined whether forbidden is hard (SA does not include it in the total) or soft (the evaluator compensates by recalculating).
- SA hard coverage check (return 999999) may over-constrain the search: a metaheuristic relies on tolerating temporary worsening to escape local optima. Whether n021w4 w0's total=0 is SA-optimized or SA-frozen-on-MILP-solution cannot be distinguished from a single instance — needs multi-instance verification.
- **[evaluator-vs-official semantics gap]** CW-1-WeekB boundary case: when a cross-week work run ends exactly at the Week A/B boundary (Week A all 7 days work → Week B d=0 is off), both SA and evaluator silently drop the run penalty (carry-in only fires when d=0 is work, so the deferred run from Week A is never scored if Week B starts with a day off). SA≡evaluator are consistent here, but whether this matches INRC-II official scoring semantics is unverified. Needs confirmation against official validator when running n030+ benchmark.