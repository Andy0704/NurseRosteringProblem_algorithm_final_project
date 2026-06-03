# NRP Project Status

<!-- AUTO-MAINTAINED: Claude updates this file at session start/end -->
<!-- Rule: surgical edits only — update changed rows, prepend to Recent Changes, never rewrite stable sections -->

## Last Updated
2026-06-04 — SA≡evaluator cost identity COMPLETE (段1–3 all passed, 800 random schedules per-item clean)

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
| inner_heuristic/src/heuristic.cpp | ✅ Consec cost homologous | SA+LA; consec-work/off cost now identical to penalty_evaluator (SD-1/2/3 fixed, transition-based, carry-in aligned, forbidden moved to hard count). Verified by 800 random schedules + 10 carry-in cases. NOTE: hard coverage check (return 999999) still freezes SA — separate next-step issue |
| inner_heuristic/build/nrp_heuristic | ✅ Built | recompiled 2026-06-03 |
| tests/ (all) | ✅ 18/18 PASS | test_pipeline.py (7, incl. test_milp_coverage_skill_feasible) + test_sa_carryin.py (10, deterministic carry-in) + test_sa_identity.py (1, 800 random schedules per-item S2/S3/forbidden <1e-6) |
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
- [2026-06-04] feat: SA≡evaluator cost identity (SD-1/2/3 + carry-in + forbidden-as-hard); 800 random schedules per-item clean; n021w4 ratio 9→0

## Next Steps

- [x] Fix config.json key mismatch (instance_dir vs exchange_path)
- [x] Benchmark n021w4 w0 with full pipeline (S1=0, total=0)
- [x] Execute SA≡evaluator identity fix (段1 read-only + forbidden classify → 段2 changes + 10 carry-in cases → 段3 800 random + pipeline). DONE 2026-06-04, see SA_IDENTITY_DIAGNOSTIC.md
- [ ] **[NEXT]** Re-evaluate hard coverage check (SA frozen, delta=0 confirmed in 段3) — replace 999999 with large soft penalty so SA can explore
- [ ] S4 weight 5→10 (known one-constant fix, 段3 confirmed pure weight diff)
- [ ] Benchmark n021w4 full 4-week with MILP+F&O+SA pipeline (NOT yet done — single-week only so far)
- [ ] Benchmark n030w4 with full pipeline (NOT yet done)
- [ ] Look-ahead mechanism in multi_week_runner.py
- [ ] Docker packaging (Phase 4)

## Known Issues

- **[NEXT — top priority]** SA hard coverage check (return 999999) freezes the search: a metaheuristic relies on tolerating temporary worsening to escape local optima. 段3 pipeline smoke confirmed SA delta=0 (frozen) on n021w4 w1. Now that cost is homologous (no longer fluctuating), this can finally be judged accurately. Decide whether to replace 999999 with a large soft penalty so SA can explore.
- PuLP 4.0 deprecation warnings (LpVariable, PULP_CBC_CMD) — non-fatal
- **[S4 weight — known simple fix]** SA `SHIFT_OFF_REQ_W=5` vs evaluator `_W_PREF=10`. 段3 measured 727/800 schedules diverge by exactly violation_count × 5, confirming this is a pure weight difference (logic identical). Fix = change the one constant 5→10.
- **[RESOLVED 2026-06-04]** SA-evaluator cost drift (the n021w4 ratio 5–9 residual). Root cause was implementation drift (not design): SD-1 (open-run scoring), SD-2 (flat vs proportional min-violation), SD-3 (SA-only same-shift block), plus carry-in misalignment, plus forbidden wrongly in soft total. Fixed by rewriting SA consec cost to be identical to penalty_evaluator (single source of truth) and moving forbidden to a hard count (Change D). Verified: 800 random schedules per-item clean, n021w4 w1 ratio 9→0. The ratio metric itself was confirmed a pseudo-metric — correct standard is per-solution per-item equality <1e-6. See references/SA_IDENTITY_DIAGNOSTIC.md.
- **[evaluator-vs-official semantics gap — still open]** CW-1-WeekB boundary case: when a cross-week work run ends exactly at the Week A/B boundary (Week A all 7 days work → Week B d=0 is off), both SA and evaluator silently drop the run penalty (carry-in only fires when d=0 is work, so the deferred run from Week A is never scored if Week B starts with a day off). SA≡evaluator are consistent here, but whether this matches INRC-II official scoring semantics is unverified. Needs confirmation against official validator when running n030+ benchmark.