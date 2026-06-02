# NRP Project Status

<!-- AUTO-MAINTAINED: Claude updates this file at session start/end -->
<!-- Rule: surgical edits only — update changed rows, prepend to Recent Changes, never rewrite stable sections -->

## Last Updated
2026-06-02 — milp session

## Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| outer_milp/models/milp_model.py | ✅ Complete | build/solve/fix_and_optimize/fix_nurses |
| outer_milp/main.py | ✅ Complete | MILP→F&O→C++ loop, 3 iterations verified |
| outer_milp/utils/inrc2_parser.py | ✅ Complete | Sc/WD/H0 JSON → problem_exchange.json |
| outer_milp/utils/penalty_evaluator.py | ✅ Complete | S1–S7 + forbidden succession |
| outer_milp/utils/multi_week_runner.py | ✅ Complete | 4-week history propagation verified |
| outer_milp/utils/validate_schema.py | ✅ Complete | exit 0/1 |
| outer_milp/utils/json_handler.py | ✅ Complete | fail-loud UTF-8 |
| inner_heuristic/src/heuristic.cpp | ✅ Complete | SA+LA (T0=20×max_cost, β=0.9, γ=150) |
| inner_heuristic/build/nrp_heuristic | ✅ Built | 254,968 bytes |
| tests/test_pipeline.py | ✅ 6/6 PASS | incl. myopic baseline |
| docker/Dockerfile | ❌ Not started | Phase 4 |

## Benchmark Results

| Instance | Nurses | Weeks | Total Penalty | Avg/Week | Solve Time | Method |
|----------|--------|-------|-------------:|---------:|------------|--------|
| n005w4   | 5      | 0–3   | 470          | 117.5    | 1.5 s      | Myopic MILP only |
| n012w8   | 12     | 0–3   | 540          | 135.0    | 2.3 s      | Myopic MILP only |
| n021w4   | 21     | 0–3   | 1680         | 420.0    | 11.9 s     | Myopic MILP only |

See `references/benchmark_results.md` for full per-week breakdown.

## Recent Changes

- [2026-06-02] feat: multi-week runner + myopic baseline test (6/6 tests pass)
- [2026-06-02] feat: F&O integrated into main loop
- [2026-06-02] checkpoint: before F&O
- [2026-06-02] chore: initial scaffold with heuristic stub

## Next Steps

- [ ] Fix config.json key mismatch (instance_dir vs exchange_path)
- [ ] Look-ahead mechanism in multi_week_runner.py
- [ ] Benchmark n021w4 / n030w4 with full pipeline
- [ ] Docker packaging (Phase 4)

## Known Issues

- config.json keys differ from main.py keys (uses .get() fallback, no crash)
- PuLP 4.0 deprecation warnings (LpVariable, PULP_CBC_CMD) — non-fatal
