"""Segment 2: 10 deterministic carry-in cases for SA ≡ evaluator identity.

Each case:
  - Constructs a minimal problem_exchange.json with a known schedule + history.
  - Runs ./nrp_heuristic --eval-only to get SA's S2/S3 breakdown.
  - Runs penalty_evaluator.evaluate() to get evaluator's S2/S3.
  - Asserts abs(sa_s2 - eval_s2) < 1e-6 AND abs(sa_s3 - eval_s3) < 1e-6.

On any failure: prints case name, schedule, history, SA breakdown, evaluator breakdown,
then stops immediately (no further cases run).

Contract used for all cases unless noted:
  min_consec_work=2, max_consec_work=5, min_consec_off=1, max_consec_off=4
  min_assign=0, max_assign=28 (weekly bounds: [0,7] — never fires)
  No shift-off requests; No forbidden successions.

W-2/W-3 NOTE: S2 and S3 identity is intentionally broken between W-2 (evaluator
CONSEC_WEIGHT corrected to 30 per Ceschia 2019) and W-3 (heuristic.cpp correction).
7 tests (CW-2, CW-4, CW-min, CO-1, CO-2, CO-3, CW-1-WeekB) will FAIL until W-3.
expected_s2/s3 below reflect the correct spec weight (30); SA still returns weight-15
values. Identity is restored in W-3.
"""

import json
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from outer_milp.utils.penalty_evaluator import evaluate

BINARY = os.path.join(os.path.dirname(__file__), "..", "inner_heuristic", "build", "nrp_heuristic")

# Contract: min_cw=2, max_cw=5, min_co=1, max_co=4
# 3 shifts: Off=0, Early=1, Day=2  (no forbidden successions)
BASE_DATA = {
    "metadata": {"num_nurses": 1, "num_days": 7, "num_shift_types": 3},
    "shift_mapping": [
        {"index": 0, "id": "Off",   "is": "Off"},
        {"index": 1, "id": "Early", "name": "Early"},
        {"index": 2, "id": "Day",   "name": "Day"},
    ],
    "nurse_info": [{
        "index": 0, "id": "N0", "contract_id": "C",
        "history": {
            "consecutive_working_days": 0,
            "consecutive_days_off": 0,
            "last_shift_index": 0,
            "num_assignments": 0,
            "num_working_weekends": 0,
            "num_consecutive_shift_assignments": 0,
        },
        "skills": [],
    }],
    "contracts": {"C": {
        "minimumNumberOfConsecutiveWorkingDays": 2,
        "maximumNumberOfConsecutiveWorkingDays": 5,
        "minimumNumberOfConsecutiveDaysOff": 1,
        "maximumNumberOfConsecutiveDaysOff": 4,
        "minimumNumberOfAssignments": 0,
        "maximumNumberOfAssignments": 28,
        "maximumNumberOfWorkingWeekends": 4,
        "completeWeekends": 0,
    }},
    "requirements": {"demand_matrix": [[0, 0]] * 7, "demand_by_skill": {}},
    "current_schedule": [[0] * 7],
    "shift_type_constraints": {"forbidden_successions": {}},
    "shift_off_requests": [],
    "skills": [],
}


def _run_eval_only(data: dict) -> dict:
    """Write data to a temp file, invoke --eval-only, return parsed JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        fname = f.name
    try:
        result = subprocess.run(
            [BINARY, "--eval-only", fname],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(f"--eval-only failed: {result.stderr.strip()}")
        return json.loads(result.stdout)
    finally:
        os.unlink(fname)


def _make_data(schedule_row: list, hist_cw: int, hist_co: int,
               last_shift: int = 0) -> dict:
    """Build a single-nurse problem dict with the given schedule and history."""
    import copy
    data = copy.deepcopy(BASE_DATA)
    data["current_schedule"] = [schedule_row]
    data["nurse_info"][0]["history"].update({
        "consecutive_working_days": hist_cw,
        "consecutive_days_off": hist_co,
        "last_shift_index": last_shift,
    })
    return data


def _assert_case(name: str, schedule: list, hist_cw: int, hist_co: int,
                 expected_s2: int, expected_s3: int, last_shift: int = 0):
    """Run both SA and evaluator; assert S2 and S3 match expected and each other."""
    data = _make_data(schedule, hist_cw, hist_co, last_shift)

    sa_out = _run_eval_only(data)
    ev_out = evaluate([schedule], data)

    sa_s2 = sa_out["S2_consecutive_work"]
    sa_s3 = sa_out["S3_consecutive_off"]
    ev_s2 = ev_out["S2_consecutive_work"]
    ev_s3 = ev_out["S3_consecutive_off"]

    ok = True
    if abs(sa_s2 - ev_s2) >= 1e-6 or abs(sa_s3 - ev_s3) >= 1e-6:
        ok = False

    if not ok:
        print(f"\n{'='*60}")
        print(f"FAILURE: {name}")
        print(f"Schedule : {schedule}  hist_cw={hist_cw}  hist_co={hist_co}")
        print(f"SA  : s2={sa_s2}  s3={sa_s3}   full={sa_out}")
        print(f"Eval: s2={ev_s2}  s3={ev_s3}   full={ev_out}")
        print(f"Expected s2={expected_s2}  s3={expected_s3}")
        print(f"{'='*60}")
        pytest.fail(f"Case {name}: sa_s2={sa_s2} eval_s2={ev_s2}  sa_s3={sa_s3} eval_s3={ev_s3}")

    assert abs(sa_s2 - expected_s2) < 1e-6, f"{name}: expected s2={expected_s2} got sa={sa_s2}"
    assert abs(ev_s2 - expected_s2) < 1e-6, f"{name}: expected s2={expected_s2} got eval={ev_s2}"
    assert abs(sa_s3 - expected_s3) < 1e-6, f"{name}: expected s3={expected_s3} got sa={sa_s3}"
    assert abs(ev_s3 - expected_s3) < 1e-6, f"{name}: expected s3={expected_s3} got eval={ev_s3}"


# ──────────────────────────────────────────────────────────────
# Working-day carry-in cases (contract: min_cw=2, max_cw=5)
# ──────────────────────────────────────────────────────────────

def test_CW1_all7_deferred():
    """CW-1: works all 7 days, hist_work=3. Run=10, never ends → deferred. s2=0."""
    # Works d=0..6; off run never triggers; open run at Sunday deferred.
    # Next week will see hist_cw=10 and score it if nurse goes off at d=0.
    _assert_case("CW-1", [1,1,1,1,1,1,1], hist_cw=3, hist_co=0,
                 expected_s2=0, expected_s3=0)


def test_CW2_works0to4_off5to6():
    """CW-2: works d=0..4, off d=5..6, hist_work=3. run=3+5=8 > max=5 → penalty."""
    # run at d=0: 1+3=4, d=1: 5, d=2: 6, d=3: 7, d=4: 8. Transition at d=5.
    # penalty = (8-5)*30 = 90
    _assert_case("CW-2", [1,1,1,1,1,0,0], hist_cw=3, hist_co=0,
                 expected_s2=90, expected_s3=0)


def test_CW3_off0_works1to4_off5to6():
    """CW-3: off d=0, works d=1..4, off d=5..6, hist_work=3. hist NOT carried (d=0 off)."""
    # run starts at d=1 (hist not carried since d=0 is off). run=4, no excess. s2=0.
    _assert_case("CW-3", [0,1,1,1,1,0,0], hist_cw=3, hist_co=0,
                 expected_s2=0, expected_s3=0)


def test_CW4_works0to1_off2to6():
    """CW-4: works d=0..1, off d=2..6, hist_work=4. run=4+2=6 > max=5 → penalty."""
    # penalty = (6-5)*30 = 30
    _assert_case("CW-4", [1,1,0,0,0,0,0], hist_cw=4, hist_co=0,
                 expected_s2=30, expected_s3=0)


def test_CW_min_isolated_single_day():
    """CW-min: works d=0 only, hist_work=0. run=1 < min=2 → penalty=(2-1)*30=30."""
    _assert_case("CW-min", [1,0,0,0,0,0,0], hist_cw=0, hist_co=0,
                 expected_s2=30, expected_s3=0)


# ──────────────────────────────────────────────────────────────
# Off-day carry-in cases (contract: min_co=1, max_co=4)
# ──────────────────────────────────────────────────────────────

def test_CO1_off0to4_works5to6():
    """CO-1: off d=0..4, works d=5..6, hist_off=3. off_run=3+5=8 > max=4 → penalty."""
    # penalty = (8-4)*30 = 120
    _assert_case("CO-1", [0,0,0,0,0,1,1], hist_cw=0, hist_co=3,
                 expected_s2=0, expected_s3=120)


def test_CO2_works0_off1to4_works5to6():
    """CO-2: works d=0, off d=1..4, works d=5..6, hist_off=3. hist NOT carried (d=0 work).

    S2: d=0 is an isolated work day (run=1). d=1 is off → run ends.
        run(1) < min_cw(2) → pen=(2-1)*30=30.
    S3: off run d=1..4 = 4 days. hist_co=3 but d=0 is work so carry-in
        condition (d==0 && hist_cw==0) is FALSE → run starts fresh at d=1.
        run=4 == max_co=4 → no penalty.
    """
    _assert_case("CO-2", [1,0,0,0,0,1,1], hist_cw=0, hist_co=3,
                 expected_s2=30, expected_s3=0)


def test_CO3_off0to2_works3to6():
    """CO-3: off d=0..2, works d=3..6, hist_off=2. off_run=2+3=5 > max=4 → penalty."""
    # penalty = (5-4)*30 = 30
    _assert_case("CO-3", [0,0,0,1,1,1,1], hist_cw=0, hist_co=2,
                 expected_s2=0, expected_s3=30)


def test_Boundary_works0to4_exact_max():
    """Boundary: works d=0..4, off d=5..6, hist_work=0. run=5 == max → no penalty."""
    _assert_case("Boundary", [1,1,1,1,1,0,0], hist_cw=0, hist_co=0,
                 expected_s2=0, expected_s3=0)


# ──────────────────────────────────────────────────────────────
# Cross-week continuation: deferral ≠ exemption
# ──────────────────────────────────────────────────────────────

def test_CW1_crossweek_continuation():
    """CW-1 cross-week: defer≠exempt.

    Week A: all 7 days work, hist_cw=3. Run=10 but never ends → deferred. s2=0.
    Week B: d=0 WORK (continues the run), d=1 off → run ends.
            run = 1 + hist_cw(10) = 11 at d=0. d=1 off → transition.
            run(11) > max_cw(5) → pen=(11-5)*30=180.
    Note: d=0 must be work to trigger carry-in (d==0 && hist_cw>0).
          If d=0 were off, carry-in never fires and the deferred run is silently
          dropped by both SA and evaluator (boundary semantics — see Known Issues).
    """
    # Week A: all 7 days working, hist_cw=3 → run=10 open, deferred
    _assert_case("CW-1-WeekA", [1,1,1,1,1,1,1], hist_cw=3, hist_co=0,
                 expected_s2=0, expected_s3=0)

    # Week B: d=0 work continues run; d=1 off ends it. run=11 > max=5 → pen=180
    _assert_case("CW-1-WeekB", [1,0,0,0,0,0,0], hist_cw=10, hist_co=0,
                 expected_s2=180, expected_s3=0)
