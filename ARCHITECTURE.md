# NRP Matheuristic — Architecture

> INRC-II Nurse Rostering Problem solver.
> A **matheuristic**: exact MILP (outer) + metaheuristic SA/LA (inner), coordinated week-by-week.

---

## 1. The Problem (INRC-II)

Assign nurses to shifts over multiple weeks so that total penalty is minimized.

**Hard constraints (never violated — H1/H2/H3):**
- H1: at most one shift per nurse per day
- H2: required staffing per (day, shift, skill) must be met
- H3: forbidden shift successions (e.g. Night → Early)

**Soft constraints (may be violated, each costs a weighted penalty — S1–S7):**
- S1 coverage/understaffing · S2 consecutive working days · S3 consecutive days off
- S4 shift-off/preference requests · S5–S7 weekend / complete-weekend / total-assignment balance

Objective is a single scalar: `total = Σ (violation_amount × weight)` over soft constraints.
**This same objective must be computed identically by every layer** (see §5).

---

## 2. Two-Layer Design — Why

| Layer | Tool | Strength | Weakness |
|-------|------|----------|----------|
| Outer | MILP (PuLP / CBC) | Provably optimal / bounded gap | Does not scale to large instances |
| Inner | SA + Late Acceptance (C++) | Fast, scales | No optimality guarantee |

A matheuristic combines them: MILP gives a high-quality start, SA refines fast where exact
solving is too slow. Follows mainstream IP+SA literature (Turhan & Bilgen 2020, see
`references/turhan2020_sa_params.md`) where both layers **share one objective function**.

---

## 3. The Pipeline (per week)

```
  INRC-II raw JSON (Sc / WD / H0)
       │  outer_milp/utils/inrc2_parser.py
       ▼
  data/exchange/problem_exchange.json ◄────────────┐
       │                                           │ (read / write same file)
       ▼                                           │
  ┌──────────────────────────────────────────┐    │
  │ OUTER MILP   outer_milp/models/milp_model │    │
  │   build() → solve()  → initial schedule   │    │
  └────────────────────┬─────────────────────┘    │
                       ▼                           │
  ┌──────────────────────────────────────────┐    │
  │ F&O (Fix-and-Optimize)                    │    │
  │   milp_model.fix_and_optimize / fix_nurses│    │
  │   fix most nurses, free a few, re-solve   │    │
  └────────────────────┬─────────────────────┘    │
                       ▼                           │
  ┌──────────────────────────────────────────┐    │
  │ INNER SA/LA   inner_heuristic/src/         │   │
  │   heuristic.cpp  (swap / dayoff moves,     │───┘
  │   delta-evaluated nurseCostFull)           │
  └────────────────────┬─────────────────────┘
                       ▼
  outer_milp/utils/penalty_evaluator.py   (ground-truth S1–S7 scoring)
                       ▼
  end-of-week history → carried into next week (multi_week_runner)
```

**Cross-week coupling:** each week's end state (consecutive work/off counts) becomes the next
week's history. A locally-optimal week can tighten the next week's feasible region — the
motivation for the planned look-ahead mechanism.

---

## 4. Component Map (actual paths)

### Outer (Python — MILP layer)
| Path | Role |
|------|------|
| `outer_milp/main.py` | MILP → F&O → C++ SA loop entry |
| `outer_milp/models/milp_model.py` | MILP build/solve; `fix_and_optimize`, `fix_nurses` (F&O) |
| `outer_milp/utils/inrc2_parser.py` | INRC-II raw (Sc/WD/H0) → `problem_exchange.json` |
| `outer_milp/utils/penalty_evaluator.py` | **Ground-truth S1–S7 + forbidden scoring (single source of truth)** |
| `outer_milp/utils/multi_week_runner.py` | Weeks 0..N driver + history propagation (myopic MILP path) |
| `outer_milp/utils/json_handler.py` | fail-loud UTF-8 exchange I/O |
| `outer_milp/utils/validate_schema.py` | exchange schema check (exit 0/1) |

### Inner (C++ — SA/LA layer)
| Path | Role |
|------|------|
| `inner_heuristic/src/heuristic.cpp` | SA + Late Acceptance; `nurseCostFull`, `coverageCostDay`, delta evaluators |
| `inner_heuristic/src/main.cpp` | SA entry; `--eval-only` flag for identity testing |
| `inner_heuristic/include/heuristic.h` | shared declarations |
| `inner_heuristic/build/nrp_heuristic` | compiled binary |

### Tests
| Path | Role |
|------|------|
| `tests/test_pipeline.py` | parser / schema / penalty / multi-week / MILP coverage (7) |
| `tests/test_sa_carryin.py` | deterministic cross-week carry-in cases (10) |
| `tests/test_sa_identity.py` | SA≡evaluator per-item identity, 800 random schedules (1) |

### Benchmarks / diagnostics
| Path | Role |
|------|------|
| `run_4week_full_pipeline.py` | full MILP→F&O→SA benchmark (ratio diagnostics SUPERSEDED, see header) |
| `compare_fo_n030w4.py` | F&O comparison on n030w4 (exploratory; full-pipeline status unverified) |

### References (literature notes + diagnostic chain)
| Path | Role |
|------|------|
| `references/SA_IDENTITY_DIAGNOSTIC.md` | the full SA≡evaluator identity diagnostic chain (key handoff asset) |
| `references/sa_identity_fix_plan.md` | the 3-stage execution plan (EXECUTED 2026-06-04) |
| `references/benchmark_results.md` | myopic baseline + post-fix results |
| `references/turhan2020_sa_params.md` | SA params + shared-objective IP+SA basis |
| `references/knust2019_delta_eval.md` | delta evaluation (O(1) incremental cost) |
| `references/portella2021_late_acceptance.md` | Late Acceptance criterion |
| `references/romer2019_dag_milp.md` | DAG/MILP formulation notes |

### Data
| Path | Role |
|------|------|
| `data/raw_inrc2/testdatasets_json/` | test instances: n005w4, n012w8, n021w4 (+ official Sol- solutions) |
| `data/raw_inrc2/datasets_json/` | larger instances: n030–n120, w4/w8 |
| `data/exchange/problem_exchange.json` | the layer-to-layer data contract |
| `data/exchange/pipeline_bench.json` | benchmark temp file (should be gitignored) |

---

## 5. The Cost-Function Identity Invariant (critical)

**Every layer must score the same schedule identically.** The MILP objective, the SA
`nurseCostFull`, and `penalty_evaluator` are three implementations of the *same* INRC-II
objective — same S1–S7 formulas, weights, and boundary rules.

If they drift, SA optimizes against a *wrong ruler* and can degrade a good MILP solution.
The 2026-06-04 fix removed three drifts — SD-1 (open-run scoring), SD-2 (flat vs proportional
min-violation), SD-3 (SA-only same-shift block) — plus carry-in misalignment, and moved
forbidden succession to a hard count (it is H3, not soft).

**Verification standard:** per-solution per-item equality `< 1e-6`, NOT a ratio. `ratio` is a
*pseudo-metric* — see `references/SA_IDENTITY_DIAGNOSTIC.md`. Guarded by
`tests/test_sa_identity.py` (800 random schedules; S2/S3/forbidden all `< 1e-6`).

---

## 6. Status Snapshot (live state in PROJECT_STATUS.md)

- ✅ MILP H2 skill-specific soft coverage
- ✅ SA≡evaluator consec cost identity (800 random + 10 carry-in cases)
- ⏭️ NEXT: hard coverage check (`return 999999`) freezes SA — replace with large soft penalty
- ⏭️ S4 weight one-constant fix (5 → 10)
- ⏭️ Look-ahead cross-week mechanism (the research contribution)
- ❌ Docker packaging (Phase 4)

---

## 7. Known Boundaries (honest)

- `penalty_evaluator` is NOT yet validated against the official INRC-II validator; SA is
  aligned to evaluator, so any evaluator-vs-official gap propagates. Confirm at n030+.
- Cross-week full-pipeline (MILP+F&O+SA over 4 weeks) output correctness verified only at
  single-week scale so far.
- `compare_fo_n030w4.py` exists but n030 full-pipeline benchmark is NOT confirmed complete.
