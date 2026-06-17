"""Segment 3: Broad SA ≡ evaluator identity test — 800 random schedules.

Contexts: n021w4 weeks 0/1/2/3 with MILP-propagated history (4 × 200 = 800).
BLOCK (< 1e-6): S2_consecutive_work, S3_consecutive_off, S4_preferences,
forbidden_violations.
LOG only (known-divergent): S1_coverage (weight/source differ).

On any BLOCK failure: print schedule, nurse histories, both-side breakdowns; stop immediately.

W-2/W-3 NOTE: S2_consecutive_work and S3_consecutive_off identity is intentionally
broken between W-2 (evaluator CONSEC_WEIGHT corrected to 30 per Ceschia 2019) and
W-3 (heuristic.cpp CONSEC_WEIGHT correction). Both tests below FAIL until W-3.
"""

import copy
import json
import os
import random
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from outer_milp.models.milp_model import MilpModel
from outer_milp.utils.inrc2_parser import parse
from outer_milp.utils.penalty_evaluator import evaluate
from outer_milp.utils.multi_week_runner import _end_of_week_history

BINARY   = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "inner_heuristic", "build", "nrp_heuristic"))
INSTANCE = "data/raw_inrc2/testdatasets_json/n021w4"
N_RANDOM = 200
RNG_SEED = 42


# ── helpers ──────────────────────────────────────────────────────────────────

def _run_eval_only(data: dict, schedule: list) -> dict:
    d = copy.deepcopy(data)
    d["current_schedule"] = schedule
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(d, f)
        fname = f.name
    try:
        res = subprocess.run(
            [BINARY, "--eval-only", fname],
            capture_output=True, text=True, timeout=15,
        )
        if res.returncode != 0:
            raise RuntimeError(f"--eval-only failed: {res.stderr.strip()}")
        return json.loads(res.stdout)
    finally:
        os.unlink(fname)


def _build_week_contexts():
    """Solve MILP for each week and propagate history, returning 4 data dicts."""
    contexts = []
    carry = None
    for week in range(4):
        data = parse(INSTANCE, week=week, history=0)
        if carry is not None:
            for n_idx in range(len(data["nurse_info"])):
                data["nurse_info"][n_idx]["history"] = carry[n_idx]["history"]
        contexts.append(copy.deepcopy(data))
        model = MilpModel(data)
        model.build()
        sched, _ = model.solve(time_limit=15)
        carry = _end_of_week_history(sched, data["nurse_info"])
    return contexts


def _block_fail(label: str, comp: str, sched: list, data: dict,
                sa_out: dict, ev_out: dict) -> None:
    """Print failure details and stop.  Called only when SA ≠ eval on a BLOCK item."""
    nurses = data["nurse_info"]
    print(f"\n{'='*70}")
    print(f"BLOCK FAILURE  {label}  component={comp}")
    print(f"  SA  breakdown : {sa_out}")
    print(f"  Eval breakdown: {ev_out}")
    print(f"  Schedule (nurse × day), 0=Off:")
    for n_idx, row in enumerate(sched):
        hist = nurses[n_idx]["history"]
        print(f"    N{n_idx:02d} row={row}  "
              f"hist_cw={hist['consecutive_working_days']}  "
              f"hist_co={hist['consecutive_days_off']}")
    print(f"{'='*70}")


# ── main test ─────────────────────────────────────────────────────────────────

def test_sa_identity_800():
    """800 random schedules: S2, S3, forbidden must be SA≡eval within 1e-6."""
    contexts = _build_week_contexts()
    rng = random.Random(RNG_SEED)

    s1_diffs = []
    total_checked = 0

    for week_idx, data in enumerate(contexts):
        N = data["metadata"]["num_nurses"]
        D = data["metadata"]["num_days"]
        S = data["metadata"]["num_shift_types"]

        for i in range(N_RANDOM):
            sched = [[rng.randint(0, S - 1) for _ in range(D)] for _ in range(N)]
            label = f"W{week_idx}_#{i:03d}"

            sa_out = _run_eval_only(data, sched)

            data_ev = copy.deepcopy(data)
            data_ev["current_schedule"] = sched
            ev_out = evaluate(sched, data_ev)

            sa_s2 = sa_out["S2_consecutive_work"]
            sa_s3 = sa_out["S3_consecutive_off"]
            sa_s4 = sa_out["S4_preferences"]
            sa_fb = sa_out["forbidden_violations"]
            ev_s2 = ev_out["S2_consecutive_work"]
            ev_s3 = ev_out["S3_consecutive_off"]
            ev_s4 = ev_out["S4_preferences"]
            ev_fb = ev_out["forbidden_succession_violations"]

            # Log known-divergent (do not block)
            s1_diffs.append(abs(sa_out["S1_coverage"] - ev_out["S1_coverage"]))

            # BLOCK assertions
            # W-2/W-3: S2 and S3 FAIL here (eval weight=30, SA weight still=15) until W-3.
            if abs(sa_s2 - ev_s2) >= 1e-6:
                _block_fail(label, "S2", sched, data, sa_out, ev_out)
                pytest.fail(f"{label}: S2 mismatch  sa={sa_s2}  eval={ev_s2}")

            if abs(sa_s3 - ev_s3) >= 1e-6:
                _block_fail(label, "S3", sched, data, sa_out, ev_out)
                pytest.fail(f"{label}: S3 mismatch  sa={sa_s3}  eval={ev_s3}")

            if abs(sa_s4 - ev_s4) >= 1e-6:
                _block_fail(label, "S4", sched, data, sa_out, ev_out)
                pytest.fail(f"{label}: S4 mismatch  sa={sa_s4}  eval={ev_s4}")

            if abs(sa_fb - ev_fb) >= 1e-6:
                _block_fail(label, "forbidden", sched, data, sa_out, ev_out)
                pytest.fail(f"{label}: forbidden mismatch  sa={sa_fb}  eval={ev_fb}")

            total_checked += 1

    # ── known-divergent summary ──────────────────────────────────────────────
    nonzero_s1 = sum(1 for d in s1_diffs if d > 0)
    print(f"\n=== KNOWN-DIVERGENT LOG ({total_checked} schedules) ===")
    print(f"  S1_coverage  : nonzero_diff={nonzero_s1}/{total_checked}  "
          f"min={min(s1_diffs)}  max={max(s1_diffs)}  "
          f"mean={sum(s1_diffs)/len(s1_diffs):.1f}")
    print(f"  BLOCK items (S2, S3, S4, forbidden): ALL CLEAN ✓")


def test_sa_h2_feasible_no_bigm_leak():
    """SA with big-M must return an H2-feasible, big-M-free solution.

    WHY (Rule 9): the big-M penalty lives only in the SA acceptance path.
    This test proves three invariants:
      1. SA moved: final_cost < initial_cost (not frozen).
      2. H2-feasible: runEvalOnly(best_sched).S1_coverage == 0.
      3. No big-M leak, via IDENTITY (not absolute equality):
         |runEvalOnly(best_sched).total - evaluator.evaluate(best_sched)['total']|
         < 1e-6. If M_COVER had leaked into runEvalOnly's totals, it would
         diverge from the evaluator -- same standard as the 800-schedule
         identity test.

    final_cost includes SA-guidance prorated S6 (weekly assignment bounds);
    runEvalOnly and penalty_evaluator measure per-week INRC-II score only.
    final_cost intentionally != evaluator_total -- this is by design, not a bug.
    The no-big-M-leak proof uses runEvalOnly vs evaluator identity (<1e-6).

    Instance: n005w4 week 3 (MILP-seeded weeks 0-3, sa_initial=330 > sa_final=30).
    n021w4 week 2 was used before W-6 but became frozen (sa_initial==sa_final)
    after TOTAL_ASSIGN_W 10→20 changed the MILP seed enough that SA found no
    improvement. n005w4 week 3 reliably shows large SA movement (330→30).
    """
    INSTANCE_N005W4 = "data/raw_inrc2/testdatasets_json/n005w4"
    # Chain MILP solves for weeks 0-3 to build an H2-feasible week-3 seed
    # with correctly propagated history.
    carry = None
    data = None
    for week in range(4):
        data = parse(INSTANCE_N005W4, week=week, history=0)
        if carry is not None:
            for n_idx in range(len(data["nurse_info"])):
                data["nurse_info"][n_idx]["history"] = carry[n_idx]["history"]
        model = MilpModel(data)
        model.build()
        sched, _ = model.solve(time_limit=15)
        data["current_schedule"] = sched
        carry = _end_of_week_history(sched, data["nurse_info"])
    # data is now week 3, MILP-seeded

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        fname = f.name
    try:
        res = subprocess.run(
            [BINARY, fname, fname], capture_output=True, text=True, timeout=120,
        )
        assert res.returncode == 0, f"SA binary failed: {res.stderr.strip()}"
        with open(fname, "r", encoding="utf-8") as fp:
            sa_out = json.load(fp)
    finally:
        os.unlink(fname)

    sa_initial = sa_out["metadata"]["initial_cost"]
    sa_final   = sa_out["metadata"]["final_cost"]
    best_sched = sa_out["current_schedule"]

    # 1. SA moved (no longer frozen)
    assert sa_final < sa_initial, (
        f"SA appears frozen: sa_initial={sa_initial}  sa_final={sa_final}")

    sa_eval = _run_eval_only(data, best_sched)

    # 2. H2-feasibility of best_sched
    assert sa_eval["S1_coverage"] == 0, (
        f"best_sched violates H2: S1_coverage={sa_eval['S1_coverage']}")

    # 3. No big-M leak: runEvalOnly(best_sched).total must match
    # penalty_evaluator.evaluate(best_sched)['total'] exactly (<1e-6).
    data_ev = copy.deepcopy(data)
    data_ev["current_schedule"] = best_sched
    ev_out = evaluate(best_sched, data_ev)
    assert abs(sa_eval["total"] - ev_out["total"]) < 1e-6, (
        f"big-M leak suspected: runEvalOnly(best_sched).total={sa_eval['total']} != "
        f"evaluator.total={ev_out['total']}")


def test_sa_h2_repair_from_infeasible_seed():
    """SA must repair an H2-infeasible incoming seed without corrupting final_cost.

    WHY (Rule 9): the cur_cost/best_cost bookkeeping carries an M_COVER *
    totalH2Units(seed) baseline. If the baseline init is wrong, final_cost
    for a repaired (H2-feasible) best_sched comes out as a large negative
    number (e.g. -2966) instead of a clean fullCost (e.g. 30) -- the bug
    fixed alongside this test.

    Setup: take an H2-feasible MILP-seeded week-2 schedule (n021w4) and
    knock one nurse off a binding minimum-coverage shift, producing
    totalH2Units(seed) > 0.
    """
    carry = None
    data = None
    for week in range(3):
        data = parse(INSTANCE, week=week, history=0)
        if carry is not None:
            for n_idx in range(len(data["nurse_info"])):
                data["nurse_info"][n_idx]["history"] = carry[n_idx]["history"]
        model = MilpModel(data)
        model.build()
        sched, _ = model.solve(time_limit=15)
        data["current_schedule"] = sched
        carry = _end_of_week_history(sched, data["nurse_info"])
    # data is now an H2-feasible week-2 seed

    sched = data["current_schedule"]
    D = data["metadata"]["num_days"]
    S = data["metadata"]["num_shift_types"]
    demand = data["requirements"]["demand_by_skill"]

    # Find a (day, skill, shift) exactly at minimum coverage (deficit == 0),
    # then send one assigned nurse home to create totalH2Units(seed) == 1.
    knocked = False
    for d in range(D):
        for skill, dem in demand.items():
            for s in range(1, S):
                required = dem[d][s - 1]
                if required <= 0:
                    continue
                assigned_nurses = [
                    n for n, ni in enumerate(data["nurse_info"])
                    if sched[n][d] == s and skill in ni["skills"]
                ]
                if len(assigned_nurses) == required:
                    sched[assigned_nurses[0]][d] = 0
                    knocked = True
                    break
            if knocked:
                break
        if knocked:
            break
    assert knocked, "no binding minimum-coverage shift found to knock off"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        fname = f.name
    try:
        res = subprocess.run(
            [BINARY, fname, fname], capture_output=True, text=True, timeout=120,
        )
        assert res.returncode == 0, f"SA binary failed: {res.stderr.strip()}"
        assert "incoming schedule violates H2" in res.stderr, (
            f"expected H2-infeasible seed warning, got: {res.stderr.strip()}")
        with open(fname, "r", encoding="utf-8") as fp:
            sa_out = json.load(fp)
    finally:
        os.unlink(fname)

    final_cost = sa_out["metadata"]["final_cost"]
    best_sched = sa_out["current_schedule"]

    # 1. final_cost must never be negative (the bug's most obvious symptom).
    assert final_cost >= 0, f"final_cost is negative: {final_cost}"

    # 2. best_sched must be H2-feasible (SA repaired the seed).
    sa_eval = _run_eval_only(data, best_sched)
    assert sa_eval["S1_coverage"] == 0, (
        f"best_sched still violates H2: S1_coverage={sa_eval['S1_coverage']}")

    # 3. final_cost == eval total + (small, non-negative) S5 design-gap --
    # not eval total - M_COVER (which would be a large negative number).
    gap = final_cost - sa_eval["total"]
    assert 0 <= gap < 200, (
        f"final_cost - eval_total={gap} outside expected S5-gap range "
        f"(final_cost={final_cost}, eval_total={sa_eval['total']})")
