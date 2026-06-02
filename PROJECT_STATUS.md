# NRP Project Status

<!-- AUTO-MAINTAINED: Claude updates this file at session start/end -->
<!-- Rule: surgical edits only — update changed rows, prepend to Recent Changes, never rewrite stable sections -->

## Last Updated
2026-06-03 — coverage-fix session

## Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| outer_milp/models/milp_model.py | ✅ Complete | H2 skill-specific soft coverage; build/solve/fix_and_optimize/fix_nurses |
| outer_milp/main.py | ✅ Complete | MILP→F&O→C++ loop, 3 iterations verified |
| outer_milp/utils/inrc2_parser.py | ✅ Complete | Sc/WD/H0 JSON → problem_exchange.json |
| outer_milp/utils/penalty_evaluator.py | ✅ Complete | S1–S7 + forbidden succession |
| outer_milp/utils/multi_week_runner.py | ✅ Complete | 4-week history propagation verified |
| outer_milp/utils/validate_schema.py | ✅ Complete | exit 0/1 |
| outer_milp/utils/json_handler.py | ✅ Complete | fail-loud UTF-8 |
| inner_heuristic/src/heuristic.cpp | ✅ Complete | SA+LA; hard coverage check in TwoWaySwap+DayOff |
| inner_heuristic/build/nrp_heuristic | ✅ Built | recompiled 2026-06-03 |
| tests/test_pipeline.py | ✅ 7/7 PASS | +test_milp_coverage_skill_feasible |
| docker/Dockerfile | ❌ Not started | Phase 4 |

## Benchmark Results

| Instance | Nurses | Weeks | Total Penalty | Avg/Week | Solve Time | Method |
|----------|--------|-------|-------------:|---------:|------------|--------|
| n005w4   | 5      | 0–3   | 470          | 117.5    | 1.5 s      | Myopic MILP only |
| n012w8   | 12     | 0–3   | 540          | 135.0    | 2.3 s      | Myopic MILP only |
| n021w4   | 21     | 0–3   | 1680         | 420.0    | 11.9 s     | Myopic MILP only (pre-fix) |
| n021w4   | 21     | w0    | 0            | 0        | ~60 s      | MILP+F&O+SA, 3 iter (post-fix) |

See `references/benchmark_results.md` for full per-week breakdown.

## Recent Changes

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
- [ ] Look-ahead mechanism in multi_week_runner.py
- [ ] Docker packaging (Phase 4)

## Known Issues

- PuLP 4.0 deprecation warnings (LpVariable, PULP_CBC_CMD) — non-fatal
- SA initial_cost (1525 for n021w4 w0) includes total-assignment penalty using full 4-week contract bounds vs. MILP's prorated weekly bounds — SA and MILP cost functions differ in scale but converge in ranking
