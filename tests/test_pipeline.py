"""Pipeline integration tests for the NRP MILP-Heuristic solver."""

import json
import os
import subprocess
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from outer_milp.utils.inrc2_parser import parse
from outer_milp.utils.validate_schema import validate
from outer_milp.utils.penalty_evaluator import evaluate

INSTANCE_DIR = os.path.join(PROJECT_ROOT, "data/raw_inrc2/testdatasets_json/n005w4")
VALIDATE_SCRIPT = os.path.join(PROJECT_ROOT, "outer_milp/utils/validate_schema.py")


def test_parser_n005w4():
    """Parse n005w4 week 0 and assert 5 nurses with correct demand shape."""
    data = parse(INSTANCE_DIR, week=0, history=0)

    assert data["metadata"]["num_nurses"] == 5, (
        f"Expected 5 nurses, got {data['metadata']['num_nurses']}"
    )

    dm = data["requirements"]["demand_matrix"]
    assert len(dm) == 7, f"demand_matrix must have 7 rows (days), got {len(dm)}"
    assert all(len(row) == 3 for row in dm), (
        "Each row of demand_matrix must have 3 columns (Early, Late, Night)"
    )


def test_schema_valid():
    """Valid problem_exchange data produced by the parser exits validate_schema.py with code 0."""
    data = parse(INSTANCE_DIR, week=0, history=0)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(data, f)
        tmppath = f.name

    try:
        result = subprocess.run(
            [sys.executable, VALIDATE_SCRIPT, tmppath],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Expected exit 0 for valid JSON, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )
    finally:
        os.unlink(tmppath)


def test_schema_invalid():
    """JSON missing 'current_schedule' key causes validate_schema.py to exit with code 1."""
    invalid_data = {
        "metadata": {"num_nurses": 1, "num_days": 7, "num_shift_types": 1},
        "shift_mapping": [{"index": 0, "id": "None"}],
        "nurse_info": [],
        "requirements": {"demand_matrix": [[0]]},
        # deliberately omitting "current_schedule"
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(invalid_data, f)
        tmppath = f.name

    try:
        result = subprocess.run(
            [sys.executable, VALIDATE_SCRIPT, tmppath],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"Expected exit 1 for invalid JSON, got {result.returncode}.\n"
            f"stdout: {result.stdout}"
        )
    finally:
        os.unlink(tmppath)


def test_penalty_zero():
    """All-off schedule (all zeros) produces only coverage penalties; S2/S3/S4/forbidden = 0.

    Why: With no nurse assigned to any shift, consecutive-work runs never form (S2=0),
    off-runs span the entire week and are open-ended at Sunday so they are deferred (S3=0),
    no preferences are triggered (S4=0), and no forbidden successions occur. Coverage demand
    is non-zero for n005w4, so S1 > 0.
    """
    data = parse(INSTANCE_DIR, week=0, history=0)
    num_nurses = data["metadata"]["num_nurses"]
    all_off = [[0] * 7 for _ in range(num_nurses)]

    result = evaluate(all_off, data)

    assert result["S2_consecutive_work"] == 0, (
        f"Expected S2=0 for all-off, got {result['S2_consecutive_work']}"
    )
    assert result["S3_consecutive_off"] == 0, (
        f"Expected S3=0 for all-off, got {result['S3_consecutive_off']}"
    )
    assert result["S4_preferences"] == 0, (
        f"Expected S4=0 for all-off, got {result['S4_preferences']}"
    )
    assert result["forbidden_succession_violations"] == 0, (
        f"Expected 0 forbidden violations for all-off, "
        f"got {result['forbidden_succession_violations']}"
    )
    assert result["S1_coverage"] > 0, (
        "Expected S1>0 for all-off: n005w4 has non-zero minimum demand"
    )
    assert result["total"] == result["S1_coverage"], (
        f"Expected total == S1_coverage for all-off, "
        f"got total={result['total']}, S1={result['S1_coverage']}"
    )


def test_multi_week_runner_n005w4():
    """Run n005w4 weeks 0-3 via multi_week_runner and verify structure and history carry-forward.

    Why: the critical invariant is that H3 (forbidden successions) is always 0
    because the MILP enforces it as a hard constraint. Consecutive-count history
    is propagated from each week's Sunday into the next week's model, so any
    bug in _end_of_week_history would surface as an infeasible solve or a
    non-zero forbidden_succession_violations count in weeks 1-3.
    """
    from outer_milp.utils.multi_week_runner import run

    results = run(INSTANCE_DIR, weeks=[0, 1, 2, 3], history_variant=0, time_limit=30)

    assert len(results) == 4, f"Expected 4 week results, got {len(results)}"

    for i, r in enumerate(results):
        assert r["week"] == i, f"Week slot {i}: expected week index {i}, got {r['week']}"
        assert r["total"] >= 0, f"Week {i}: negative total penalty {r['total']}"
        assert r["S1_coverage"] >= 0, f"Week {i}: negative S1_coverage"
        assert r["S2_consecutive_work"] >= 0, f"Week {i}: negative S2"
        assert r["S3_consecutive_off"] >= 0, f"Week {i}: negative S3"
        assert r["S4_preferences"] >= 0, f"Week {i}: negative S4"
        assert r["forbidden_succession_violations"] == 0, (
            f"Week {i}: MILP must enforce H3 (forbidden successions = 0), "
            f"got {r['forbidden_succession_violations']}"
        )

    accumulated = sum(r["total"] for r in results)
    assert accumulated >= 0, f"Accumulated total must be non-negative, got {accumulated}"
