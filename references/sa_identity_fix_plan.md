# SA Cost Function Diagnostic — SA ≡ Evaluator Identity Fix

## Context

After fixing SA assignment-bound prorating (weekly ÷4), n012w8 ratio dropped to 2.0–2.6 ✓,
but n021w4 ratio remains 5–9 ✗. The target is **identity**: SA `nurseCostFull` must produce
the exact same per-schedule cost as the Python `penalty_evaluator` so the SA landscape
matches what the MILP optimized. Ratio comparison is not an acceptable substitute.

---

## Verified Findings (read-only analysis before any edit)

**S3 weight**: `penalty_evaluator.py` line 22 → `_W_CONSEC = 15`. Lines 105 and 115
both use `_W_CONSEC` for S2 (work) and S3 (off). **The draft plan's `CONSEC_OFF_W = 30`
was wrong.** No weight constant change is needed; `CONSEC_WEIGHT = 15` is already correct
for both.

**SA loop range**: `heuristic.cpp` line 235 → `for (int d = 0; d < D; d++)` where `D = 7`.
SA processes day 6 inside the loop. Evaluator (line 95) → `for d in range(6)`, explicitly
commenting "day 6 (Sunday) is never a run-end." They are **not** the same range.

**Two structural differences** exposed by comparing lines 238–244 (SA) vs lines 99–117
(evaluator):

| Issue | SA (lines 232–260) | Evaluator (lines 95–117) |
|---|---|---|
| SD-1: open-run scoring | Scores max-excess on every working day inside the loop (including d=6) **plus** post-loop check | Never scores open runs; defers to next week |
| SD-2: min-violation weight | Flat `CONSEC_WEIGHT` (line 240, 255) regardless of shortfall | Proportional `(min − run_len) × _W_CONSEC` (lines 105, 115) — diverges when `min − run_len > 1` |

**SD-3: same-shift block** (lines 274–291): SA-only; no equivalent in evaluator or MILP.

Simply deleting the post-loop checks (lines 244, 259) is **insufficient** because SA still
scores in-loop excess at d=6 for open runs. The loop itself must change.

---

## History Carry-in Analysis (pre-condition for Change A/B)

Evaluator carry-in logic (`penalty_evaluator.py` lines 92–117):

```python
prior_work = hist.get("consecutive_working_days", 0)
prior_off  = hist.get("consecutive_days_off", 0)

for d in range(6):
    if today_work and not next_work:          # work run ends at d
        run_len = _count_backward(row, d, working=True)
        if run_len == d + 1:                  # run occupies days 0..d (hit day 0)
            run_len += prior_work             # add cross-week carry
    elif not today_work and next_work:        # off run ends at d
        run_len = _count_backward(row, d, working=False)
        if run_len == d + 1:
            run_len += prior_off
```

Condition `run_len == d + 1`: fires when backward count from d reaches day 0 without
interruption, i.e., the run occupies the entire week prefix 0..d — meaning it extends
from the previous week.

SA transition-based carry-in (proposed Change A):
```cpp
run++;
if (d == 0 && nurse.hist_consec_work > 0)
    run += nurse.hist_consec_work;
```

Equivalence: `d == 0 && hist > 0` fires **only** when nurse works at d=0 AND has carry-in.
This is the same condition as the evaluator's `run_len == d+1` checked at the eventual
run-end. Trace example — nurse works d=0,1,2 (hist=3), off at d=3:

- SA: run starts at 0. d=0: run=1+3=4. d=1: run=5. d=2: run=6. d=3 (off): score 6.
- Evaluator at d=2 (transition): `_count_backward=3`, `3==2+1` → run_len=3+3=6. Score 6. ✓

If d=0 is off and hist_consec_work > 0: SA `else` branch fires, run stays 0 — historical
work run NOT scored. Evaluator also does not score it (no work→off transition fires at d=0).
Both defer the cross-week work run. ✓

Off run carry-in: condition `d == 0 && hist_consec_work == 0` ensures carry-in only when
the nurse ended last week on days off (`hist_consec_work == 0 → hist_consec_off > 0`).
When `hist_consec_work > 0`, `hist_consec_off` is 0 in INRC-II history, so `prior_off = 0`
in the evaluator regardless — the conditions are logically equivalent. ✓

**Mutual-exclusivity scan result** (pre-condition for using the boolean proxy):
Scanned all 51 H0 history files, 2,994 nurse-history entries across all test and production
instances (n005/n012/n021/n030/n040/n050/n060/n080/n100/n120, w4 and w8 variants).
Result: zero entries with both `consecutive_working_days > 0` AND `consecutive_days_off > 0`.
Distribution: 35.4% work-only, 64.6% off-only, 0% both. Value range: [1, 7] for both.
The boolean proxy `hist_consec_work == 0` is therefore **proven** to imply
`hist_consec_off > 0` for any instance in the INRC-II dataset. No actual-value fallback
needed. (If a future instance violates this — e.g., both > 0 — SA would silently under-add
carry-in. The scan is a one-time gate before Change B.)

---

## Component Source Analysis (pre-condition for per-item assertions)

**S2 (consecutive work)**  
SA: heuristic.cpp lines 232–244, weight `CONSEC_WEIGHT=15`.  
Evaluator: `_compute_s2_s3`, `_W_CONSEC=15`.  
Weight: matched. Logic: diverged (Changes A fixes). **Block on assertion.**

**S3 (consecutive off)**  
SA: heuristic.cpp lines 247–259, weight `CONSEC_WEIGHT=15`.  
Evaluator: `_compute_s2_s3`, `_W_CONSEC=15`.  
Weight: matched. Logic: diverged (Change B fixes). **Block on assertion.**

**S4 (shift-off requests / preferences)**  
SA: heuristic.cpp lines 293–301, `SHIFT_OFF_REQ_W=5`.  
Evaluator: `_compute_s4`, `_W_PREF=10`.  
Same violation condition (nurse × day × shiftType match). Weight: **DIVERGENT** (5 vs 10,
factor 2). **Known-divergent this round. Log violation count; do not block.**

**Forbidden succession — INRC-II classification: HARD (H3)**  
INRC-II competition defines three hard constraints: H1 (single assignment per day), H2
(required staffing not understaffed), **H3 (forbidden shift succession)**. Soft constraints
are S1–S7 only. Forbidden succession is therefore a **hard** constraint.  
Implication for SA: forbidden violations must NOT be included in the soft-penalty total.
`FORBIDDEN_WEIGHT=25` in SA incorrectly adds them to `nurseCostFull`'s `penalty`.  
Implication for evaluator: `_compute_forbidden_successions` correctly returns a count outside
`evaluate()`'s total — this is architecturally correct.  
Resolution (Change D): remove the forbidden block from `nurseCostFull` soft accumulation;
track as a separate `forbidden_hard` count. SA's total then equals evaluator's total structure
(S2+S3+S4 for nurse-level soft, S1 coverage separate). The `--eval-only` reports
`forbidden_violations` as a hard count outside `total`. For current test data (H3=0, empty
`forbidden_succ` set), this is a no-op behavior change — no violations exist to remove.  
Total alignment after Change D: `sa_total == eval_total` is now architecturally possible
(same components: S1+S2+S3+S4, no forbidden weight on either side).

---

### File 1: `inner_heuristic/src/heuristic.cpp`

#### Change A — Replace consecutive work block (lines 232–245) with transition-based scoring

The evaluator only scores a run when it **ends** (work→off transition) and scores
proportionally. Replace SA's incremental per-day logic with:

```cpp
// Consecutive working days (transition-based, matches evaluator)
{
    int run = 0;
    for (int d = 0; d < D; d++) {
        if (sched[n][d] != 0) {
            run++;
            if (d == 0 && nurse.hist_consec_work > 0)
                run += nurse.hist_consec_work;
        } else {
            if (run > 0) {
                if (run < contract.min_consec_work)
                    penalty += (contract.min_consec_work - run) * CONSEC_WEIGHT;
                else if (run > contract.max_consec_work)
                    penalty += (run - contract.max_consec_work) * CONSEC_WEIGHT;
                run = 0;
            }
        }
    }
    // No post-loop check: open run at week end is deferred (matches evaluator)
}
```

Fixes SD-1 (open runs) and SD-2 (min proportionality) simultaneously.

#### Change B — Replace consecutive off block (lines 247–260) with transition-based scoring

```cpp
// Consecutive days off (transition-based, matches evaluator)
{
    int run = 0;
    for (int d = 0; d < D; d++) {
        if (sched[n][d] == 0) {
            run++;
            if (d == 0 && nurse.hist_consec_work == 0)
                run += nurse.hist_consec_off;
        } else {
            if (run > 0) {
                if (run < contract.min_consec_off)
                    penalty += (contract.min_consec_off - run) * CONSEC_WEIGHT;
                else if (run > contract.max_consec_off)
                    penalty += (run - contract.max_consec_off) * CONSEC_WEIGHT;
                run = 0;
            }
        }
    }
    // No post-loop check
}
```

`CONSEC_WEIGHT = 15` on line 16 is **unchanged** (correct for both work and off).

#### Change C — Remove consecutive same-shift block (lines 274–291)

Delete the entire block (`// Consecutive same-shift type ... { ... }`). No equivalent in
evaluator or MILP.

#### Change D — Move forbidden succession from soft penalty to hard count

Replace the forbidden block (lines 221–230) in `nurseCostFull`: instead of
`penalty += FORBIDDEN_WEIGHT`, accumulate into `nc.forbidden_hard` (separate from `nc.total`).
The `FORBIDDEN_WEIGHT=25` constant remains defined but is no longer used in the soft total.
For all current INRC-II instances (H3=0, `prob.forbidden_succ` is an empty set), this is
a no-op behavior change. Architecturally aligns SA total with INRC-II definition and
evaluator's total structure.

---

### Prerequisite change — `nurseCostFull` returns a breakdown struct

To output per-component costs without writing a separate accumulation (which would introduce
a third drift source), change `nurseCostFull`'s return type from `int` to a struct:

```cpp
struct NurseCost {
    int s2_consec_work  = 0;
    int s3_consec_off   = 0;
    int s4_pref         = 0;
    int forbidden_hard  = 0;  // HARD H3 count — NOT included in total
    int total           = 0;  // s2 + s3 + s4 only
};
```

Each soft block inside `nurseCostFull` accumulates into its named field AND into `total`.
The forbidden block accumulates into `forbidden_hard` only (not `total`). The SA main loop
changes from `cost += nurseCostFull(...)` to `cost += nurseCostFull(...).total` — no behavior
change for soft cost. Delta evaluators also use `.total`. Logic inside blocks is **unchanged**.

### File 2: `inner_heuristic/src/main.cpp` — Add `--eval-only` flag

Add a branch at the top of `main()`:

```cpp
if (argc >= 2 && std::string(argv[1]) == "--eval-only") {
    int s1 = 0, s2 = 0, s3 = 0, s4 = 0, forbidden_hard = 0;
    for (int d = 0; d < prob.num_days; d++)
        s1 += coverageCostDay(prob, sched, d);
    for (int n = 0; n < prob.num_nurses; n++) {
        NurseCost nc = nurseCostFull(prob, sched, n);
        s2 += nc.s2_consec_work;
        s3 += nc.s3_consec_off;
        s4 += nc.s4_pref;
        forbidden_hard += nc.forbidden_hard;
    }
    int total = s1 + s2 + s3 + s4;  // matches evaluator total structure (hard excluded)
    // Output JSON: {S1_coverage, S2_consec_work, S3_consec_off, S4_preferences,
    //               forbidden_violations (hard count), total}
    // Exit 0
}
```

**Thin-wrapper rule satisfied**: calls `coverageCostDay` and `nurseCostFull` — the exact same
primitives as `fullCost()`. The breakdown comes from the struct fields, not from new
aggregation logic. Any future fix to a block inside `nurseCostFull` automatically applies.

---

## Diff Shape

```
heuristic.cpp Section 1 (weights)
  no change — CONSEC_WEIGHT = 15 stays

heuristic.cpp Section 4b — consec work block (lines 232–245)
  - int run = nurse.hist_consec_work;
  - for (...) { run++; if (run>max) +=flat; else {if(run<min) +=flat; run=0;} }
  - if (run > max_consec_work) penalty += CONSEC_WEIGHT;
  + int run = 0;
  + for (...) { if work {run++; if d==0&&hist>0 run+=hist;}
  +             else {if run>0 {proportional; run=0;}} }
  + (no post-loop)

heuristic.cpp Section 4b — consec off block (lines 247–260)
  - int run = (hist_work>0)?0:hist_off;
  - same incremental pattern
  - if (run > max_consec_off) penalty += CONSEC_WEIGHT;
  + same transition-based pattern, hist carry-in at d=0

heuristic.cpp Section 4b — forbidden block (lines 221–230)
  - penalty += FORBIDDEN_WEIGHT (×N violations)
  + nc.forbidden_hard += 1 per violation (not added to nc.total)

heuristic.cpp Section 4b — same-shift block (lines 274–291)
  - entire ~18-line block removed

heuristic.cpp Section 4b — nurseCostFull return type
  - static int nurseCostFull(...)
  + static NurseCost nurseCostFull(...)   [new struct added above fullCost]
  Soft blocks (S2/S3/S4) accumulate into named field AND nc.total.
  forbidden_hard block accumulates into nc.forbidden_hard only (not nc.total).
  All call sites: cost += nurseCostFull(...) → cost += nurseCostFull(...).total

main.cpp
  + --eval-only branch (~20 lines); calls coverageCostDay + nurseCostFull(.total / fields)
  total = s1 + s2 + s3 + s4 (forbidden_hard reported separately, not in total)
```

Delta evaluation (section 4d) calls `nurseCostFull` directly — no separate path to update.

---

## Verification (3-segment, each ends with explicit stop-and-report)

---

### 段1 — Read-only confirmation (no code, stop after report)

Execute ONLY:
1. Re-read `heuristic.cpp` lines 17–19 (weights), 221–230 (forbidden), 274–291 (same-shift)
   to confirm Component Source Analysis is consistent with the actual file.
2. Re-read `penalty_evaluator.py` lines 21–23 (`_W_CONSEC`, `_W_PREF`), `_compute_s4`,
   `_compute_forbidden_successions` to confirm evaluator side.
3. Confirm mutual-exclusivity scan result (recorded above) still matches actual H0 files
   (no re-scan needed — just verify the claim against the 3 smallest instances by inspection).
4. State the forbidden classification conclusion explicitly:
   - H3 hard → SA removes forbidden from soft total (Change D), forbidden_violations in
     `--eval-only` output but outside total. total alignment is now possible.
   - OR: provide counter-evidence and classify differently.

**Stop after 段1 report. Do not write any code. Wait for confirmation.**

---

### 段2 — Changes + narrow 10-case verification (stop after carry-in cases pass)

Only after 段1 is confirmed:

#### Step A — Implement Changes A, B, C, D + NurseCost struct + `--eval-only`

1. Rebuild:
```
cd inner_heuristic/build && make -j4
```
Must compile cleanly.

2. Write `tests/test_sa_carryin.py`. Each case: manually construct `problem_exchange.json`
with known schedule + known history, run `./nrp_heuristic --eval-only`, compare to evaluator.

Required cases (use a nurse with min_consec_work=2, max_consec_work=5,
min_consec_off=1, max_consec_off=4):

| Case | Schedule (d=0..6) | history | Expected |
|---|---|---|---|
| CW-1 | works d=0..6 (all 7) | hist_work=3 | sa_s2=0: run=10 DEFERRED (not exempt — if run ends next week, next week evaluator will score it there) |
| CW-2 | works d=0..4, off d=5..6 | hist_work=3 | run=3+5=8, exceeds max=5 → score |
| CW-3 | off d=0, works d=1..4, off d=5..6 | hist_work=3 | hist NOT carried, run=4, no excess |
| CW-4 | works d=0..1, off d=2..6 | hist_work=4 | run=4+2=6, exceeds max=5 → score |
| CW-min | works d=0, off d=1..6 | hist_work=0 | run=1, violates min=2 → proportional |
| CO-1 | off d=0..4, works d=5..6 | hist_off=3 | off run=3+5=8, exceeds max=4 → score |
| CO-2 | works d=0, off d=1..4, works d=5..6 | hist_off=3 | hist NOT carried, off run=4, exact max |
| CO-3 | off d=0..2, works d=3..6 | hist_off=2 | off run=2+3=5, exceeds max=4 → score |
| Boundary | works d=0..4, off d=5..6 | hist_work=0 | run=5, exactly at max → no penalty |

Additional case — cross-week continuation:  
Week A = CW-1 (all 7 days working, hist_work=3, run=10 deferred). Week B history: hist_work=10.
Week B schedule: off d=0. Expected: Week B SA scores run=10 > max=5. Assert both weeks
against evaluator. Verifies deferral ≠ exemption.

Assertions per case: `abs(sa_s2 - eval_S2) < 1e-6` AND `abs(sa_s3 - eval_S3) < 1e-6`.
If any case fails: print case name, schedule, history, SA breakdown, evaluator breakdown.
**Stop immediately — do not continue to next case.**

**Stop after 段2 report (all 10 carry-in cases pass). Do not run 800 random. Wait for confirmation.**

---

### 段3 — Broad verification (only after 段2 confirmed)

Only after 段2 is confirmed:

#### Step B — Per-component identity test (N=200 random × 4 week contexts = 800 total)

Write `tests/test_sa_identity.py`:

1. Build pool of problem_exchange.json contexts:
   - n021w4 week 0 (no history)
   - n021w4 weeks 1, 2, 3 (propagated history from multi_week_runner)
2. Generate N=200 random schedules per context (800 total).
3. For each schedule:
   a. Run `./nrp_heuristic --eval-only <temp.json>` → parse: `sa_s1`, `sa_s2`, `sa_s3`,
      `sa_s4`, `sa_forbidden_violations`, `sa_total`.
   b. Run `penalty_evaluator.evaluate(sched, data)` → parse all fields.
   c. Per-component assertions:
      - S1: known-divergent (coverage not same-source). Log ratio; do NOT assert.
      - S2: **Assert** `abs(sa_s2 - eval_S2_consecutive_work) < 1e-6` → BLOCK.
      - S3: **Assert** `abs(sa_s3 - eval_S3_consecutive_off) < 1e-6` → BLOCK.
      - S4: known-divergent (weight 5 vs 10). Log; do NOT assert.
      - Forbidden: **Assert** `abs(sa_forbidden_violations - eval_forbidden_violations) < 1e-6`
        → BLOCK (both are raw counts after Change D; H3=0 means always 0, so mismatch ≠ 0
        signals a parsing/logic bug).
   d. On any blocking failure: print schedule index, per-component breakdown, stop immediately.

**Pass criterion**: all 800 schedules clean on S2, S3, forbidden. S1 and S4 known-divergent.

#### Step C — Regression
```
python3 -m pytest tests/ -v
```
Must remain 4/4.

#### Step D — Pipeline smoke test
Run n021w4 week 1. Report SA/evaluator ratio. If Step B failed, skip this step.