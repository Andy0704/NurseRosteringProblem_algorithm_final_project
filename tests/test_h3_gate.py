"""Segment H3-gate: SA must never return an H3-infeasible best_sched.

WHY (Rule 9): the 2026-06-15 trajectory diagnostic
(references/h3_leak_diagnostic_n012w8.md) showed SA was silently producing
forbidden_succession_violations=15 on n012w8 W3 because the best_sched gate
only checked totalH2Units==0, with forbidden_hard excluded from
nurseCostFull.total (Change D) and invisible to all three delta functions.
This test guards against regression of the M_FORBID + best_sched H3-gate fix.
"""

import json
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from outer_milp.models.milp_model import MilpModel
from outer_milp.utils.inrc2_parser import parse
from outer_milp.utils.json_handler import save_problem
from outer_milp.utils.penalty_evaluator import evaluate
from outer_milp.utils.multi_week_runner import _end_of_week_history
from run_4week_full_pipeline import _run_fo, _run_sa, MILP_TIME, EXCHANGE

BINARY   = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "inner_heuristic", "build", "nrp_heuristic"))
INSTANCE = "data/raw_inrc2/testdatasets_json/n012w8"


def _run_eval_only(data: dict, schedule: list) -> dict:
    d = dict(data)
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


def test_sa_h3_clean_on_n012w8_w3():
    """SA's best_sched on n012w8 W3 must have forbidden_succession_violations==0.

    Setup mirrors references/h3_leak_diagnostic_n012w8.md: MILP-solve weeks
    0-2 with history carry-in, then run week 3 (the documented 15-violation
    case) through MILP -> F&O -> SA.
    """
    carry = None
    data = None
    for week_idx in range(4):
        data = parse(INSTANCE, week=week_idx, history=0)
        if carry is not None:
            for n_idx in range(len(data["nurse_info"])):
                data["nurse_info"][n_idx]["history"] = carry[n_idx]["history"]

        model = MilpModel(data)
        model.build()
        schedule, milp_obj = model.solve(time_limit=MILP_TIME)
        data["current_schedule"] = schedule

        schedule, post_fo_obj, _ = _run_fo(data, milp_obj)
        data["current_schedule"] = schedule

        if week_idx == 3:
            break
        carry = _end_of_week_history(data["current_schedule"], data["nurse_info"])

    # MILP+F&O seed must already be H3-clean (confirmed in the diagnostic).
    seed_forbidden = evaluate(data["current_schedule"], data)["forbidden_succession_violations"]
    assert seed_forbidden == 0, (
        f"MILP+F&O seed for n012w8 W3 has {seed_forbidden} H3 violations "
        f"(expected 0 per h3_leak_diagnostic_n012w8.md Step 2)")

    save_problem(data, EXCHANGE)
    sa_out = _run_sa(EXCHANGE)
    best_sched = sa_out["current_schedule"]

    # 1. best_sched must be H3-feasible (the actual gate fix).
    sa_forbidden = evaluate(best_sched, data)["forbidden_succession_violations"]
    assert sa_forbidden == 0, (
        f"best_sched still violates H3: forbidden_succession_violations={sa_forbidden}")

    # 2. final_cost must be M_COVER-/M_FORBID-free (Rule 8: per-item identity,
    #    no proxy/ratio comparison). best_sched is H2-/H3-clean here, so
    #    runEvalOnly's total must equal final_cost exactly to within the
    #    documented small non-negative S5 design gap (see
    #    test_sa_h2_repair_from_infeasible_seed for the analogous H2 check).
    final_cost = sa_out["metadata"]["final_cost"]
    sa_eval = _run_eval_only(data, best_sched)
    assert sa_eval["forbidden_violations"] == 0, (
        f"runEvalOnly reports forbidden_violations="
        f"{sa_eval['forbidden_violations']} on best_sched")
    gap = final_cost - sa_eval["total"]
    assert 0 <= gap < 200, (
        f"final_cost - eval_total={gap} outside expected S5-gap range "
        f"(final_cost={final_cost}, eval_total={sa_eval['total']})")
