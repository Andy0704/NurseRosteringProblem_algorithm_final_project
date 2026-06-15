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

### Post-H3-fix re-measurement (2026-06-15)

The 2026-06-15 fix (`fix: H3 forbidden_succession leak in SA (M_FORBID +
best_sched gate, p0=0.05)`) added an `M_FORBID` big-M penalty (mirroring
`M_COVER` for H2) to all three SA delta functions, and extended the
`best_sched` gate to require `totalForbiddenViolations(sched) == 0` in
addition to `totalH2Units(sched) == 0`. Re-running the same n012w8 weeks
0-7 measurement with the fixed binary:

| Wk | sa_initial | sa_final | S1 | S2 | S3 | S4 | forbidden (H3) | total |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 130 | 130 | 0 |   0 |  0 | 10 | 0 |  10 |
| 1 | 145 | 145 | 0 |  15 |  0 | 10 | 0 |  25 |
| 2 | 185 | 170 | 0 |   0 | 30 | 10 | 0 |  40 |
| 3 | 420 | 415 | 0 | 285 |  0 |  0 | 0 | 285 |
| 4 | 140 | 140 | 0 |   0 |  0 | 20 | 0 |  20 |
| 5 | 120 | 120 | 0 |   0 |  0 |  0 | 0 |   0 |
| 6 | 130 | 130 | 0 |   0 |  0 | 10 | 0 |  10 |
| 7 | 130 | 130 | 0 |   0 |  0 | 20 | 0 |  20 |
| **SUM** | | | 0 | 300 | 30 | 80 | **0** | **410** |

#### Side-by-side: pre-fix vs. post-fix

| Wk | pre-fix total | pre-fix H3 | post-fix total | post-fix H3 |
|---:|---:|---:|---:|---:|
| 0 |  10 |  0 |  10 | 0 |
| 1 |  25 |  0 |  25 | 0 |
| 2 |  40 |  0 |  40 | 0 |
| 3 | 120 | 15 | 285 | 0 |
| 4 |  95 | 15 |  20 | 0 |
| 5 |  70 | 16 |   0 | 0 |
| 6 | 105 |  2 |  10 | 0 |
| 7 |  20 |  0 |  20 | 0 |
| **SUM** | **485** | **48** | **410** | **0** |

#### Interpretation

- **H3 forbidden-succession violations are fully eliminated** (48 -> 0
  across the whole 8-week horizon), confirming the M_FORBID + best_sched
  gate fix works as designed. No fail-loud "incoming schedule has N H3
  violations" warning fired for any week (MILP+F&O seeds remained
  H3-clean, as expected from the diagnostic).
- **The total penalty over weeks 0-7 dropped from 485 to 410** (-15.5%),
  so the fix is a net improvement at the horizon level.
- **However, the cross-week pathology did not disappear -- it relocated
  to W3.** Pre-fix, W3's total was 120 (S2=45, S3=75, forbidden=15);
  post-fix, W3's total is 285, entirely S2 (consecutive working days),
  with S3 and forbidden both now 0. W4-W7 improved dramatically
  (95/70/105/20 -> 20/0/10/20), consistent with the hypothesis that the
  H3 violations in W3-W6 were a *secondary* symptom of an underlying
  W2->W3 history-carry-in pathology: once SA is forced to resolve the
  W3 boundary state without using forbidden successions as an escape
  valve, it pays the cost as S2 in W3 itself instead of leaking H3
  violations (and downstream S2/S3 spikes) into W4-W6.
- **Net effect for Phase 2**: the *hard*-constraint problem (H3) is
  solved, and the *total* improved, but the single-week S2=285 spike in
  W3 is now the dominant remaining residual (69.5% of the entire
  8-week total). This is a sharper, more concentrated target than the
  previous diffuse S2(225)+S3(150)+forbidden(48) picture, and is exactly
  the kind of single-week, history-carry-in-driven spike that Mischek's
  S9*/S10* and ORTEC's "connection feasibility" soft constraints
  (Section 2 above) are designed to address.

### Footnote — myopic baseline comparison caveat

> Myopic baseline number (n012w8 W3 = 390, S2 = 300) is taken from
> `benchmark_results.md` (2026-06-02), prior to subsequent MILP/parser/
> evaluator changes. The qualitative pathology (W2→W3 escalation driven by
> consecutiveness constraints under history propagation) remains the target;
> absolute deltas vs. the current full-pipeline numbers above should be
> interpreted with this caveat. Re-running the myopic MILP baseline under the
> current codebase is a separate task (out of scope for this segment).

---

## W3 Spike Localization (H1 vs H2 experiment)

Following the post-H3-fix re-measurement above, W3's `total=285` (all S2,
i.e. consecutive-working-days violations) is 69.5% of the entire 8-week
total. Before designing Phase 2, this section distinguishes whether the
spike is caused by W2's carry-in history (cross-week, Hypothesis 1) or is
intrinsic to W3's own week-data (myopic, Hypothesis 2), via two runs of
n012w8 W3 through the same MILP+F&O+SA pipeline:

- **Run A (baseline)**: carry-in history propagated W0->W1->W2 via
  `_end_of_week_history` (the same setup as the post-H3-fix table above).
- **Run B (synthetic clean history)**: `inrc2_parser.parse(instance_dir,
  week=3, history=0)` — this loads W3's demand file (`WD-n012w8-3.json`)
  together with the canonical zero-history file `H0-n012w8-0.json` (the
  same file used for week 0; `history` only selects the `H0-*` file, not
  the demand week). No history was hand-constructed (Rule 14).

### Run A (W0->W1->W2 carry-in, baseline)

| sa_initial | sa_final | S1 | S2 | S3 | S4 | forbidden (H3) | total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 420 | 415 | 0 | 285 | 0 | 0 | 0 | 285 |

### Run B (canonical zero history, W3 demand)

| sa_initial | sa_final | S1 | S2 | S3 | S4 | forbidden (H3) | total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 100 | 0 | 0 | 0 | 0 | 0 | 0 |

### Delta (A - B)

| Component | Run A | Run B | Delta |
|---|---:|---:|---:|
| S1_coverage | 0 | 0 | 0 |
| S2_consecutive_work | 285 | 0 | **285** |
| S3_consecutive_off | 0 | 0 | 0 |
| S4_preferences | 0 | 0 | 0 |
| forbidden_succession_violations | 0 | 0 | 0 |
| **total** | **285** | **0** | **285** |

### W2-end carry-in: consecutive_working_days vs. contract max

The carry-in history that Run A used (`_end_of_week_history` after W2's SA
output), per nurse:

| nurse | consec_working_days_at_W2_end | contract_max | stretch tail |
|---|---:|---:|---|
| Alice | 4 | 5 | near |
| Bob | 5 | 5 | **yes** |
| John | 5 | 5 | **yes** |
| Kate | 0 | 5 | no |
| Mary | 5 | 5 | **yes** |
| Paul | 5 | 5 | **yes** |
| Arthur | 0 | 5 | no |
| Pier | 5 | 5 | **yes** |
| Lucy | 2 | 5 | no |
| Maggie | 3 | 5 | no |
| Patrick | 0 | 5 | no |
| Jane | 0 | 5 | no |

5 of 12 nurses (Bob, John, Mary, Paul, Pier) ended W2 already *at* their
contract's `maximumNumberOfConsecutiveWorkingDays` (5), and one more
(Alice) ended one day short (4/5, "near"). Each of these nurses is
therefore forced to take day 0 of W3 off (or risk an immediate S2
over-max violation) purely because of their W2 end-state — independent of
W3's own demand.

### Interpretation

- **Run B (S2=0, total=0) is dramatically lower than Run A (S2=285,
  total=285)** — the full delta of 285 is attributable to the W0->W1->W2
  carry-in history, not to W3's own week-data. With a clean/zero history,
  W3's demand alone produces a perfectly satisfiable schedule (total=0).
- **Hypothesis 1 is confirmed**: the W3 S2=285 spike is a **cross-week
  pathology** caused by W2's end-of-week state, not a myopic
  intrinsic-difficulty of W3 itself.
- **Mechanism**: 5/12 nurses ended W2 at their `max_consec_work` (5/5)
  and 1/12 ended one day short (4/5) — exactly the "stretch tail" pattern
  Mischek's S10* targets (p. 137-138): a work-stretch that has already
  reached (or is one day from) its maximum at the week boundary, forcing
  a day off in week `w+1` regardless of week `w+1`'s own demand. With 6
  of 12 nurses simultaneously in this state at the W2->W3 boundary, W3's
  MILP+F&O+SA must absorb a large, synchronized forced-day-off pattern
  that W3's demand data alone does not require, producing the S2=285
  spike.
- **Design-space implication (not a design — per task scope)**: Phase 2
  should enter the **cross-week / carry-in design space** (Mischek
  S10*-style end-of-week stretch avoidance, or ORTEC-style connection
  soft-constraints in W2's own model, Section 2 above) rather than
  single-week heuristic or MILP-reformulation changes to W3 in isolation
  — Run B shows W3's own week-data is not the bottleneck.

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
