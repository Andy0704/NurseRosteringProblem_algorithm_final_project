# H3 Forbidden-Succession Leak — n012w8 W3 Diagnostic (段1)

Diagnostic for Finding 1 of the Phase 2 look-ahead evidence base
(`lookahead_design_notes.md`): n012w8 weeks 3–6 show
`forbidden_succession_violations` (H3, INRC-II hard constraint, Ceschia et al.
2019 §2.5.1) of 15, 15, 16, 2 respectively in the SA output. This document
bisects **week 3 (15 violations)** to find where in the pipeline they enter.

Reproducible via `/tmp/h3_bisect_w3.py` (temporary, not committed; reuses
`MilpModel`, `parse`, `_run_fo`, `_run_sa`, `evaluate`,
`_compute_forbidden_successions` from the existing codebase without
modification).

---

## 1. Step 1 — Confirmation (real violation, not an evaluator artifact)

For the SA output schedule of W3, every `(nurse, day→day+1, shift_d, shift_d+1)`
pair flagged by `penalty_evaluator._compute_forbidden_successions` was printed
and manually checked against the scenario's `forbidden_successions` table
(`Night→{Early,Day,Late}`, `Late→{Early,Day}` per `Sc-n012w8.json`):

```
nurse=Alice day0->day1: Night -> Day
nurse=Alice day4->day5: Night -> Early
nurse=Bob   day1->day2: Night -> Early
nurse=Bob   day4->day5: Late  -> Early
nurse=John  day1->day2: Night -> Day
nurse=Kate  day0->day1: Late  -> Early
nurse=Mary  day3->day4: Late  -> Early
nurse=Mary  day5->day6: Late  -> Day
nurse=Arthur day2->day3: Night -> Day
nurse=Pier  BOUNDARY hist_last=Night -> day0=Early
nurse=Pier  day3->day4: Night -> Day
nurse=Lucy  BOUNDARY hist_last=Night -> day0=Day
nurse=Maggie day2->day3: Night -> Early
nurse=Jane  day1->day2: Night -> Late
nurse=Jane  day3->day4: Late  -> Early
```

Manual recount = **15**, matches `evaluate()["forbidden_succession_violations"]`
= 15, and a direct call to `_compute_forbidden_successions()` also returns 15.
**Confirmed real** — every pair listed is a genuine `(s1, s2)` member of
`forbidden_successions` (e.g. Night→Day, Night→Early, Late→Early, Night→Late,
Late→Day are all forbidden successions per the scenario file), including two
cross-week **boundary** violations (Pier, Lucy: history's `last_shift_index`
= Night, followed by a work shift on day 0 of W3). This is not an evaluator
boundary/off-by-one bug.

---

## 2. Step 2 — Bisection table

| Stage | H3 (forbidden) count | Notes |
|---|---:|---|
| MILP solve (W3) | **0** | `model.solve()` output |
| F&O (1 pass, FREE_COUNT=2) | **0** | 0/6 pairs accepted (no F&O improvement found within time limit, schedule unchanged from MILP) |
| SA seed (= exchange JSON fed to `nrp_heuristic`) | **0** | identical schedule to F&O output, re-evaluated |
| **SA output (`best_sched`)** | **15** | matches the originally measured value |

The leak occurs entirely **within the SA stage** (MILP and F&O are clean).

---

## 3. Identified root cause stage: **SA (`heuristic.cpp`)**

Per Step 3/4 checks: `MilpModel.build()` applies H3 as a hard PuLP constraint
for every nurse, every day pair, **and** the cross-week boundary (history
`last_shift_index` → day 0), via `H3_{n}_{d}_{s1}_{s2}` and `H3h_{n_idx}_{s_to}`
(`outer_milp/models/milp_model.py` lines 118–135). `fix_and_optimize()` calls
`build()` again from scratch (line 368), so the same hard H3 constraints apply
to the F&O sub-problem too. Both MILP and F&O outputs are confirmed H3-clean
(Step 2), so neither is the entry point.

### Root cause (Step 5): H3 is excluded from the cost SA's search optimizes

`inner_heuristic/src/heuristic.cpp`:

```
259: // forbidden_hard is an H3 hard-constraint count — NOT included in total.
260: // total = s2_consec_work + s3_consec_off + s4_pref + assignment (soft only).
261: struct NurseCost {
262:     int s2_consec_work = 0;
263:     int s3_consec_off  = 0;
264:     int s4_pref        = 0;
265:     int forbidden_hard = 0;
266:     int total          = 0;
267: };
...
278:     // Forbidden successions — H3 HARD constraint (Change D):
279:     // count violations separately; do NOT add to soft total.
280:     if (nurse.hist_last_shift != 0 && sched[n][0] != 0) {
281:         if (prob.forbidden_succ.count({nurse.hist_last_shift, sched[n][0]}))
282:             nc.forbidden_hard++;
283:     }
284:     for (int d = 1; d < D; d++) {
285:         int from = sched[n][d - 1], to = sched[n][d];
286:         if (from != 0 && to != 0 && prob.forbidden_succ.count({from, to}))
287:             nc.forbidden_hard++;
288:     }
```

`forbidden_hard` is computed per nurse, but **deliberately excluded from
`nc.total`** (per the 2026-06-04 "Change D" fix that moved forbidden out of
the *soft* total — see `SA_IDENTITY_DIAGNOSTIC.md`). The three SA delta
functions all compute their delta exclusively from `.total` plus the H2
coverage `M_COVER` term:

```
389: static int deltaTwoWaySwap(...)
...
395:     int old_partial = coverageCostDay(prob, sched, d)
396:                     + nurseCostFull(prob, sched, n1).total
397:                     + nurseCostFull(prob, sched, n2).total;
...
407:     return (new_partial - old_partial) + M_COVER * (new_units - old_units);
```

(identical pattern in `deltaRandomDayOff` lines 415–433 and
`deltaShiftTypeChange` lines 441–459 — neither reads `.forbidden_hard` at all).

**Consequence:** a move that creates or removes an H3 violation produces
`delta == 0` for that change (the violation is invisible to `cur_cost`,
`best_cost`, the Metropolis criterion, and Late Acceptance). SA can freely
introduce H3 violations at zero apparent cost.

Additionally, the `best_sched` promotion gate (line 630) only checks H2
feasibility, with **no analogous H3 check**:

```
626:             // best_sched gate: cur_cost includes the M_COVER surcharge, but the
...
628:             // Require explicit H2-feasibility (totalH2Units==0) before promoting
629:             // a state to best_sched, so the returned solution is always H2-clean.
630:             if (cur_cost < best_cost && totalH2Units(prob, sched) == 0) {
631:                 ...
632:                 best_sched = sched;
```

So even if a candidate state has `forbidden_hard > 0`, it can still be
promoted to `best_sched` as long as `totalH2Units == 0` and `cur_cost <
best_cost` — both conditions are satisfied for the W3 output (final_cost=170,
totalH2Units(best_sched)==0, but forbidden=15).

Finally, `runHeuristic`'s `result["metadata"]` never reports `forbidden_violations`
at all (only `runEvalOnly`, a separate `--eval-only` CLI path, computes it —
`heuristic.cpp` lines 678–703). This means the SA binary's own output gives no
signal that it has produced an H3-infeasible schedule; the leak is only
visible via the Python-side `penalty_evaluator`.

---

## 4. Verbatim code citations

- `inner_heuristic/src/heuristic.cpp:259-267` — `NurseCost` struct, comment
  documents `forbidden_hard` is excluded from `.total` by design (2026-06-04
  "Change D").
- `inner_heuristic/src/heuristic.cpp:278-288` — `forbidden_hard` computed in
  `nurseCostFull`, including the cross-week boundary case (line 280-283),
  but never folded into `.total`.
- `inner_heuristic/src/heuristic.cpp:389-408` — `deltaTwoWaySwap`: delta
  computed from `.total` + `M_COVER * Δunits` only; no `forbidden_hard` term.
- `inner_heuristic/src/heuristic.cpp:415-433` — `deltaRandomDayOff`: same
  pattern.
- `inner_heuristic/src/heuristic.cpp:441-459` — `deltaShiftTypeChange`: same
  pattern.
- `inner_heuristic/src/heuristic.cpp:626-634` — `best_sched` gate checks
  `totalH2Units(prob, sched) == 0` only; no H3 analogue.
- `inner_heuristic/src/heuristic.cpp:665-669` — `runHeuristic`'s
  `result["metadata"]` sets only `initial_cost`/`final_cost`; no
  `forbidden_violations` field (unlike `runEvalOnly`, lines 695-702).
- `outer_milp/models/milp_model.py:118-135` — H3 hard constraints (within-week
  `H3_{n}_{d}_{s1}_{s2}` and cross-week boundary `H3h_{n_idx}_{s_to}`), applied
  in every `build()` call including inside `fix_and_optimize()` (line 368).
  Confirmed H3-clean for W3 MILP and F&O outputs (Step 2).

---

## 5. Proposed minimal fix (description only — NOT implemented)

The 2026-06-13/14 H2 fix already establishes the pattern to follow for H3:

1. **Add an `M_FORBID`-style big-M penalty** (analogous to `M_COVER` for H2,
   Knust 2019 p0=0.05 derivation) proportional to the *change* in
   `forbidden_hard` for the affected nurse/nurses, inside each of the three
   delta functions (`deltaTwoWaySwap`, `deltaRandomDayOff`,
   `deltaShiftTypeChange`) — mirroring how `M_COVER * (new_units - old_units)`
   is added today for H2.
2. **Extend the bookkeeping invariant** from
   `cur_cost_k = fullCost(s_k) + M_COVER * totalH2Units(s_k)` to also include
   `+ M_FORBID * totalForbiddenViolations(s_k)`, and strip both terms when
   computing `final_cost = best_cost - M_COVER*totalH2Units(best_sched) -
   M_FORBID*totalForbiddenViolations(best_sched)`.
3. **Extend the `best_sched` gate** (line 630) to require
   `totalForbiddenViolations(sched) == 0` in addition to
   `totalH2Units(sched) == 0`, so a returned `best_sched` is always both
   H2- and H3-feasible (matching the seed, which is H3-clean per Step 2).
4. **(Optional, low priority)** add `forbidden_violations` to
   `runHeuristic`'s `result["metadata"]` (currently only in `runEvalOnly`) so
   the C++ binary's own output surfaces H3 feasibility without requiring the
   Python evaluator as a second pass.

This fix is structurally identical to the existing H2/M_COVER mechanism and
would not require new data structures — `forbidden_hard` is already computed
per nurse in `nurseCostFull` (Step 5), it just needs to be summed across nurses
(a `totalForbiddenViolations()` helper analogous to `totalH2Units()`) and
wired into the delta/gate/bookkeeping exactly as `totalH2Units`/`M_COVER` are
today.

**Open question for 段2 / implementation segment:** whether fixing this changes
the n012w8 W3–W6 cross-week profile measured in `lookahead_design_notes.md`
§1 (S3=75 spike in W3, S2=105 spike in W6) — if SA is currently "spending"
some of its search budget producing now-untracked H3 violations instead of
repairing S2/S3, fixing H3 first could shift those numbers before Phase 2
look-ahead design is finalized.
