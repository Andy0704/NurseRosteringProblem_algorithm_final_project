# NRP Matheuristic — INRC-II Nurse Rostering Solver

A hybrid **matheuristic** for the INRC-II Nurse Rostering Problem: an exact **MILP** outer
layer (PuLP/CBC) feeds a fast **Simulated Annealing + Late Acceptance** inner layer (C++),
coordinated week-by-week through a shared `data/exchange/problem_exchange.json`.

- Design rationale: [`ARCHITECTURE.md`](ARCHITECTURE.md)
- Live state: [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
- Agent rules / skills: [`CLAUDE.md`](CLAUDE.md) · [`skills/SKILL.md`](skills/SKILL.md)

---

## Quick Start

```bash
# 1. Build the C++ heuristic
cd inner_heuristic && mkdir -p build && cd build \
  && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j4
cd ../..

# 2. Full pipeline benchmark on one instance (MILP -> F&O -> SA)
python3 run_4week_full_pipeline.py --instance n021w4

# 3. Test suite (expect 18/18)
python3 -m pytest tests/ -v
```

---

## How It Works (one paragraph)

The MILP layer produces a high-quality, provably-grounded schedule for one week.
Fix-and-Optimize then re-solves small sub-problems (a few nurses at a time) to refine it.
The SA/LA inner layer applies many fast local moves (shift swaps, day-offs), each scored by
**delta evaluation** (O(1) incremental cost). Every layer scores schedules with the *same*
INRC-II objective — this cost-function identity is the core invariant (ARCHITECTURE §5). Each
week's end state (consecutive work/off counts) carries into the next week's history.

---

## Repository Layout

```
outer_milp/
  main.py                      MILP -> F&O -> C++ SA loop entry
  models/milp_model.py         MILP build/solve, Fix-and-Optimize
  utils/inrc2_parser.py        INRC-II raw -> problem_exchange.json
  utils/penalty_evaluator.py   ground-truth S1-S7 scoring (single source of truth)
  utils/multi_week_runner.py   week 0..N driver, history propagation
  utils/json_handler.py        fail-loud UTF-8 exchange I/O
  utils/validate_schema.py     schema check (exit 0/1)

inner_heuristic/
  src/heuristic.cpp            SA + Late Acceptance, nurseCostFull, delta evaluators
  src/main.cpp                 entry; --eval-only flag for identity testing
  include/heuristic.h
  build/nrp_heuristic          compiled binary

tests/
  test_pipeline.py             parser / schema / penalty / multi-week / MILP coverage (7)
  test_sa_carryin.py           deterministic cross-week carry-in cases (10)
  test_sa_identity.py          SA==evaluator per-item identity, 800 random schedules (1)

references/
  SA_IDENTITY_DIAGNOSTIC.md    full SA-evaluator identity diagnostic chain
  sa_identity_fix_plan.md      3-stage execution plan (executed)
  benchmark_results.md         myopic baseline + post-fix results
  turhan2020_sa_params.md      SA params + shared-objective IP+SA basis
  knust2019_delta_eval.md      delta evaluation notes
  portella2021_late_acceptance.md   Late Acceptance criterion
  romer2019_dag_milp.md        DAG/MILP formulation notes

data/raw_inrc2/
  testdatasets_json/           n005w4, n012w8, n021w4 (+ official Sol- solutions)
  datasets_json/               larger instances n030-n120, w4/w8
data/exchange/                 problem_exchange.json (the layer-to-layer contract)

run_4week_full_pipeline.py     full MILP->F&O->SA benchmark (diagnostic)
compare_fo_n030w4.py           F&O comparison on n030w4 (exploratory)
session_snapshot.sh            collect core handoff set for project-files upload
ARCHITECTURE.md PROJECT_STATUS.md CLAUDE.md skills/SKILL.md config.json
```

---

## Testing & Verification Philosophy

Two ideas are load-bearing (codified in `CLAUDE.md` rules 8-12):

1. **Cost-function identity, not ratios.** Two implementations of the same objective must
   agree per-solution per-item to `< 1e-6`. A ratio that "looks close" proves nothing.
2. **Deterministic edge cases before random breadth.** Cross-week carry-in is exercised by
   hand-built cases (`test_sa_carryin.py`) first, then 800 random schedules
   (`test_sa_identity.py`) for breadth.

Current: **18/18 tests pass** (7 pipeline + 10 carry-in + 1 identity).

---

## Status

See [`PROJECT_STATUS.md`](PROJECT_STATUS.md). Headline: SA==evaluator cost identity complete;
next is replacing the SA hard coverage check (currently freezes the search) and the look-ahead
cross-week mechanism.

## Communication convention

Notes and discussion in Traditional Chinese; all code, identifiers, and comments in English.
