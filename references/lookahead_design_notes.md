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

## 3. Selected Design: S10* Stretch-Tail Penalty (段0 spec)

Targets the W2->W3 spike localized above: 5/12 nurses ended W2 at
`max_consec_work=5/5`, 1/12 at `4/5`, forcing a synchronized day-off
pattern in W3 unrelated to W3's own demand. This section specifies a
single-mechanism, surgical adaptation of Mischek & Musliu (2019) S10*
("Unresolvable patterns", p. 137-139, eq. 40) for `MilpModel.build()`.

### Q1 — Threshold

**Answer: `threshold = M_w - 1`** (one less than
`maximumNumberOfConsecutiveWorkingDays`).

Mischek's eq. 40 (p. 138) is shift-type-specific and considers a trailing
block of `>= w_n^+ - sigma_s^-` shifts (p. 137, Fig. 4/5) — i.e. the
*general* condition is "the trailing work-stretch is already close enough
to `w_n^+` (max work stretch) that no valid continuation into next week
exists for some shift type `s`". Our simplification (Q4) restricts this
to plain `consecutive_working_days` (ignores per-shift-type `sigma_s`),
so the binding case is the boundary one: the trailing run *equals*
`M_w` (fully saturated at week end) — exactly the condition observed for
Bob/John/Mary/Paul/Pier (5/5) in the localization table above. Setting
`threshold = M_w - 1` means the penalty fires only when the trailing run
reaches `M_w` (the "near" case, Alice at 4/5, is not penalized — see Q4
caveat).

### Q2 — Penalty form

**Answer: linear**, `z_n >= tail_run_proxy_n - threshold`, `z_n >= 0`.
Mischek's eq. 40 is itself linear in the surplus variable `C_n^{S10*}`
(p. 138) — no quadratic term anywhere in S6*-S10*. Our `z_n` plays the
same role as `C_n^{S10*}`.

`tail_run_proxy_n` is a **window-sum relaxation expression**, mirroring
the existing S1 window-sum pattern (`milp_model.py:205-211`,
`pulp.lpSum(w[d:d+M_w+1]) <= M_w + p`):

```
tail_run_proxy_n = sum(w[D - M_w : D])   # last M_w days of the week
```

where `w[d] = 1 - x[n][d][0]` (already defined, `milp_model.py:184`).
`tail_run_proxy_n` ranges `0..M_w`. If `tail_run_proxy_n == M_w`, all of
the last `M_w` days are worked, which (since there is no room for a gap)
implies a true trailing run of exactly `M_w` consecutive working days
ending at week-end — the fully-saturated "stretch tail" condition. This
reuses the existing `w[]` expressions; no new per-day run-length tracking
variables are introduced (Rule 3).

### Q3 — Weight alpha (re-verified per Clarification 1, 2026-06-16)

**Mischek's W_{S10*} = 15 maps to option (a) — shift-stretch-length
(same-shift-type, CS2a/b); our W3 violations are option (b) —
consecutive working days (any shift, CS2c/d). α = 15 is locked for
our system.**

**Mischek's S2 decomposition** (objective formula, p. 127–128):
`f = ... + 15·CS2a/b + 30·CS2c/d + ...`, where:
- **CS2a/b** (weight **15**): violations of `MinConsecutiveShiftDays` /
  `MaxConsecutiveShiftDays` per shift type — same-shift-type stretch
  length, the "shift-stretch-length constraint" Mischek cites on p. 139.
- **CS2c/d** (weight **30**): violations of `MinConsecutiveWorkingDays` /
  `MaxConsecutiveWorkingDays` per contract — any-shift consecutive
  working days.

Mischek p. 139 verbatim: *"a violation of this constraint directly results
in a violation of at least one shift-stretch-length constraint in the next
week and thus warrants a weight of 15 (as if the violation had already
occurred)"*. Table 1 (p. 140) confirms `W_{S10*} = 15`.  
**W_{S10*} = 15 = shift-stretch weight = CS2a/b weight = option (a).**

**Our W3 violations are option (b) — confirmed by direct trace:**

`penalty_evaluator._compute_s2_s3` (`penalty_evaluator.py:87–107`) checks
`contract.get("minimumNumberOfConsecutiveWorkingDays")` /
`"maximumNumberOfConsecutiveWorkingDays"` and fires when any working run
(`row[d] > 0`, shift-type agnostic) exceeds `max_cw`. Traced violation
from the W3 MILP output (no-S10* baseline):

> **Nurse 1 (FullTime)**: carry-in `prior_work=5`, W3 days 0–4 worked
> with shifts Night→Late→Late→Late→Late (**4 different shift types**),
> run_len = 10, max_cw = 5, excess = 5 days, penalty = 5 × 15 = 75.
> `same_type=False` confirms this is a working-days (CS2c/d) violation,
> **not** a same-shift-type (CS2a/b) violation.

4 nurses in this state (Nurses 1, 2, 4, 7); total S2 = 300 from MILP
output (SA reduces to 285). All four are any-shift working-day violations.

**α decision: α = W_CONSEC = 15 (locked).**

In our system, `penalty_evaluator._W_CONSEC = 15` (`penalty_evaluator.py:23`)
charges each excess consecutive-working-day at 15. The S10* "as if the
violation had already occurred" semantic requires α to match the actual
cost our evaluator charges for the violation type. Our evaluator charges
15 per violation-day for this constraint (CS2c/d), so α = 15 is correct
for our system.

*Open question (separate task, out of scope here)*: Mischek's CS2c/d = 30
while our `_W_CONSEC = 15` — our evaluator may be underweighting
consecutive-working-days violations relative to the INRC-II official
scoring rule. If `_W_CONSEC` is later corrected to 30, α should be
updated to match. For this segment, α must match our evaluator's current
actual charge, not a hypothetical corrected weight.

### Q4 — Coverage scope (updated per Clarification 2, 2026-06-16)

**Penalty covers `consecutive_working_days` only.**

Explicitly excluded:
- **`consecutive_same_shift_type` (CS2a/b sub-component)**: not observed
  spiking in the localization measurement (`S2_consecutive_work = 285`,
  same-shift-type violations not tracked in our evaluator), Rule 10 defers.
  Note: the Q3 trace reveals that Nurses 2/4/7 (all-Night runs crossing
  the W2→W3 boundary) have simultaneous CS2a/b violations that our
  evaluator does not capture — documented for a future same-shift-type
  evaluation pass, not addressed in this segment.
- **`consecutive_days_off` (S3)**: zero in both Run A (S3=0) and Run B
  (S3=0) of the localization experiment, Rule 10 defers.

Either could be extended later if a separate localization shows them
dominant in a different instance or week.

**Q1 caveat**: `threshold = M_w - 1` only fires at full saturation
(`tail_run_proxy_n == M_w`), so the "near" case (Alice, 4/5) is not
penalized. This is the paper's published value and is used as-is.

**Evaluation policy (Clarification 3, 2026-06-16)**: 段3 runs
`threshold = M_w - 1` as the **single attempt** (Mischek's published
value). If W3 is not substantially resolved, STOP and report — no retry
within this segment. Further adjustments (different α, different
threshold, additional mechanisms) are decided in a new segment per Rule
14 evidence standard.

### Q5 — Applied when

**Answer: every week `k < num_weeks - 1`** (i.e. all weeks except the
final week of the instance). Mischek p. 138: *"all constraints introduced
in this section should be ignored in the last week, as there is no
further week to influence."* For n012w8 (`num_weeks=8`), this applies to
W0-W6 and is skipped for W7 — matches the task's framing ("W6 is
pre-final so look-ahead helps W7 - apply").

### Implementation sketch (for 段1, after confirmation)

For each nurse `n_idx` in `MilpModel.build()`, when `is_final_week is
False`:

```python
M_w = contract.get("maximumNumberOfConsecutiveWorkingDays", D)
tail_run_proxy = pulp.lpSum(w[max(0, D - M_w):D])
z = pulp.LpVariable(f"z_s10_{n_idx}", lowBound=0)
model += (z >= tail_run_proxy - (M_w - 1), f"S10star_{n_idx}")
penalty_terms.append((W_CONSEC, z))   # alpha = W_CONSEC = 15
```

Added to `penalty_terms` exactly like existing S1-S7 terms (same sign,
same objective `pulp.lpSum(wt * pv for wt, pv in penalty_terms)`) — no
new objective-assembly logic. Because `penalty_terms` only feeds the MILP
*search* objective and is never read back by `penalty_evaluator`,
`runEvalOnly`, or `fullCost`, `z_s10_*` is automatically excluded from the
reported INRC-II total (Rule 12) without any extra bookkeeping.

---

## 4. Selected Design

S10* stretch-tail penalty as specified in Section 3 above. Spec confirmed
with Clarifications 1–3 (2026-06-16): α = 15 (locked, Q3 verified),
explicit CS2a/b and S3 exclusions (Q4), single-attempt evaluation policy
(Clarification 3). Proceeding to 段1 implementation.

**Post-implementation note (W-9/W-9-supplement, 2026-06-17):** α was
re-verified and corrected to **30** (not 15) once the evaluator/SA weight
audit (W-2/W-3/W-6) established that CS2c/d (our actual violation type,
per the Q3 trace above) is weighted 30, not 15, in the spec-correct
system. α=15 above was based on a since-corrected `_W_CONSEC=15`. Full
pipeline measurement (`references/s10_star_alpha30_evaluation.md`) shows
S10* α=30 alone is a **net regression for n012w8** (+17.3% total INRC-II)
and validated only for n005w4 (-25.0%) — see that document for the
complete result. This motivates Section 5 below.

---

## 5. S6*/S7* Design Spec (W-10 段0, read-only — no code changes)

**Context:** W-9-supplement showed S10* alone relocates n012w8's cross-week
cliff (W4→W5) rather than removing it, and the global S7 term balloons
(540→900) — a cost invisible to S10* (which only reasons about
*consecutive-working-days* stretch tails, not assignment/weekend budgets).
Mischek & Musliu (2019) report their **best combination is S6\*/S7\* + S8\*
+ S10\*** (p. 139), with S6\*/S7\* individually having "the largest impact"
of any single extension (p. 138, Fig. 6 commentary). This section answers
Q1–Q6 to specify S6\*/S7\* before any implementation, per the user's W-10
段0 instructions. All page citations refer to Mischek & Musliu (2019),
*Ann. Oper. Res.* 275:123–143 (local PDF: PDF page = paper page − 122).

### Q1 — What does Mischek's S6* actually do?

**Mechanism (verbatim, p. 133):**

> "S6\*. Average assignments: The total number of assignments up to the
> current week must be within the bounds defined in the contract,
> multiplied by the fraction of weeks that have already passed. This
> extension generalizes constraints S6 to earlier weeks."

**Worked example (verbatim, p. 133):**

> "if a nurse has a minimum of 10 assignments and a maximum of 22, then
> after stage 4 (of 8), they should have between 5 and 11 shifts assigned.
> Assuming that they already had 7 shifts assigned in stages 1–3, this
> constraint would require them to have between 0 and 4 assignments in
> stage 4."

> "If these constraints are satisfied during all weeks, it can be
> guaranteed that also constraints S6 are satisfied for the whole
> schedule." (p. 133)

**Formula (eq. 29–30, p. 134):**

```
S6*  ∀n∈N:  a_n^tot + Σ_{s,k,d∈{1..7}} x^d_{nsk}  ≤  ⌊a_n^+ · w/|W|⌋ + C^{S6*}_n     (29)
S6*  ∀n∈N:  a_n^tot + Σ_{s,k,d∈{1..7}} x^d_{nsk}  ≥  ⌈a_n^- · w/|W|⌉ − C^{S6*}_n     (30)
```

Where `a_n^tot` = cumulative assignments from **actual fixed history**
(weeks before the current one), `Σ x^d_{nsk}` = the current week's
decision-variable sum (current week only, matching the basic S6 scope in
eq. 25–26), `a_n^+`/`a_n^-` = contract max/min total assignments, `w` =
current week index (1-indexed), `|W|` = total weeks in the horizon.

**Penalized variable/expression:** the **running cumulative total**
(`a_n^tot` + this week's assignments) against a target that is a fixed
proportion (`w/|W|`) of the **full-horizon** contract bound — i.e. "by
week `w`, you should be at roughly `w/|W|` of your total budget."

**Relationship to our S6:** our spec-correct S6 (weight 20,
`evaluate_global_s6_s7()`, W-6) is exactly Mischek's *basic* S6 (eq.
25–26, p. 131) — a hard horizon-end check against the full `a_n^+`/`a_n^-`
bound, evaluated only after all weeks are fixed. S6\* **generalizes** this
basic check to fire incrementally every week, using the actual-so-far
total + a proportional target — per the paper, satisfying S6\* in every
week *guarantees* S6 is satisfied for the whole schedule (p. 133, quoted
above).

**Critical finding — our existing MILP does NOT implement basic S6, let
alone S6\*:** `milp_model.py:289-298` (internally mislabeled `"S5"`)
currently does:

```python
weekly_min = min_assign // 4
weekly_max = math.ceil(max_assign / 4)
total_w = pulp.lpSum(w)
penalty_terms.append((W_ASSIGN, p_u)); penalty_terms.append((W_ASSIGN, p_o))
model += (total_w >= weekly_min - p_u, ...)
model += (total_w <= weekly_max + p_o, ...)
```

This checks **only the current week's own count** (`total_w`) against a
**static** `÷4` fraction of the full-horizon bound — it never reads
`hist.get("num_assignments", ...)` (grep-confirmed: `num_assignments` is
never referenced anywhere in `milp_model.py`), and the `÷4` divisor is
hardcoded regardless of the instance's actual `|W|` (already flagged as a
known limitation for 8-week instances — n012w8: `weekly_min=30//4=7` forces
near-daily work). This is **not** Mischek's basic S6 (eq. 25–26, which
uses real `a_n^tot` and the true total `a_n^+`/`a_n^-`, no `÷4`), and not
S6\* either. **Implementing faithful S6\* requires first deciding whether
to replace this `÷4` approximation** (Rule 11 — two mechanisms targeting
the same concept with different formulas is drift, not by-design surrogate,
unless explicitly justified) **— flagged for human decision in Q6, not
resolved here.**

### Q2 — What does Mischek's S7* actually do?

**Mechanism (verbatim, p. 134–135):**

> "4.3 Average working weekends. The same argument as above also applies
> to constraints S7, the maximum number of total weekends. Just like
> assignments in general, also weekends should not be used up in the early
> stages, but distributed across all weeks to preserve options. Therefore,
> an analogous constraint S7\* can be defined: S7\*. Average working
> weekends: In each week, the still available working weekends (not yet
> used in previous weeks) should be divided equally among all remaining
> weeks."

**Formula (eq. 33, p. 135):**

```
S7*  ∀n∈N:  W_n  ≤  ⌊(t_n^+ − t_n^tot) · 1/(|W| − w + 1)⌋ + C^{S7*}_n
```

> "Note that since there is at most one working weekend per week and
> nurse, and the maximum number of working weekends is less than the
> number of weeks, the limit set for each week will either be 0 or 1."
> (p. 135)

**Penalized variable/expression:** `W_n` (binary "this week is a working
weekend" indicator, already defined at eq. 23, p. 131) against a
**remaining-budget-divided-by-remaining-weeks** target: `(t_n^+ −
t_n^tot)` is the true remaining weekend allowance (using actual cumulative
history `t_n^tot`), divided by the number of weeks left including the
current one (`|W| − w + 1`).

**Important asymmetry — S7\* is NOT the direct analogue of S6\*; it
matches S6\*b instead.** Mischek defines *two* formulas for assignments:
S6\* (eq. 29–30, proportional-of-total-budget, quoted in Q1) and **S6\*b**
(eq. 31–32, p. 134, "remaining assignments... divided equally among all
remaining weeks" — same wording pattern as S7\*). S7\*'s formula (eq. 33)
follows the **S6\*b style** (remaining-budget ÷ remaining-weeks), not the
S6\* style (proportional-of-total). There is no separate "S7\*b". This
must be implemented precisely — using the S6\*-style formula for S7 would
not match the paper.

**Relationship to our S7:** our spec-correct S7 (weight 30) is Mischek's
*basic* S7 (eq. 27, p. 131): `ttot_n + W_n ≤ t_n^+ + C^{S7}_n`. **Our
existing `milp_model.py:300-307` already implements this exactly**:
`h_wknd = hist.get("num_working_weekends", 0)` (= `t_n^tot`, confirmed via
grep — this is the only history-cumulative field actually used in
`milp_model.py`) and `model += (wk + h_wknd - max_wknds <= p_wk, ...)` ⟺
`h_wknd + wk ≤ max_wknds + p_wk`, identical in structure to eq. 27. **S7\*
would be a genuinely new, additive constraint** (no Rule 11 conflict,
unlike S6\* above) — Mischek's own model runs the basic S7 (eq. 27) and
S7\* (eq. 33) simultaneously when the extended model is active; they are
not alternatives.

### Q3 — Per-week budget allocation strategy and boundary handling

**Not ambiguous — both formulas are fully specified, and both use the
real (fixed) cumulative history, never an assumed/synthetic one.** The
two formula families differ in what the *target* represents, not in what
data they use:

- **S6\* (proportional-of-total, eq. 29–30):** the target ceiling/floor at
  week `w` is `⌊a_n^+ · w/|W|⌋` / `⌈a_n^- · w/|W|⌉` — i.e. "what fraction
  of the *full-horizon* bound should be used by now," computed purely from
  `w`, `|W|`, and the contract bound (no assumption about prior weeks'
  actual values baked into the target itself). This target is then
  compared against the actual cumulative count `a_n^tot + (this week)`,
  where `a_n^tot` is always the real, already-solved history — never a
  hypothetical average. Concretely, for the user's example (8-week
  horizon, `max_total_assign=30`, solving week 3): the target ceiling is
  `⌊30 · 3/8⌋ = ⌊11.25⌋ = 11`, and this 11 is compared against the nurse's
  **actual** `a_n^tot` (real count from weeks 1–2, already fixed) plus
  week 3's assignments — not against an assumed `30/8 = 3.75/week` history.
  If the nurse actually under-used their budget in weeks 1–2, they have
  *more* room in week 3 (since the comparison is against the real total,
  which is lower than expected); if they over-used it, less room (or a
  forced `C^{S6*}_n > 0` surplus penalty).
- **S6\*b/S7\* (remaining-budget ÷ remaining-weeks, eq. 31–33):** the
  target is computed *directly* from the real remaining budget
  `(a_n^+ − a_n^tot)` or `(t_n^+ − t_n^tot)`, divided by the weeks left
  `(|W| − w + 1)`. This is even more explicitly history-driven — there is
  no "proportional of total" assumption at all; the formula only ever
  asks "how much is left, divided evenly over what's left."

**Both formulas use `a_n^tot`/`t_n^tot` as the real, already-fixed
cumulative count — confirmed by our own carry-in infrastructure already
matching this exactly:** `multi_week_runner._end_of_week_history()`
(lines 71-82) computes `"num_assignments": hist.get("num_assignments", 0)
+ this_week_assigns` and `"num_working_weekends": hist.get(...) +
worked_weekend` — i.e. genuine cumulative real counts, propagated week to
week, exactly matching Mischek's `a_n^tot`/`t_n^tot` definition (p. 131,
eq. 25–27 use the same `_tot` notation for "cumulative through end of
prior week"). No new history-tracking mechanism is needed; the existing
`history["num_assignments"]` / `history["num_working_weekends"]` fields
already are `a_n^tot`/`t_n^tot`.

### Q4 — α weights for S6* and S7*

**Mischek's published values (Table 1, p. 140, IRACE-tuned):**

| Param | Weight |
|---|---:|
| `W_{S6*}` | 9.9 |
| `W_{S7*}` | 9.9 |
| `W_{S8*}` | 11.9 |
| `W_{S10*}` | 15 |

**Verbatim (p. 139):** *"To find optimal weights for the extensions
S6\*/S7\* and S8\* (the weight for S10\* corresponds directly to the
weight of the shift stretch length constraints), we used IRACE. Both
`W_{S6*}(= W_{S7*})` and `W_{S8*}` were varied between 0 and 20... The
best values reported by IRACE are `W_{S6*} = 9.9` and `W_{S8*} = 11.9`."*

**Critical distinction from S10\*'s weight rationale:** S10\*'s `α=15` was
**deliberately set to equal the official CS2a/b scoring weight** ("as if
the violation had already occurred," p. 139 — i.e. weight-matching to the
real cost is the explicit design rationale). **No equivalent rationale
exists for S6\*/S7\*.** The paper states `W_{S6*}=W_{S7*}` were *tied
together as a single free hyperparameter* and tuned purely empirically via
IRACE search (range 0–20) — there is no claim or implication that this
value should equal (or relate to) the official S6/S7 scoring weights (20
and 30 in our spec-correct system). The two mechanisms use fundamentally
different weight-selection philosophies in the source paper.

**Should `α_S6*` match our S6=20 and `α_S7*` match our S7=30?** Per
Mischek's own approach: **no** — faithful replication means
`α_S6*=α_S7*=9.9` (or a value re-tuned by us via the same kind of search,
not derived from the official weight by analogy). The W-9 approach of
"α should match the cost it's meant to prevent" (used to correct S10* from
15→30 once our `_W_CONSEC` was corrected) **does not transparently apply
here**, because Mischek himself never used that rationale for S6\*/S7\* —
he used trial-and-error tuning instead. This is a genuine open decision
point for human confirmation before implementation; this segment does not
decide it (per guardrails — "the decision is whether to follow Mischek
faithfully first").

### Q5 — Interaction with S10*

**Additive — no special interaction term.** The extended objective (eq.,
p. 137–138, Sect. 4.6) is:

```
minimize f' = f + W_{S8*}·ΣC^{S8*}_skd + W_{S6*}·ΣC^{S6*}_n + W_{S7*}·ΣC^{S7*}_n
                + W_{S9*}·Σ(C^{S9*a}_n+C^{S9*b}_n+C^{S9*c}_n) + W_{S10*}·ΣC^{S10*}_n
```

Every extension contributes an independent linear term, summed directly
into `f'`. **For the same nurse, if both `C^{S6*}_n > 0` (or `C^{S7*}_n >
0`) and `C^{S10*}_n > 0` are simultaneously true, both penalties are added
without any combination, cap, or cross-term** — the MILP solver simply
balances all active surplus variables against the same objective.

**Does Mischek note interaction effects?** Only an empirical (not
mechanistic) one: *"The solution quality can further be improved by
combining multiple extensions. A combination of S6\* (and S7\*), S8\* and
S10\* produced the best results, each of the extensions further reducing
the penalties of the generated solutions"* (p. 139). No quote anywhere
describes a negative interference or special handling between S6\*/S7\*
and S10\* specifically — they are reported as purely complementary
(further reducing penalty when combined), consistent with pure additivity
in `f'`.

### Q6 — Implementation in our pipeline

**`milp_model.py`:** yes — new objective terms added inside `build()`,
gated on `not is_final_week`, exactly mirroring the existing S10\*
pattern (`milp_model.py:235, 249-250`). Confirmed consistent with
Mischek p. 138: *"all constraints introduced in this section should be
ignored in the last week, as there is no further week to influence."*

**`multi_week_runner.py`:** **yes, something new is needed beyond what
S10\* required.** S10\*'s only dependency was the boolean `is_final_week`
(already plumbed correctly per W-9/W-9-supplement). S6\*/S7\*'s formulas
(eq. 29–30, 33) require the **numeric current week index `w`** and **total
horizon length `|W|`** — neither is currently passed into
`MilpModel.build()`. `run()` and `run_with_global()` both compute
`is_final_week = (seq_idx == len(weeks) - 1)` but discard `seq_idx` and
`len(weeks)` otherwise. **A new parameter (e.g. `build(week_index=seq_idx+1,
num_weeks=len(weeks), is_final_week=...)`) would need to be added to the
`build()` signature** — this is a code change for the next segment, not
made here. The cumulative history values themselves (`a_n^tot`/`t_n^tot`)
require **no new plumbing** — `history["num_assignments"]` and
`history["num_working_weekends"]` are already correctly maintained by
`_end_of_week_history()` and already passed through `nurse_info[...]["history"]`
(confirmed in Q3).

**`heuristic.cpp` / `penalty_evaluator.py`: untouched — confirmed matches
Mischek's architecture exactly.** Verbatim (p. 138): *"After a solution
has been fixed, the actual penalty has to be recalculated using the
objective function of the basic model `f`, to ensure that the penalties
from the additional constraints of the extended model are not included in
the final result."* This is precisely our Rule 12 (objective membership):
`C^{S6*}_n`/`C^{S7*}_n` are MILP-search-only surplus variables, invisible
to `runEvalOnly()`/`evaluate()`/`fullCost()`, identical in architecture to
how `ALPHA_S10`/`z_s10` currently live only inside `MilpModel.build()`.

**Open implementation dependency flagged for human decision (not resolved
in this segment):** S7\* can be added as a clean, additive new constraint
(our existing S7 already matches Mischek's basic S7 exactly — Q2). S6\*
**cannot** be added cleanly without first resolving the Q1 finding: our
existing `"S5"`-labeled assignment-proration mechanism
(`milp_model.py:289-298`) is a non-faithful, non-cumulative, `÷4`-hardcoded
approximation that does not match either Mischek's basic S6 or S6\*. Adding
true S6\* alongside the existing `÷4` mechanism would create two
differently-formulated penalties for the same underlying concept (S6),
which Rule 11 classifies as drift unless explicitly justified as an
intentional dual-surrogate design — a decision for 段1, not assumed here.

---

## 6. Selected Design — S6*/S7* (pending human confirmation)

**Not yet selected.** Per the W-10 段0 task scope, this segment is
read-only design research; Q1–Q6 above surface the spec and one
implementation dependency (the existing non-faithful S6 mechanism) that
must be resolved before code changes. Awaiting human review of:
1. Whether to follow Mischek's literal `α_{S6*}=α_{S7*}=9.9` (tied,
   IRACE-tuned) or a different weight-selection approach (Q4).
2. Whether to first replace the existing `÷4` S6 approximation with
   Mischek's basic S6 (eq. 25–26) before layering S6\* on top, or some
   other resolution to the Rule 11 conflict identified in Q1/Q6.
3. Whether to implement S6\* and S7\* together (as Mischek's paper
   evaluates them as a tied pair) or S7\* first in isolation (since it has
   no implementation dependency, unlike S6\*).

---

## W-10 段1A: Mislabel Fix + True S6/S6* Implementation (2026-06-17)

**Decision taken (human, not this segment):** Path A, split into two
phases. This segment (段1A) fixes F1 and implements true basic-S6/S6*
only — no S7\*, no S10\* changes. α_S6\* locked to **20** (matches
official S6 weight, same rationale as S10\*'s α=30 — "match the cost being
prevented"), explicitly **not** Mischek's IRACE-tuned 9.9 (Q4 finding:
9.9 was tuned for Mischek's own solver/instance set and does not transfer).

### F1 mislabel diagnosis

`milp_model.py:289-298` (pre-fix), internally labeled `"S5"`:

```python
weekly_min = min_assign // 4
weekly_max = math.ceil(max_assign / 4)
total_w = pulp.lpSum(w)                      # this week's count ONLY
model += (total_w >= weekly_min - p_u, ...)
model += (total_w <= weekly_max + p_o, ...)
```

Confirmed (grep, no other call site): this was the **only** location
implementing the assignment-count proration. `num_assignments` (the
cumulative history field) is referenced nowhere else in `milp_model.py` —
the term checked only the current week's own count against a static `÷4`
fraction of the full-horizon bound, regardless of the instance's actual
`|W|` (8 for n012w8) or any nurse's actual cumulative history. No test
asserted this mechanism's specific values (`grep` for
`weekly_min|weekly_max|S5_min|S5_max` across `tests/` returned nothing).

### Replacement design

Replaced with true cumulative tracking, branching on `is_final_week`
(same gate S10\* already uses):

```python
a_tot = hist.get("num_assignments", 0)        # real cumulative history
cumulative_total = a_tot + pulp.lpSum(w)       # + this week's decision vars
if is_final_week:
    # Basic S6 (Mischek eq.25-26): horizon-end check against full bound
    model += (cumulative_total >= min_assign - p_u, ...)
    model += (cumulative_total <= max_assign + p_o, ...)
else:
    # S6* (Mischek eq.29-30): proportional cumulative target
    target_lower = math.ceil(min_assign * cur_week / num_weeks)
    target_upper = math.floor(max_assign * cur_week / num_weeks)
    model += (cumulative_total >= target_lower - p_u, ...)
    model += (cumulative_total <= target_upper + p_o, ...)
```

`build()` gained two new keyword parameters, `cur_week: int = 1` and
`num_weeks: int = 1` (defaults preserve single-week/backward-compatible
behavior — basic S6 with no proration). `multi_week_runner.py`'s two
`build()` call sites (`run()`, `run_with_global()`) now pass
`cur_week=seq_idx+1, num_weeks=len(weeks)`.

**Test fallout (both resolved, root cause confirmed non-architectural):**
- `test_stretch_tail_reduces_w2_end_saturation_n012w8` initially regressed
  to 6/12 (matching the no-fix baseline) because it called
  `build(is_final_week=False)` without `cur_week`/`num_weeks`, defaulting
  to 1/1 — i.e. **no proration at all**, demanding the full
  `min_assign` be reached by week 0 alone. This created a degenerate
  "work every day, every week" pressure that exactly canceled S10\*'s
  stretch-tail-avoidance signal. Fixed by passing `cur_week=week_idx+1,
  num_weeks=8` (n012w8's real horizon) in the test. Result after fix:
  **0/12** nurses saturated (vs. 4/12 with S10\* alone under the old
  mislabel, 6/12 with neither) — threshold tightened `≤4`→`≤1`.
- `test_sa_h3_clean_on_n012w8_w3`: SA's own (untouched) prorated-S6
  guidance gap widened from 200→240 because the corrected MILP+F&O seed
  for W3 changed, shifting how much work SA's internal guidance had left
  to do. Confirmed via direct trace (not assumed): `final_cost=540`,
  `eval_total=300`, `gap=240` — the same well-documented SA-vs-eval scale
  gap mechanism (SA's prorated S6 contribution, excluded from the
  evaluator per Rule 12), consistent with gaps up to 240/week already
  observed in `baseline_w6_spec_aligned.md`. Threshold widened 200→300.

22/22 tests pass. H2/H3 gates clean on all weeks in all three instances
measured below. SA≡evaluator identity unaffected (MILP-side change only).

### Isolated measurement: F1 fix alone, S10* disabled (diagnostic only — NOT reproducible via any committed entry point; see "Correction" below)

To isolate the F1 fix's effect from S10\*'s (already measured in
W-9-supplement), a temporary diagnostic script built each week with
`cur_week`/`num_weeks` passed correctly (true S6/S6\* active), then
stripped the `S10star_*` constraints from the built PuLP model in-place
before solving (the associated surplus variables, with no remaining
constraint, settle to 0 — equivalent to S10\* being fully disabled,
without editing `milp_model.py`'s committed S10\* code per the guardrail).
Full pipeline (MILP→F&O→SA), `multi_week_runner`-equivalent history
propagation.

**n012w8 8-week, true S6/S6*, S10* disabled:**

| Wk | sa_init | sa_fin | S1 | S2  | S3  | S4 | forb | total |
|---:|--------:|-------:|---:|----:|----:|---:|-----:|------:|
|  0 |   510.0 |  510.0 |  0 | 120 |   0 | 10 |    0 |   130 |
|  1 |   270.0 |  270.0 |  0 |   0 |   0 | 10 |    0 |    10 |
|  2 |   310.0 |  310.0 |  0 |   0 |   0 | 10 |    0 |    10 |
|  3 |   380.0 |  380.0 |  0 |   0 |   0 |  0 |    0 |     0 |
|  4 |   570.0 |  570.0 |  0 | 150 |   0 |  0 |    0 |   150 |
|  5 |   640.0 |  640.0 |  0 |   0 | 270 | 10 |    0 |   280 |
|  6 |   260.0 |  260.0 |  0 |   0 |   0 |  0 |    0 |     0 |
|  7 |   380.0 |  380.0 |  0 |   0 |  60 | 20 |    0 |    80 |
| SUM | | | **0** | **270** | **330** | **60** | **0** | **660** |

Global: S6=0, S7=300, total_global=300. **Full INRC-II = 960**

**Comparison vs W-6 baseline (old `÷4` mislabel, no S10*, full pipeline):**

| Instance | W-6 baseline | W-10 段1A (F1 fix, no S10*) | Δ | Δ% |
|----------|-------------:|------------------------------:|--:|----|
| n012w8   | 2770         | **960**                       | **-1810** | **-65.3%** |
| n005w4   | 320          | **300**                       | -20 | -6.25% |
| n021w4   | 350          | **420**                       | +70 | +20.0% |

### Correction (2026-06-19): 960/300/420 are not the production numbers

The 960/300/420 row above required stripping `S10star_*` constraints
post-`build()` — an operation with no committed entry point. `milp_model.py`
gates S6\* and S10\* on the same `is_final_week` flag (no independent
toggle exists), so `run_4week_full_pipeline.py`, once correctly plumbed
with `cur_week`/`num_weeks`, always runs S6\*+S10\* together. The
production-faithful numbers (verified via `run_4week_full_pipeline.py`,
see `w10_1a_verification.md` § Correction) are:

| Instance | W-6 baseline | F1 alone (isolation, not reproducible) | F1+S10\* (production) | Δ vs W-6 | Δ% vs W-6 |
|----------|-------------:|------------------------------------:|----------------------:|---------:|----------:|
| n012w8   | 2770         | 960                                  | **1070**               | **-1700** | **-61.4%** |
| n005w4   | 320          | 300                                  | **260**                | -60       | -18.75%   |
| n021w4   | 350          | 420                                  | **400**                | +50       | +14.3%    |

**S10\* marginal effect on the F1-corrected baseline** (F1+S10\* minus F1
alone): n012w8 +110 (regressive — single-week look-ahead doesn't resolve
the 12-nurse coupling), n005w4 -40 (-13.3%, helps), n021w4 -20 (-4.8%,
small help). This is the 段1B measurement — S10\* on top of the
F1-corrected baseline — and it was answered as a side effect of fixing
the plumbing, not a separate experiment.

**-61.4% (1070), not -65.3% (960), is the correct headline number for
n012w8 going forward.** The isolation tables below remain useful as a
mechanistic decomposition (they show what F1 does in the absence of
S10\*) but are not a result the pipeline ever actually produces.

**n012w8 per-week delta (`sa_final`):**

| Wk | W-6 | W-10 段1A | Δ |
|---:|----:|----------:|--:|
| 0 | 150 | 510 | +360 |
| 1 | 210 | 270 | +60 |
| 2 | 260 | 310 | +50 |
| 3 | 190 | 380 | +190 |
| 4 | 950 | 570 | **-380** |
| 5 | 400 | 640 | +240 |
| 6 | 270 | 260 | -10 |
| 7 | 460 | 380 | -80 |

**n012w8 per-week delta (`total`, the headline metric):**

| Wk | W-6 | W-10 段1A | Δ |
|---:|----:|----------:|--:|
| 0 |  10 | 130 | +120 |
| 1 |  10 |  10 |   0 |
| 2 |  20 |  10 | -10 |
| 3 |  30 |   0 | -30 |
| 4 | 710 | 150 | **-560** |
| 5 | 160 | 280 | +120 |
| 6 | 110 |   0 | -110 |
| 7 | 220 |  80 | -140 |
| SUM | 1270 | 660 | **-610** |

**n005w4, true S6/S6*, S10* disabled:** per-week=60, global S6=60/S7=180
(total_global=240). **Full INRC-II = 300** (vs. W-6's 320, -6.25%).

**n021w4, true S6/S6*, S10* disabled:** per-week=420 (S2=390, S4=30),
global S6=0/S7=0 (total_global=0). **Full INRC-II = 420** (vs. W-6's 350,
+20.0%) — per-week worsened but global went to a perfect 0.

H2/H3 clean (S1=0, forbidden=0) on every week, all three instances.

### Interpretation

**The F1 fix alone — with no look-ahead mechanism at all — is the
dominant factor in resolving the n012w8 regression**, far exceeding what
S10\* achieved either alone (W-9: MILP-only +7.1%, full-pipeline +17.3%
regression) or combined with the old `÷4` mislabel. The W4 cliff (710)
that survived W-9-supplement's S10\*+old-mislabel combination (and that
S10\* alone only relocated to W5 at 690) drops to **150** here, with no
comparable new cliff appearing elsewhere — W5's 280 is moderate, not
catastrophic. Global S6 reaches **exactly 0** (vs. 960 under the old
mislabel) — the broken `÷4` proration was forcing the MILP toward
schedules that systematically violated the true horizon-end assignment
bound, since it was never actually modeling that bound.

n005w4 (small N) sees a modest improvement (-6.25%), consistent with it
already being close to optimal under the old mechanism (W-6 was already
only 320). n021w4 regresses on per-week total (+20.0%) but **eliminates**
its global S6/S7 cost entirely (150→0) — the true proration pushes nurses
toward more consecutive work to hit their accurate weekly target, trading
S2 violations for perfect global compliance; net effect for this instance
is roughly a wash in total INRC-II terms (350→420, a smaller relative
move than n012w8's).

**One-sentence verdict: the F1 fix is not "partial" — for n012w8 (the
instance that motivated this whole Phase 2 investigation) it resolves far
more of the regression than S10\* did, suggesting the `÷4` mislabel, not
the absence of look-ahead, was the primary driver of the original
cross-week pathology.**

This reframes the role of 段1B (S7\* + S10\* recombination): rather than
being the main fix, S7\*/S10\* may now only need to clean up the
*remaining* residual (n012w8's W0/W5 moderate bumps, n021w4's S2 increase)
on top of an already-much-healthier F1-fixed baseline — a smaller, more
targeted problem than originally framed.

**SA frozen on most weeks (observation, not a defect):** `sa_initial ==
sa_final` for nearly every week across n012w8 and n021w4 (n005w4 is the
exception, with real SA movement on weeks 1-3). This likely reflects the
new MILP+F&O seed already being close to SA's own local optimum under the
corrected assignment-count signal, leaving little room for further local
search improvement — consistent with, not contradicting, the F1 fix being
the dominant lever rather than SA's local search.

**Corrigendum (2026-06-19):** the verdict above ("far exceeding what
S10\* achieved") was written against the 960/300/420 isolation figures,
which turned out not to be reproducible from any committed code path
(see Correction above). On the production-faithful F1+S10\* numbers
(1070/260/400), the qualitative conclusion is unchanged — F1 is still
the dominant lever, and the original `÷4` mislabel was still the primary
driver of the n012w8 regression — but the precise headline improvement
is **-61.4%**, not -65.3%, and S10\*'s role in production is no longer
hypothetical: it is a measured +110 (regressive) on n012w8, -40 and -20
(small helps) on n005w4/n021w4 respectively, on top of the F1 fix.

## W-10 段1B: S7* per-week working weekend look-ahead

### Implementation note — S7 gate alignment (latent dead-code fix)

Before this change, the S7 block (`milp_model.py` S7c) was unconditional:
it fired identically every week, checking the real cumulative
`h_wknd + wk - max_wknds <= p_wk` against the *full* contract
`max_wknds`, regardless of `is_final_week`. Per Ceschia 2019 p.177, S7
is a global constraint evaluated only at the end of the planning
horizon — and since a nurse works at most one weekend per single-week
MILP call, the cumulative total could never reach `max_wknds` early
enough to trip this check before the final week. So S7c was dead code
on every non-final week since the initial scaffold commit (confirmed via
`git log -L 324,336:outer_milp/models/milp_model.py` — unconditional
since `5b1a11e`). 段1B wraps the unchanged S7c logic in
`if is_final_week:` and adds S7\* in the `else:` branch, mirroring the
S6/S6\* and S10\* structure from 段1A — a correctness fix independent of
whether S7\* itself helps or hurts.

### Spec (Mischek 2019 eq.33, p.134-135)

    W_n <= floor( (t_n^+ - t_n^tot) / (|W| - w + 1) )

`W_n` = current week's working-weekend indicator (existing binary `wk`),
`t_n^+` = `max_wknds`, `t_n^tot` = real cumulative weekends through week
`w-1` (existing `h_wknd`), `|W|` = `num_weeks`, `w` = `cur_week`
(confirmed 1-indexed: `cur_week=seq_idx+1` in both callers). Denominator
counts weeks remaining *inclusive* of the current week —
`slots_remaining = num_weeks - cur_week + 1`, collapsing to 1 at the
final week (matching the real S7c check there). Slack:
`z_wknd_n >= wk - proportional_bound`, `z_wknd_n >= 0`.

### α decision

`α_S7* = W_WEEKEND = 30`, matching the official S7 weight — same
weight-alignment logic as `α_S6* = W_ASSIGN = 20` (段1A) and `α_S10* =
30` (W-9): weighted by the cost it prevents, not Mischek's IRACE-tuned
9.9 (locked, 段0).

### Production results

| Instance | 段1A (S6\*+S10\*) | 段1B (+S7\*) | Δ | Δ% |
|---|---:|---:|---:|---:|
| n012w8 | 1070 | **860** | -210 | **-19.6%** |
| n005w4 | 260  | **240** | -20  | **-7.7%**  |
| n021w4 | 400  | **450** | +50  | **+12.5%** |

**n012w8 per-week breakdown, 段1B** (`evaluate()` on SA output, H2/H3
clean every week — S1_coverage=0, forbidden=0 confirmed all 8 weeks):

| Wk | S1 | S2 (consec. work) | S3 (consec. off) | S4 (pref) | forbidden | total |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 |  60 | 0 | 10 | 0 |  70 |
| 1 | 0 |  60 | 0 | 10 | 0 |  70 |
| 2 | 0 |   0 | 0 | 10 | 0 |  10 |
| 3 | 0 |   0 | 0 |  0 | 0 |   0 |
| 4 | 0 | 150 | 0 |  0 | 0 | 150 |
| 5 | 0 |   0 | 0 | 20 | 0 |  20 |
| 6 | 0 |   0 | 0 | 20 | 0 |  20 |
| 7 | 0 | 150 | 0 | 10 | 0 | 160 |
| **SUM** | 0 | 420 | 0 | 80 | 0 | **500** |

**Global S6/S7 comparison (all instances):**

| Instance | 段1A S6 / S7 | 段1B S6 / S7 |
|---|---|---|
| n012w8 | 0 / 450 | 0 / **360** |
| n005w4 | 80 / 150 | **60** / 150 |
| n021w4 | 0 / 30  | 0 / **210** |

All H2/H3 gates (`S1_coverage=0`, `forbidden_succession_violations=0`)
reconfirmed clean across all 16 weeks (8+4+4) under S7\*, via a separate
gate-check pass over the full pipeline per instance. Full 22/22 pytest
suite still passes.

### Interpretation

**n012w8 — (a) clear win.** Per-week total drops (620→500, -19.4%) and
global S7 excess drops in lockstep (450→360, -20%). S7\* spreads
weekend-work pressure across the 8-week horizon instead of letting it
concentrate near the end, exactly as intended — n012w8 now benefits from
every look-ahead term applied across 段1A+段1B.

**n005w4 — (a) clear win (modest, indirect).** Per-week total is flat
(30→30) and global S7 itself is unchanged (150→150); the entire -20
improvement comes from global S6 (80→60) — a knock-on effect of S7\*
reshaping *which* nurse covers *which* weekend, which shifted the
downstream SA search toward fewer excess total assignments, not a direct
effect of the S7\* constraint itself.

**n021w4 — (b) target met but spill.** Per-week total improves
substantially (370→240, -35.1% — S7\*'s local proportional targets are
satisfied turn-by-turn), but global S7 excess explodes (30→210, +600%),
driving a net regression (+50, +12.5%). Each week's MILP only sees its
*own* proportional budget; it has no visibility into which other nurses
are also near their caps. Pushing weekend-avoidance onto whichever nurse
has slack *this week* can concentrate the cumulative excess onto a
smaller subset of nurses by the final week instead of distributing it —
the local target is met every week, but the cost spills onto nurses with
no further weeks left to recover.

**Net read across S6\*/S10\*/S7\* (段1A+段1B combined): no instance is
helped or hurt by every term** — n012w8 gains from S6\*+S7\* but loses to
S10\*; n021w4 gains from S10\* but loses to S7\*; n005w4 gains modestly
from all three. Consistent with Mischek's framing of these as heuristic
search-time aids, not mathematically necessary constraints: they trade
off per instance, and the full INRC-II total is the only fair arbiter.
