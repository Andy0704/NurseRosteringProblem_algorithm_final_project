# Project Context
This project implements a hybrid optimization algorithm (Matheuristic) to solve the Nurse Rostering Problem (NRP), specifically adhering to the standards and benchmarks of the Second International Nurse Rostering Competition (INRC-II). 
The architecture is divided into two decoupled layers:
- Outer Layer: Managed in Python, responsible for the global coordination, parsing INRC-II data, and modeling the Mixed-Integer Linear Programming (MILP) components.
- Inner Layer: Managed in C++, optimized for high-performance metaheuristics (e.g., Simulated Annealing, Local Search, Tabu Search) to optimize local schedules.

# About Me
- Role: Lead Architect and Outer-Layer Developer.
- Responsibilities: Defining system specifications, data exchange standards, creating the MILP mathematical formulations, and managing the overall workflow coordination.
- Team Dynamic: I establish the system rules and data boundaries. My teammates implement the internal C++ heuristic engines based on my definitions.

# Architectural Rules (System Boundaries)
1. **Strict Decoupling**: Python (Outer MILP) and C++ (Inner Heuristic) must remain strictly decoupled. Communication is restricted to file-based or string-based JSON via Python's `subprocess` module.
2. **Data Exchange Contract**: All cross-language communication must strictly adhere to the schema of `problem_exchange.json`. No dynamic or loosely-typed fields outside the specification are allowed.
3. **Rigid Schedule Representation**: Current roster data must always use the 2D integer array format: `matrix[nurse_index][day_index]` mapping to a predefined `shift_index`.
4. **INRC-II Standards**: Logic, terminology, and hard/soft constraint evaluations must strictly align with the Second International Nurse Rostering Competition (INRC-II) definitions.

# Agent Behavioral Rules (Execution & Coding Standards)
1. **Think Before Coding**:
   Before outputting any codebase or modifications, analyze existing logic first. Explicitly state your assumptions, inputs, outputs, and algorithmic complexity.
2. **Surgical Modifications Only**:
   Do not rewrite entire files. Minimize code diffs by modifying only the precise lines necessary (e.g., specific heuristic moves or constraints), preventing side effects on math models.
3. **Keep It Simple & Minimalist**:
   Prefer clean, readable loops and native data structures. Avoid over-engineering, unnecessary design patterns, or introducing third-party libraries without consent (except `nlohmann/json` for C++). Only add, do not modify existing rules.
4. **Fail Loudly & No Silent Failures**:
   Implement aggressive error handling at the language boundaries. If C++ JSON parsing fails or `subprocess` crashes, it must throw descriptive errors and exit with a non-zero code immediately. No silent failures.
5. **Deep Testing (Verify 'Why', Not Just 'If')**:
   When writing tests for constraints or schedule validity, do not just check boolean success. Ensure the test validates *why* a specific penalty score or constraint violation occurred based on INRC-II rules.
6. **Step-by-Step Reporting + Pre-Execution Segmentation**: 
   For complex multi-step tasks, execute and report after each individual step, waiting for human approval before proceeding.  
   Additional: If a single plan exceeds about 150 lines or involves more than 3 code changes plus tests, it must be segmented before execution according to dependency boundaries (typical: read-only analysis → changes + narrow verification → broad verification), with each segment stopping to report.
7. **Adhere to Pre-existing Styles**:
   Read the project structure and existing code style before implementing new functions. Do not introduce alternative paradigms, variable naming conventions, or structural variations.
8. **No Proxy Metrics for Correctness**:  
   When verifying whether two components are consistent, the only standard is per-solution exact equality (<1e-6), comparing item by item. Using proxy metrics such as ratio, normalization, or "not too far off" to determine correctness is prohibited. A ratio close to 1 does not prove common origin. An indicator that can pass but does not prove correctness is more dangerous than having no indicator at all.
9. **Isolate Components Before Asserting**:  
   Before comparing the sum of multiple components (e.g., total penalty), each item must be separated and compared individually (S1/S2/S3/S4/forbidden each compared separately). Aggregated assertions can disguise "discrepancies in unverified items" as "bugs in the current change." If an item is known to be non-identical, it should be clearly marked as known-divergent and excluded from the total sum; it must not be mixed into the aggregate.
10. **Verify Assumptions Against Data, Not Semantics**:  
   Any premise such as "X cannot happen simultaneously," "this value must be 0," or "the two are semantically equivalent," must be validated against actual data using scripts before using it to simplify logic (especially when replacing actual values with boolean proxies). The scope of the data scan should be recorded. Semantic validity ≠ validity in data. If the premise is a one-time gate, indicate the "silent failure mode if violated in the future."
11. **Surrogate vs Drift**:  
   When two components compute the same concept but yield different results, first determine qualitatively whether this is an "intentional design" (e.g., for accelerated delta evaluation or proxy cost for multi-objectives) or an "implementation drift" (each implemented differently and incorrectly).  
   If it is drift → fix it back to the same source (align to a single source of truth), do not try to preserve order, do not align numbers, and do not retroactively package it as an objective design.  
   Delta evaluation is an O(1) precise incremental update for the same goal, not another function.
12. **Define Objective Membership Explicitly**:
   Each penalty term must clearly specify "whether it is included in the final optimization objective total, at which layer it is included, and with what weight."
   If a term is included in the total at layer A but not at layer B, this constitutes a structural homology contradiction.
   Simply "comparing the count of that term" will bypass rather than resolve the issue.
   The total membership of hard constraints (such as H3 forbidden=0) and soft constraints must be consistent across both layers.




# Project Structure
```text
NRP_Claude_Agent/
├── config.json                 # Runtime config: instance path, iterations, solver params
├── CLAUDE.md                   # AI behavioral contract and architecture rules
├── SKILL.md                    # Encapsulated automation skills (project root)
├── README.md                   # Public API and spec documentation
│
├── data/
│   ├── raw_inrc2/
│   │   ├── testdatasets_json/  # Small instances: n005w4, n012w8, n021w4 (with ref solutions)
│   │   └── datasets_json/      # Production instances: n030–n120 (4-week and 8-week)
│   └── exchange/
│       └── problem_exchange.json  # Cross-language data contract (Python ↔ C++)
│
├── outer_milp/                 # Python Outer Layer — Lead Architect focus
│   ├── __init__.py
│   ├── main.py                 # Orchestration loop: MILP → C++ heuristic → F&O → repeat
│   ├── models/
│   │   ├── __init__.py
│   │   └── milp_model.py       # MILP formulation: build(), solve(), fix_and_optimize()
│   └── utils/
│       ├── __init__.py
│       ├── inrc2_parser.py     # Converts INRC-II JSON (Sc/WD/H0) → problem_exchange.json
│       ├── json_handler.py     # Fail-loud UTF-8 load/save for problem_exchange.json
│       ├── validate_schema.py  # CLI schema checker: exits 0 (valid) or 1 (invalid)
│       ├── penalty_evaluator.py  # Standalone penalty breakdown: S1–S7 + forbidden succession
│       └── multi_week_runner.py  # Multi-week sequential solver with history propagation
│
├── inner_heuristic/            # C++ Inner Layer — Teammate focus
│   ├── CMakeLists.txt          # C++17 build config
│   ├── build/
│   │   └── nrp_heuristic       # Compiled binary (158 KB)
│   ├── include/
│   │   ├── heuristic.h         # runHeuristic() declaration
│   │   └── nlohmann/
│   │       └── json.hpp        # Header-only JSON library
│   └── src/
│       ├── main.cpp            # CLI entry: reads JSON → runHeuristic() → writes JSON
│       └── heuristic.cpp       # SA + Late Acceptance + Delta Evaluation engine
│
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py        # pytest: parser, schema, penalty_evaluator (4/4 passing)
│
├── references/                 # Algorithm implementation guides (auto-generated from papers)
│   ├── knust2019_delta_eval.md
│   ├── turhan2020_sa_params.md
│   ├── portella2021_late_acceptance.md
│   └── romer2019_dag_milp.md
│
├── skills/
│   └── SKILL.md                # Project automation skills
│
└── docker/
    └── Dockerfile              # Environment replication (Phase 4 — not started)
```

# Reference Papers (Algorithm Design Basis)
- Turhan & Bilgen (2020): Matheuristic foundation, SA + Fix-and-Optimize hybrid
- Ceschia et al. (2019): INRC-II official spec, hard/soft constraints definition
- Knust & Xie (2019): SA operators (TwoWaySwap, SwapSequences), Delta Evaluation
- Mischek & Musliu (2019): Look-ahead constraints (S9*, S10*) for multi-stage
- Römer & Mellouli (2019): Network Flow MILP, DAG-based schedule modeling
- Portella (2021): Late Acceptance F&O, M1/M2/M3 formulation comparison

# Algorithm Parameters:
   SA: T0=20×max_cost, β=0.9, COOL_EVERY=30000, T_MIN=10, NO_IMPROVE_MAX=500000
   Late Acceptance: γ=150, acceptance: Z(s') < L[iter mod 150]
   Fix-and-Optimize: nurse decomposition, free_count=2, trigger on no-improvement

# Common Commands

- Build C++:            `cd inner_heuristic && mkdir -p build && cd build && cmake .. && make -j4`
- Run C++ tests:        `cd inner_heuristic/build && ./run_unit_tests`
- Run Python solver:    `python outer_milp/main.py --config config.json`
- Validate JSON schema: `python outer_milp/utils/validate_schema.py data/exchange/problem_exchange.json`
- Run tests: python3 -m pytest tests/ -v
- Multi-week: python3 outer_milp/utils/multi_week_runner.py --instance data/raw_inrc2/testdatasets_json/n005w4
- Full pipeline: python3 outer_milp/main.py --config config.json

## Git Setup (run once per new WSL environment)
git config user.email "candy070405@gmail.com"
git config user.name "andy0704"

## Git Workflow
- Before any major change: git add -A && git commit -m "checkpoint: <description>"
- Check what changed: git diff HEAD
- Revert last change: git checkout -- <file>

## Session Lifecycle Rules

**SESSION START** — 每次新 session 的第一件事：
1. Read PROJECT_STATUS.md
2. Read CLAUDE.md
3. 用 PROJECT_STATUS.md 中的 Component Status 和 Next Steps 作為主要上下文
4. 不需要 scan 所有檔案，除非 task 明確需要

**SESSION END / TASK COMPLETE** — 每次任務完成或中斷前：
1. 更新 PROJECT_STATUS.md（surgical edit only）：
   - 修改 Last Updated（時間 + session 名稱）
   - 只更新本次有變動的 Component Status 列
   - 在 Recent Changes 最頂端 prepend 一行（格式：[YYYY-MM-DD] type: 描述）
   - 勾選已完成的 Next Steps，新增新發現的待辦
   - 若發現新問題，append 到 Known Issues
2. git add PROJECT_STATUS.md && git commit -m "chore: update project status"
3. 禁止重寫整個 PROJECT_STATUS.md；只能修改變動的行