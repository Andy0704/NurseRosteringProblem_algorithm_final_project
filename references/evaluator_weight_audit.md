# INRC-II Official Weights vs Implementation Audit

**Date:** 2026-06-16 (initial); spec column verified 2026-06-17  
**Scope:** penalty_evaluator.py, heuristic.cpp, milp_model.py  
**Trigger:** Q3 verification in S10* segment revealed `_W_CONSEC=15` may underweight
CS2c/d (consecutive working days, official weight 30 per Ceschia 2019, Section 2.5)

---

## Spec source verification (W-1, 2026-06-17)

**Weight authority: Ceschia et al. 2019, Section 2.5.1 (Sec 2.5.2 for S6/S7),
verified 2026-06-17 against PDF pages 6–7 (journal pp. 176–177) using pdfplumber.
Earlier intermediate citation via `romer2019_dag_milp.md` superseded by direct PDF
quotes below. All weights in that intermediate reference were correct.**

### Direct PDF verbatim excerpts (Ceschia 2019, Section 2.5.1, p. 176)

> **S1. Insufficient staffing for optimal coverage (30):** The number of nurses for
> each shift for each skill must be equal to the optimal requirement. Each missing
> nurse is penalised according to the weight provided.

> **S2. Consecutive assignments (15/30):** A minimum and maximum number of
> consecutive assignments to the same shift type should be respected. Each extra or
> missing day is multiplied by the corresponding weight. **The weight for consecutive
> shift of the same type is 15.**
> Similarly, a minimum and maximum number of consecutive assignments to any working
> shift should be respected. **For consecutive working days of any shift the weight
> is 30.** In both cases, the evaluation involves also the border data.

> **S3. Consecutive days off (30):** Minimum and maximum number of consecutive days
> off should be respected. Their evaluation involves also the border data. Each extra
> or missing day is multiplied by the corresponding weight.

> **S4. Preferences (10):** Each assignment to an undesired shift is penalised by the
> corresponding weight.

> **S5. Complete weekend (30):** Every nurse that has the complete weekend value set
> to true, must work both weekend days or neither. If she/he works only one of the two
> days Sat and Sun, this is penalised by the corresponding weight.

### Section 2.5.2 (p. 177) — constraints spanning the planning horizon

> **S6. Total assignments (20):** For each nurse the total number of assignments
> (working days) must be within the limits (minimum and maximum) enforced by her/his
> contract. The difference (in either direction), multiplied by the constraint's
> weight, is added to the objective function.

> **S7. Total working weekends (30):** For each nurse the number of working weekends
> must be less than or equal to the maximum. The number of worked weekends in excess
> is added to the objective function multiplied by the weight. **A weekend is
> considered "working" if at least one of the two days (Sat and Sun) is busy for
> the nurse.**

> [p. 177, same section] "Obviously, the solver should take constraints S6 and S7
> into account in each single stage. However, their violation values have a decreasing
> degree of uncertainty going from one week to the following one, and only in the last
> week can they be evaluated exactly."

### Confirmed spec for the four "missing" components

**S2 CS2a/b (same-shift-type, weight 15):**
- Constraint object: shift type's `min_consecutive` / `max_consecutive` fields in
  the scenario file (Ceschia 2019, p. 174, Sect. 2.1: *"For each shift type… the
  minimum and maximum number of consecutive assignments of that specific type"*).
- Border data required: *"number of consecutive worked shifts of the same type"*
  (p. 175, Sect. 2.3, border data).
- Our `_end_of_week_history` sets `num_consecutive_shift_assignments: 0` always —
  the same-shift border data is missing from the carry-forward, independent of the
  weight issue.

**S5 (complete weekend, weight 30):**
- Contract flag: `completeWeekends = true/false` (Boolean, p. 173, Sect. 2.1).
- Violation condition: exactly one of {Sat, Sun} is a working day.
- Penalty: 1 violation per nurse per week = weight 30 per incomplete weekend occurrence.
- n012w8 has `completeWeekends=1` for both FullTime and PartTime contracts.

**S7 (total working weekends, weight 30):**
- Constraint: max-only (`maximumNumberOfWorkingWeekends`, no minimum).
- "Working" weekend definition: at least one of Sat/Sun worked (p. 177).
- Evaluated globally at end of horizon; charged incrementally per week by convention.
- Our MILP uses the at-least-one-of-{Sat,Sun} definition correctly (`wk >= w[SAT]`,
  `wk >= w[SUN]`, `milp_model.py:299-300`). SA/evaluator do not implement S7.

**S6 (total assignments, weight 20):**
- Constraint: both min and max (p. 177: *"within the limits (minimum and maximum)"*).
- Evaluated at end of horizon; solver responsible for modeling per-week prorating.
- Official weight 20; our MILP uses W_ASSIGN=15 (25% low), SA uses TOTAL_ASSIGN_W=10
  (50% low). Both are wrong.

### Verdict on intermediate reference

All seven weights in `romer2019_dag_milp.md` lines 164–181 match the PDF exactly.
No weight differs from what that reference reported. The "via romer2019" citation in
the initial audit is superseded by the direct PDF citations above but was not wrong.

---

## S-component weight table

| S-component | Spec weight (Ceschia 2019, Sec 2.5) | evaluator.py | heuristic.cpp | milp_model.py | Verdict |
|---|---|---|---|---|---|
| **S1** — insufficient staffing | 30 | `_W_COVERAGE=30` (line 22) | `COVER_WEIGHT=30` (line 16) | `W_COVERAGE=30` (line 79) | ✅ |
| **S2 CS2a/b** — same-shift-type consec | 15 | MISSING | MISSING (removed, line 395) | MISSING | ⚠️ scope |
| **S2 CS2c/d** — any-shift consec work days | **30** | `_W_CONSEC=15` (line 23) | `CONSEC_WEIGHT=15` (line 17) | `W_CONSEC=15` (line 80) | ❌ all 3 underweight 2× |
| **S3** — consec days off | **30** | `_W_CONSEC=15` (line 23) | `CONSEC_WEIGHT=15` (line 17) | `W_OFF=30` (line 81) | ❌ evaluator + SA wrong; MILP correct |
| **S4** — nurse shift preferences | 10 | `_W_PREF=10` (line 24) | `SHIFT_OFF_REQ_W=10` (line 20) | `W_PREF=10` (line 85) | ✅ |
| **S5** — complete weekend | 30 | MISSING | MISSING | `W_COMPLETE=30` (line 84) | ⚠️ MILP only |
| **S6** — total assignments (horizon) | 20 | MISSING | `TOTAL_ASSIGN_W=10` (line 19) | `W_ASSIGN=15` (line 82) | ❌ 3-way divergence |
| **S7** — total working weekends | 30 | MISSING | MISSING | `W_WEEKEND=30` (line 83) | ⚠️ MILP only |
| **H3** — forbidden successions | hard | count only | M_FORBID dynamic gate | H3 hard constraint | ✅ |

---

## Per-row analysis

### S1 — Coverage (weight 30)

All three layers use 30.

- `penalty_evaluator._compute_s1` (`penalty_evaluator.py:38–75`): `_W_COVERAGE = 30`
- `heuristic.cpp:coverageCostDay` (`heuristic.cpp:184–208`): `COVER_WEIGHT = 30`
- `milp_model.py:build()` (`milp_model.py:79,161`): `W_COVERAGE = 30`, applied to
  `p_H2_{sk}_{d}_{s}` slack variables

**Verdict: ✅ All match spec.**

---

### S2 CS2a/b — Same-shift-type consecutive (weight 15)

**Officially scored at weight 15 per Ceschia 2019, Sec 2.5.**

Violations: a nurse works fewer than `MinConsecutiveShiftDays` or more than
`MaxConsecutiveShiftDays` of the same shift type in a row. The n012w8 shift mapping
shows e.g. Night: `min_consecutive=4, max_consecutive=5` (parsed and stored in
`ShiftDef.min_consecutive / max_consecutive`, `heuristic.cpp:94–96` and
`shift_mapping[i].min_consecutive` in the JSON).

**Status in all three layers: MISSING.**

- `penalty_evaluator._compute_s2_s3` (`penalty_evaluator.py:78–119`): checks
  `minimumNumberOfConsecutiveWorkingDays` / `maximumNumberOfConsecutiveWorkingDays` only
  (contract-level any-shift constraint). No `min_consecutive` / `max_consecutive` per
  shift type is consulted.
- `heuristic.cpp:nurseCostFull` (`heuristic.cpp:312–411`): explicit removal comment at
  line 395: `"// Consecutive same-shift type — Change C: removed (no equivalent in
  evaluator or MILP)."` The `ShiftDef.min_consecutive` / `max_consecutive` fields are
  parsed but never used in cost computation.
- `milp_model.py:build()` (`milp_model.py:39–332`): no loop over `shift_mapping` for
  per-shift-type consecutive constraints. The `min_consecutive` / `max_consecutive`
  fields in the shift_mapping JSON are not referenced anywhere in `build()`.

**Verdict: ⚠️ Deliberate scope reduction.** The SA comment ("no equivalent in evaluator
or MILP") confirms this was a known, intentional omission. However it is not documented
as a formal scope decision with impact analysis. The Q3 trace (`W3 S2 trace`,
`lookahead_design_notes.md §3`) shows that Nurses 2/4/7 in n012w8 W3 have simultaneous
CS2a/b violations (Night: run=10 > max=5 across W2→W3 boundary) that all three layers
silently miss. Under spec-correct scoring, these 3 nurses × 5 excess days × 15 = 225
additional penalty points would appear in the W3 score — not currently reported.

---

### S2 CS2c/d — Any-shift consecutive working days (weight **30**)

**Officially scored at weight 30 per Ceschia 2019, Sec 2.5.**

Violations: a nurse works fewer than `minimumNumberOfConsecutiveWorkingDays` or more
than `maximumNumberOfConsecutiveWorkingDays` (any shift type) in a row.

**Status: All three layers implement this constraint but at weight 15, not 30.**

- `penalty_evaluator._compute_s2_s3` (`penalty_evaluator.py:87–119`): uses
  `_W_CONSEC = 15` (line 23). Checks `min_cw` / `max_cw` from contracts.
  Reported as `S2_consecutive_work` in the `evaluate()` return dict.
- `heuristic.cpp:nurseCostFull` (`heuristic.cpp:333–356`): uses `CONSEC_WEIGHT = 15`
  (line 17). Checks `contract.min_consec_work` / `contract.max_consec_work`.
  Stored in `nc.s2_consec_work`, included in `nc.total`.
- `milp_model.py:build()` (`milp_model.py:80,191–228`): uses `W_CONSEC = 15` (line 80)
  for both the S1 (max-consec) window-sum constraints (lines 191–214) and the S2
  (min-consec) run-start constraints (lines 220–228). Comment at line 78 attributes
  this to "Ceschia et al. 2019" — **this attribution is incorrect for CS2c/d**
  (the spec weight is 30, not 15).

**Identity implication:** evaluator and SA agree (both use 15 for CS2c/d), so the
800-schedule identity test (`test_sa_identity_800`) passes. However, BOTH are wrong
vs. spec. The identity proves same-source, not spec-correctness.

**Impact on all reported measurements:**
- Every `S2_consecutive_work` number in `lookahead_design_notes.md` §1 (n012w8
  weeks 0–7 tables) is understated by exactly 2×.
- Post-H3-fix SUM=410 decomposition: S2=300, S3=30, S4=80.  
  Spec-correct S2 weight doubles the S2 contribution: 300 → 600, SUM → 710.
- The S10* attempt-1 measurement (SUM=525) and attempt-2 (SUM=520) are similarly
  understated: spec-correct SUM ≈ 850 (attempt-1), 840 (attempt-2).
- S10*'s α=15 determination in `lookahead_design_notes.md §3` was justified as "match
  our evaluator's actual cost = 15 per violation-day." If S2 weight is corrected to 30,
  the evaluator's actual cost becomes 30 and α=30 is then the correct "as if the
  violation had already occurred" value.

**Verdict: ❌ SPEC BUG in all three layers.** All underweight by 2×. Evaluator and SA
agree (identity preserved), MILP also agrees — all three are consistently wrong together.
Correcting requires updating `_W_CONSEC` in evaluator, `CONSEC_WEIGHT` in SA, and
`W_CONSEC` in MILP from 15 to 30 for the CS2c/d computation path.

---

### S3 — Consecutive days off (weight **30**)

**Officially scored at weight 30 per Ceschia 2019, Sec 2.5.**

**Status: MILP correct at 30; evaluator and SA both use 15 (wrong).**

- `penalty_evaluator._compute_s2_s3` (`penalty_evaluator.py:109–118`): the same
  `_W_CONSEC = 15` constant is reused for S3 (off-run violations). No separate
  `_W_OFF` constant exists in the evaluator.
- `heuristic.cpp:nurseCostFull` (`heuristic.cpp:359–381`): uses `CONSEC_WEIGHT = 15`
  for `nc.s3_consec_off`. Same constant as S2.
- `milp_model.py:build()` (`milp_model.py:81,249–283`): uses **`W_OFF = 30`** (line 81)
  for S3 (max-consec-off, `p_mo_{n}_{d}`) and S4 (min-consec-off, `p_mino_{n}_{d}_{k}`).

**This is the only S-component where the MILP is correct and both evaluator and SA are wrong.**

**Structural consequence:** The MILP optimizes with W_OFF=30 for consecutive-off
violations, but the `penalty_evaluator.evaluate()` reported score uses _W_CONSEC=15.
For schedules with non-trivial S3 violations, the MILP search objective and the
reported score give different relative importance to S3 vs S2. This is a Rule 12
structural divergence: the penalty term weight is inconsistent between the layer that
optimizes it (MILP, W_OFF=30) and the layer that reports it (evaluator, _W_CONSEC=15).

**SA vs evaluator identity:** The SA identity test (`test_sa_identity_800`) passes
because BOTH SA (CONSEC_WEIGHT=15) and the evaluator (_W_CONSEC=15) use 15 for S3.
The identity proves same-source between SA and evaluator, but both deviate from spec
AND from the MILP for S3. A schedule with S3 violations would produce identical SA
and evaluator totals (correct identity), but the MILP's search objective assigned
2× more weight to that violation.

**Impact on reported measurements:**
- n012w8 post-H3-fix SUM=410 includes S3=30 (evaluator). Under spec-correct S3 weight:
  S3 contribution = 60, SUM → 440.
- n012w8 pre-fix (first table in §1): S3=150 → spec-correct S3 = 300, SUM → 635.
- S3 was 0 in most weeks of the post-H3-fix measurement, limiting impact there.

**Verdict: ❌ evaluator + SA underweight S3 by 2×; MILP correct.**  
The S3 deviation ALSO breaks evaluator-MILP consistency, which is separate from the
SA-evaluator identity (which remains intact).

---

### S4 — Shift preferences (weight 10)

All three layers use 10.

- `penalty_evaluator._compute_s4` (`penalty_evaluator.py:122–144`): `_W_PREF = 10`
- `heuristic.cpp:nurseCostFull` (`heuristic.cpp:398–408`): `SHIFT_OFF_REQ_W = 10`
- `milp_model.py:build()` (`milp_model.py:85,316–329`): `W_PREF = 10`

**Verdict: ✅ All match spec.**

---

### S5 — Complete weekend (weight 30)

**Officially scored at weight 30 per Ceschia 2019, Sec 2.5.**

Violation: a nurse works exactly one of Saturday/Sunday (incomplete weekend) when the
contract requires `completeWeekends = 1`.

- `penalty_evaluator.py`: MISSING. No complete-weekend check in `evaluate()`.
- `heuristic.cpp:nurseCostFull`: MISSING. Not present in `nc.total`.
- `milp_model.py:build()` (`milp_model.py:84,304–308`): implemented as `W_COMPLETE=30`,
  added to `penalty_terms` when `complete_wknd=1`:
  ```python
  model += (w[SAT] - w[SUN] <= p_cpl, ...)
  model += (w[SUN] - w[SAT] <= p_cpl, ...)
  ```

**Verdict: ⚠️ SCOPE CHOICE — MILP implements S5; evaluator and SA do not.**  
This is analogous to the S10* design (Rule 12): S5 enters the MILP search objective
but is not reported in the evaluated score. Unlike S10*, this is not documented as an
explicit scope choice with Rule 12 justification. The MILP's reported penalty from
`model.solve()` includes W_COMPLETE terms, but `penalty_evaluator.evaluate()` on the
same schedule does not — so MILP's `obj_val` and evaluator's `total` DIFFER whenever
S5 violations exist. Impact: n012w8 instances have `completeWeekends=1` for all nurses,
so S5 violations are possible whenever a nurse works exactly one weekend day.

---

### S6 — Total assignments over planning horizon (weight **20**)

**Officially scored at weight 20 per Ceschia 2019, Sec 2.5.**

Violation: total working days assigned over the 4-week horizon falls outside
`[minimumNumberOfAssignments, maximumNumberOfAssignments]`.

**Three-way divergence: spec=20, MILP=15, SA=10, evaluator=missing.**

- `penalty_evaluator.py`: MISSING. Not in `evaluate()` return dict.
- `heuristic.cpp:nurseCostFull` (`heuristic.cpp:383–393`): implements S6 via
  `TOTAL_ASSIGN_W = 10` (line 19), **prorated weekly** (`weekly_min = min_assign / 4`,
  `weekly_max = ceil(max_assign / 4)`). Added to `nc.total`.
- `milp_model.py:build()` (`milp_model.py:82,286–294`): implements S6 via
  `W_ASSIGN = 15` (line 82), also prorated weekly (same formula).

**Critical structural issue:** `heuristic.cpp:nurseCostFull.total` includes S6 at
weight 10, but `heuristic.cpp:runEvalOnly` rebuilds `total = s1 + s2 + s3 + s4`
(line 789) from named components only, which do NOT include the assignment-count
component. So:

- `runEvalOnly.total` = S1 + S2 + S3 + S4 (no S6)
- `fullCost.total` = S1 + S2 + S3 + S4 + **S6** (includes assignment count)

The SA search (`fullCost`) includes S6, but the reported score (`runEvalOnly` and
`penalty_evaluator.evaluate()`) excludes it. This means the SA search objective and
the reported score DIVERGE whenever assignment bounds are violated weekly.

**Why identity test passes:** `test_sa_identity_800` uses n005w4 schedules prorated
to 1 week. For n005w4, `minimumNumberOfAssignments=30` → `weekly_min=7`,
`maximumNumberOfAssignments=44` → `weekly_max=11`. A 7-day schedule cannot have more
than 7 working days, so `weekly_max` is never exceeded. The minimum (7) can only be
violated if some nurses have fewer than 7 working days, but the randomized test
schedules likely keep all nurses near-fully employed. S6 violations are zero in the
test corpus — this is the silent assumption that lets the identity test pass despite
the structural divergence.

**Verdict: ❌ Three-way divergence:** spec=20, MILP=15, SA=10, evaluator=missing.
All three are wrong vs. spec, and MILP ≠ SA creates an additional layer divergence
for any instance where assignment bounds are violated weekly.

---

### S7 — Total working weekends (weight 30)

**Officially scored at weight 30 per Ceschia 2019, Sec 2.5.**

- `penalty_evaluator.py`: MISSING. Not in `evaluate()` return dict.
- `heuristic.cpp:nurseCostFull`: MISSING. Not in `nc.total`.
- `milp_model.py:build()` (`milp_model.py:83,297–303`): implemented as `W_WEEKEND=30`,
  via `wk + h_wknd - max_wknds <= p_wk`.

**Verdict: ⚠️ SCOPE CHOICE — MILP implements S7; evaluator and SA do not.**  
Same pattern as S5: MILP search objective includes S7, reported score does not. No
Rule 12 documentation. `model.solve()` objective includes W_WEEKEND terms; the
`evaluate()` total does not.

---

### H3 — Forbidden successions (hard constraint)

All layers correctly treat H3 as a hard constraint with no soft scoring weight.

- `penalty_evaluator._compute_forbidden_successions`: returns count only, not included
  in `total`.
- `heuristic.cpp:nurseCostFull`: `nc.forbidden_hard` is counted separately, never
  added to `nc.total`. Gated by `M_FORBID` big-M in SA search (not a scoring weight).
- `milp_model.py:build()`: H3 enforced as hard linear constraints (lines 122–138).

**Dead code note:** `heuristic.cpp` defines `FORBIDDEN_WEIGHT = 25` (line 18), but
this constant is **never referenced** anywhere in the file. It predates the current
H3-hard design; it is dead code.

**Verdict: ✅ Correctly handled as hard in all three layers.**

---

## Summary of deviations

| # | Finding | Layers affected | Severity |
|---|---|---|---|
| 1 | S2 CS2c/d weight 15 vs spec 30 | evaluator + SA + MILP (all 3, same value) | ❌ Critical — every S2 measurement understated 2× |
| 2 | S3 weight 15 (eval/SA) vs spec 30 | evaluator + SA (MILP is correct at 30) | ❌ Critical — eval/SA underweight; breaks MILP-eval consistency for S3 |
| 3 | S6 3-way divergence (spec=20, MILP=15, SA=10, eval=missing) | all 3, all different | ❌ SA fullCost ≠ runEvalOnly when S6 violated; identity silent because test corpus has S6=0 |
| 4 | S2 CS2a/b entirely absent | evaluator + SA + MILP | ⚠️ Scope — intentional per SA comment; undocumented impact |
| 5 | S5 (complete weekend) in MILP only | evaluator + SA missing | ⚠️ Scope — MILP search includes it; reported score does not; no Rule 12 doc |
| 6 | S7 (total working weekends) in MILP only | evaluator + SA missing | ⚠️ Scope — same as S5 |
| 7 | FORBIDDEN_WEIGHT=25 is dead code | heuristic.cpp only | Low — unused, no functional impact |

---

## Impact on previously reported measurements

All measurements in `lookahead_design_notes.md §1`, `benchmark_results.md`,
and `PROJECT_STATUS.md` were produced with the evaluator using `_W_CONSEC=15`
for S2 (CS2c/d) and S3.

**If S2 CS2c/d is corrected to weight 30:**

| Measurement | As reported | Spec-correct S2 only |
|---|---|---|
| n012w8 post-H3-fix W3 total | 285 (S2=285) | 570 (S2=570) |
| n012w8 post-H3-fix SUM (W0-W7) | 410 (S2=300) | 710 (S2=600) |
| S10* attempt-1 SUM | 525 | ~875 |
| S10* attempt-2 SUM | 520 | ~865 |

**If S3 is also corrected to weight 30 in evaluator/SA** (to match the MILP and spec):

Additional correction: S3=30 in post-H3-fix baseline → spec-correct S3=60. Net
adjustment to SUM: +30. Combined S2+S3 correction: 410 → 740.

**S10* α implication:**  
`lookahead_design_notes.md §3 Q3` concluded α=15 because "our evaluator charges 15
per violation-day." If S2 weight is corrected to 30, the evaluator will charge 30
per violation-day, and α=30 becomes the spec-consistent "as if the violation had
already occurred" value. The existing S10* source (3 uncommitted files) uses α=15
(`W_CONSEC=15`, `milp_model.py:245`). If the weight is corrected before re-running
S10*, α should be updated to match.

---

## Recommended next steps (READ-ONLY AUDIT — no code changes in this segment)

Per task guardrails, no code is changed in this segment. The following are questions
for the architect to decide:

**Q-A:** Is S2 CS2c/d weight 30 confirmed by reading Ceschia 2019 Section 2.5 in the
PDF? (The above cites `romer2019_dag_milp.md` as the source; the PDF is authoritative.)

**Q-B:** If confirmed: which layer to fix first — evaluator only, or all three
simultaneously? Fixing evaluator alone re-establishes spec-correct reporting but
creates a temporary evaluator/SA identity break (until SA is also fixed). Fixing
all three simultaneously preserves identity but is a larger change surface.

**Q-C:** S3: evaluator/SA both use 15; MILP uses 30. Fix the evaluator/SA to 30
(matching MILP and spec), or downgrade the MILP to 15 (matching evaluator/SA)?

**Q-D:** S5/S7 (MILP-only): explicitly document these as Rule 12 search-time-only
terms (like S10*), or add them to the evaluator?

**Q-E:** S6: define a single canonical weight (spec says 20), then decide which
layers implement it, and document the objective membership per Rule 12.
