# Mischek & Musliu (2019) — IP Model Extensions for Multi-Stage NRP

**Citation:** Mischek, F. & Musliu, N. (2019). Integer programming model
extensions for a multi-stage nurse rostering problem. *Ann. Oper. Res.* 275,
123–143. https://doi.org/10.1007/s10479-017-2623-z

---

## Problem Setting (p. 124–127)

INRC-II instances are 4 or 8 weeks long. Each week's schedule must be fixed by
the solver using only: the global scenario file (nurses, contracts, global
counters), the current week's demand data, and a history file summarizing the
end-state of the previous week's solution. **Information about future weeks'
coverage requirements is not available** until the current week is fixed
(p. 125, "stepping horizon" per Salassa & Vanden Berghe 2012).

Two consequences (p. 125):
1. Even if every week is solved to per-week optimality, the overall multi-week
   schedule is not guaranteed optimal.
2. A naive per-week model produces **imbalanced schedules**: early weeks look
   good, but options get used up, causing **large penalties in later weeks**.

The basic per-week objective `f` (p. 127–128) is the standard INRC-II weighted
sum over S1–S7 for the *current week only*:
`f = 30·CS1 + 15·CS2a/b + 30·CS2c/d + 30·CS3a/b + 10·CS4 + 30·CS5 + 20·CS6 + 30·CS7`.
S6/S7 (global counters) are normally evaluated only after the last week, but
Mischek & Musliu compute and charge them **per-week incrementally** (p. 131,
eq. 25–27) — they note this does not change the overall total, only how it is
distributed across weeks.

---

## Model Extensions ("Look-Ahead" Constraints, Sect. 4, p. 131–138)

These are **additional soft constraints added to the current week's IP model**.
None of them require real future-week demand data — they only use information
already available at the current stage (current-week data + global counters
`a_n^tot`, `t_n^tot` carried from history, plus `|W|` and current week index `w`).

| Constraint | Idea | Mechanism | Weight used |
|---|---|---|---|
| **S8\*** Overstaffing (p. 131–132) | Penalize assigning *more* nurses than the optimal coverage `o^d_{sk}` for any shift/skill/day | `Σ x ≤ o^d_{sk} + C^{S8*}` (eq. 28) | 11.9 (IRACE-tuned) |
| **S6\*** Average assignments (p. 133–134) | Each nurse's cumulative assignments after week `w` must stay within `a_n^± · (w/|W|)` (proportional share of the contract bounds) | eq. 29–30 | 9.9 (IRACE-tuned) |
| **S6\*b** Average assignments (alt.) | Remaining assignments (`a_n^± − a_n^tot`) divided evenly over the *remaining* weeks `|W|−w+1` | eq. 31–32 | ~no diff. vs S6\* (p. 135) |
| **S7\*** Average working weekends (p. 134–135) | Same idea as S6\* applied to `t_n^+` (max working weekends) | eq. 33 | 9.9 (= W_{S7*}, tied to S6\*) |
| **S9\*** Restriction of next week's assignments (p. 135–137) | Penalize current-week assignment patterns that would *force* a violation in next week's sequence constraints (shift/work/rest stretch bounds), based only on current-week-end state | eq. 34–39 | low weight, but **worsened results** (p. 139) |
| **S10\*** Unresolvable patterns (p. 137–138) | Detects a specific end-of-week work-stretch pattern that *cannot* be completed in week `w+1` without violating either the max work-stretch length or the min shift-stretch length, regardless of what next week's demand turns out to be | eq. 40 | 15 (set equal to the shift-stretch-length weight, "as if the violation had already occurred", p. 139) |

**Key distinction:** S6\*/S7\*/S8\* are "self-balancing" constraints — they
spread *known* global budgets (assignment counts, weekend counts, coverage
slack) evenly across weeks. S9\*/S10\* are genuine **look-ahead-into-next-week**
constraints, reasoning about whether the current week's *tail* pattern leaves
next week's sequence constraints satisfiable — **without** assuming any
specific future demand.

---

## Reported Results (Sect. 5, p. 138–142)

- Individually, **S6\*/S7\* and S8\*** had the largest impact (Fig. 6, p. 139).
- S6\* and S6\*b performed "next to no difference" (p. 139).
- **S9\* increased penalties** when added — partly attributed to ~2× longer
  solve times causing more weeks to time out before optimality, but the paper
  notes this isn't the only cause: even instances solved to optimality with S9\*
  were worse (p. 139).
- Best combination: **S6\*/S7\* + S8\* + S10\*** (excludes S9\*) — this is
  called the "extended model" (p. 139–140).
- IRACE-tuned weights for the extended model (Table 1, p. 140):
  `W_{S6*}=W_{S7*}=9.9`, `W_{S8*}=11.9`, `W_{S10*}=15`.
- Extended model reduces total penalty by **~40% on average** vs. the basic
  per-week model, with no instance improving by less than 20% (p. 141).
- Compared against the 7 INRC-II finalists (Table 2, p. 141–142): the extended
  model achieves an **average rank of 3.45/7** — "competitive (slightly better
  than the median)", though no new best-known solutions (p. 141).

---

## Objective Membership / Final-Score Recalculation (p. 138, Sect. 4.6)

The extension surplus variables (`C^{S8*}`, `C^{S6*}`, `C^{S7*}`, `C^{S9*}`,
`C^{S10*}`) **are added to the per-week IP's objective `f'` during solving**,
but **after a week's solution is fixed, the actual reported penalty is
recomputed using only the basic objective `f`** (the official INRC-II S1–S7
weighted sum) — "to ensure that the penalties from the additional constraints
of the extended model are not included in the final result" (p. 138). All
extension constraints are also dropped entirely for the **last week** of the
horizon, since there is no future week left to protect (p. 138).

This is directly analogous to our Rule 12 (objective membership): the
look-ahead terms are a **search-time surrogate** (layer: SA/MILP search
objective only), while the **reported/official score** (layer: final
`evaluate()` / `final_cost`) must remain the unmodified S1–S4 INRC-II total.

---

## INRC-II Compliance

- Built directly on the official INRC-II problem definition (Ceschia et al.
  2015/2019) — same H1–H4 hard constraints, same S1–S7 weights (p. 126–127).
- The extensions are **additional soft constraints layered on top of** the
  official objective, scored out for the final report (see above) — they do
  **not** redefine or reweight S1–S7, and do not constitute a multi-objective
  reformulation (consistent with Rule 13).
