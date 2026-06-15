# Phase 2 — Cross-Week Look-Ahead: Design Notes (段1 Evidence Base)

This document is the evidence base for Phase 2 (look-ahead). It does not
propose a design — Sections 3–4 are placeholders for a future segment (段2).
See [`mischek2019_lookahead.md`](mischek2019_lookahead.md) for the primary
literature reference.

---

## 1. Empirical Target — current full pipeline, n012w8, weeks 0–7

Measured with the current MILP→F&O→SA full pipeline (post-ShiftTypeChange +
M_COVER fix, commit `7f0aa33`), instance `n012w8` (`numberOfWeeks: 8`, 8 weeks
of demand data confirmed available: `WD-n012w8-0.json` … `WD-n012w8-7.json`).
Per-week breakdown via `penalty_evaluator.evaluate()` on the SA output
schedule, with `history=0` (carry-in propagated week-to-week via
`_end_of_week_history`).

| Wk | sa_initial | sa_final | S1 | S2 (consec. work) | S3 (consec. off) | S4 (preferences) | forbidden (H3) | total |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 130.0 | 130.0 | 0 |   0 |  0 | 10 |  0 |  10 |
| 1 | 145.0 | 145.0 | 0 |  15 |  0 | 10 |  0 |  25 |
| 2 | 185.0 | 170.0 | 0 |   0 | 30 | 10 |  0 |  40 |
| 3 | 420.0 | 170.0 | 0 |  45 | 75 |  0 | 15 | 120 |
| 4 | 470.0 | 185.0 | 0 |  30 | 15 | 50 | 15 |  95 |
| 5 | 650.0 | 140.0 | 0 |  30 | 30 | 10 | 16 |  70 |
| 6 | 260.0 | 255.0 | 0 | 105 |  0 |  0 |  2 | 105 |
| 7 | 140.0 | 140.0 | 0 |   0 |  0 | 20 |  0 |  20 |
| **SUM** | | | 0 | 225 | 150 | 110 | 48 | **485** |

### Interpretation

- **S1 (coverage) is always 0** across all 8 weeks — the MILP+H2 fix
  (2026-06-03) and SA's M_COVER mechanism (2026-06-13/14) keep coverage
  fully satisfied throughout the horizon; coverage is not part of the
  cross-week pathology under the current pipeline.
- **The myopic W2→W3 escalation is still visible, but in a different shape
  than the MILP-only baseline.** `sa_initial` (SA's starting point, i.e. the
  MILP+F&O output before SA runs) jumps from 185 (W2) to 420 (W3) to 470 (W4)
  to 650 (W5) — a clear escalating-cost pattern in the *MILP+F&O* stage,
  consistent with the "imbalanced schedule, options used up in later weeks"
  pathology described by Mischek & Musliu (p. 125).
- **SA absorbs most, but not all, of this escalation.** `sa_final` for W3–W5
  drops back to 170/185/140 — SA's local search substantially repairs the
  MILP+F&O escalation each week. However, two residuals remain that SA does
  *not* fully repair:
  - **Forbidden-succession (H3) violations appear starting W3** (15, 15, 16)
    and persist through W5, dropping to 2 in W6 and 0 by W7. H3 is a *hard*
    constraint in INRC-II — its presence in the SA output for 4 consecutive
    weeks (W3–W6) is itself a candidate target for look-ahead (a
    week-boundary pattern that creates an unavoidable forbidden-succession in
    the next week, directly analogous to Mischek's S10\* "unresolvable
    patterns", p. 137–138).
  - **S2/S3 (consecutiveness) spikes recur**: S3=75 in W3 (vs. 30 in W2, 15 in
    W4), and S2=105 in W6 (vs. 0 in W5, 0 in W7) — both are isolated
    single-week spikes rather than a smooth trend, suggesting the pathology
    is driven by specific week-boundary states (history carry-in) rather than
    a monotonic resource-depletion curve.
- **Net effect**: the current full pipeline's *total* penalty over weeks 0–7
  (485) is dominated by S2 (225) and S3 (150), with H3 forbidden violations
  (48) as a secondary but hard-constraint-violating residual concentrated in
  W3–W6. This is the quantity Phase 2 look-ahead should aim to reduce,
  particularly the H3 violations (hard constraint) and the W3 S3 spike.

### Footnote — myopic baseline comparison caveat

> Myopic baseline number (n012w8 W3 = 390, S2 = 300) is taken from
> `benchmark_results.md` (2026-06-02), prior to subsequent MILP/parser/
> evaluator changes. The qualitative pathology (W2→W3 escalation driven by
> consecutiveness constraints under history propagation) remains the target;
> absolute deltas vs. the current full-pipeline numbers above should be
> interpreted with this caveat. Re-running the myopic MILP baseline under the
> current codebase is a separate task (out of scope for this segment).

---

## 2. INRC-II Finalist Cross-Week Strategy Survey

Source: Ceschia et al. (2019), *Ann. Oper. Res.* 274, 171–186
(`references/Ceschia(2019)_INRC-II_official_spec_hard_soft_constraints_definition.pdf`),
Table 1 (finalists, p. 181), Table 2 (final ranking, p. 182), and Sect. 6.1
"Finalists' search methods" (p. 182–183).

| Rank | Team | Architecture | Cross-week / look-ahead mechanism | Fit with our MILP+F&O+SA architecture |
|---:|---|---|---|---|
| 1 | **NurseOptimizers** (Römer & Mellouli) | Network-flow MILP (DAG per nurse) | **Deterministic look-ahead**: relaxes integrality and extends the planning period with an *anticipation period*, whose demand data is **artificially generated from the current and previous weeks' demand** (p. 183) | Closest to our outer MILP layer (already DAG/flow-documented in `romer2019_dag_milp.md`). Synthetic-demand anticipation horizon could extend `MilpModel` without touching the inner SA — but is a structural MILP change (Rule 6 segmentation). |
| 2 | **Polytechnique Montreal** (Legrain et al.) | MIP + column generation | To anticipate future requirements, **costs are modified and constraints are added**; at each stage several candidate schedules are generated and the best is selected (p. 183) | "Modify costs / add constraints to anticipate future weeks" is the same *flavor* as Mischek's S6\*/S7\*/S8\*/S10\* — portable as additional soft terms in `MilpModel`, without column generation. |
| 3 | **SSHH** (Kheiri et al.) | Sequence-based selection hyper-heuristic (HMM-driven low-level heuristics) | Generates **demand of the coming weeks from current information** and solves the *whole anticipated horizon* before committing to the current week (p. 183) | Heuristic-side anticipation requires synthesizing future demand — higher complexity; not a natural fit for our inner SA which operates on a single fixed week's exchange JSON. |
| 4 | Hust.Smart (Su et al.) | Iterated Tabu Search (greedy init + intensify/diversify) | No cross-week mechanism described in Sect. 6.1 | Architecturally closest to our inner SA layer (Tabu/SA-family local search), but the paper gives no look-ahead mechanism to borrow. |
| 5 | **ORTEC** (Jin et al.) | Local search (commercial ORTEC Workforce Scheduling) | Added **artificial soft constraints that ensure a feasible connection between two consecutive weeks** (p. 183) | Directly analogous to Mischek's S9\*/S10\* and to the H3/S3 week-boundary residuals observed in Sect. 1 above — a small set of "connection feasibility" soft constraints addable to MILP and/or SA delta evaluation without a structural rewrite. |
| 6 | LabGOL (Picca Nicolino et al.) | Hyper-heuristic combining Tabu Search / Local Search / VNS (ILS + MultiStart) | No cross-week mechanism described in Sect. 6.1 | Same family as our SA inner layer; no specific mechanism to port. |
| 7 | ThreeJohns (Tassopoulos et al.) | Modified Variable Neighbourhood Search with ad-hoc escape procedure | No cross-week mechanism described in Sect. 6.1 | No specific mechanism to port. |

### Commentary

- Ceschia et al. (p. 182–183) explicitly note: of the two main directions for
  handling the multi-stage nature of the problem — (a) adding auxiliary
  constraints to the current formulation (ORTEC), vs. (b) extending the
  rostering period at each stage to solve the current stage together with
  *anticipated* future stages (NurseOptimizers, SSHH, Polytechnique Montreal)
  — **direction (b) "seems to work better in the competition context, since
  the top three all exploited ideas in this direction"** (p. 183).
- However, all three top-3 "anticipation horizon" approaches require
  **synthetically generating future-week demand data**, which is a
  significant structural addition (new MILP variables/rows for fabricated
  future weeks, or a heuristic-side demand generator).
- The **ORTEC-style "connection feasibility" soft constraints** (direction a)
  are structurally the smallest change, and map directly onto the H3/S3
  week-boundary residuals already observed empirically in Section 1
  (forbidden successions in W3–W6, S3 spike in W3) — these do not require any
  future-demand synthesis, only knowledge of the *current* week's end-state
  and the *next* week's sequence-constraint parameters (already available via
  the scenario file, per Mischek's S9\*/S10\*, see
  `mischek2019_lookahead.md`).

---

## 3. Design Options

*TBD in 段2.*

---

## 4. Selected Design

*TBD after human review.*
