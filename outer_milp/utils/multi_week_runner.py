"""Multi-week sequential MILP runner for INRC-II nurse rostering.

Runs the MILP solver across n consecutive weeks, carrying end-of-week nurse
history (last_shift_index, consecutive working/off day counts, cumulative
assignments and working weekends) forward between weeks.

Week 0 uses the static H0-{id}-{history}.json file for initial history.
Weeks 1+ inject history derived from the prior week's solved schedule.

Usage:
    python3 outer_milp/utils/multi_week_runner.py \
        --instance data/raw_inrc2/testdatasets_json/n005w4 \
        [--weeks 0 1 2 3] \
        [--history 0] \
        [--time-limit 30]

Complexity: O(W * MILP_solve_time) where W = number of weeks.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from outer_milp.models.milp_model import MilpModel
from outer_milp.utils.inrc2_parser import parse
from outer_milp.utils.penalty_evaluator import evaluate, evaluate_global_s6_s7


def _end_of_week_history(schedule_matrix: list, nurse_info: list) -> list:
    """Derive carry-forward history from a solved week's schedule.

    For each nurse:
      - last_shift_index: Sunday (day 6) shift assignment
      - consecutive_working_days: trailing working-day run ending at Sunday;
        if the entire week was worked, extends backward into the prior run
      - consecutive_days_off: trailing off-day run ending at Sunday;
        if the entire week was off, extends backward into the prior run
      - num_assignments: cumulative (prior + this week's working days)
      - num_working_weekends: cumulative (prior + 1 if Sat or Sun worked)

    Returns a new list of nurse dicts with updated history fields.
    """
    updated = []
    for n_idx, nurse in enumerate(nurse_info):
        row = schedule_matrix[n_idx]
        hist = nurse["history"]

        cons_work = 0
        for d in range(6, -1, -1):
            if row[d] > 0:
                cons_work += 1
            else:
                break
        if cons_work == 7:
            cons_work += hist.get("consecutive_working_days", 0)

        cons_off = 0
        for d in range(6, -1, -1):
            if row[d] == 0:
                cons_off += 1
            else:
                break
        if cons_off == 7:
            cons_off += hist.get("consecutive_days_off", 0)

        this_week_assigns = sum(1 for d in range(7) if row[d] > 0)
        worked_weekend = 1 if (row[5] > 0 or row[6] > 0) else 0

        updated.append({
            **nurse,
            "history": {
                "consecutive_working_days": cons_work,
                "consecutive_days_off": cons_off,
                "last_shift_index": row[6],
                "num_assignments": hist.get("num_assignments", 0) + this_week_assigns,
                "num_working_weekends": hist.get("num_working_weekends", 0) + worked_weekend,
                "num_consecutive_shift_assignments": 0,
            },
        })
    return updated


def run(instance_dir: str, weeks: list, history_variant: int,
        time_limit: int = 30) -> list:
    """Solve each week sequentially, carrying nurse history forward.

    Args:
        instance_dir:    path to the INRC-II instance folder
        weeks:           ordered list of week indices to solve
        history_variant: H0 file index used for the first week only
        time_limit:      CBC solver time limit per week (seconds)

    Returns:
        list of dicts, one per week, with keys:
          week, S1_coverage, S2_consecutive_work, S3_consecutive_off,
          S4_preferences, forbidden_succession_violations, total
    """
    if not weeks:
        raise ValueError("multi_week_runner.run: 'weeks' list must not be empty")

    results = []
    carry_nurse_info = None

    for seq_idx, week_idx in enumerate(weeks):
        data = parse(instance_dir, week=week_idx, history=history_variant)

        if carry_nurse_info is not None:
            for n_idx in range(len(data["nurse_info"])):
                data["nurse_info"][n_idx]["history"] = carry_nurse_info[n_idx]["history"]

        model = MilpModel(data)
        model.build()
        schedule_matrix, _ = model.solve(time_limit=time_limit)

        penalties = evaluate(schedule_matrix, data)
        results.append({"week": week_idx, **penalties})

        carry_nurse_info = _end_of_week_history(schedule_matrix, data["nurse_info"])

    return results


def run_with_global(instance_dir: str, weeks: list, history_variant: int,
                    time_limit: int = 30) -> tuple:
    """Like run(), but also computes end-of-horizon global S6/S7.

    Returns:
        (results, global_result) where results is the same list as run()
        and global_result is from evaluate_global_s6_s7().
    """
    if not weeks:
        raise ValueError("run_with_global: 'weeks' list must not be empty")

    results = []
    weekly_schedules = []
    nurse_info_w0 = None
    contracts = None
    carry_nurse_info = None

    for seq_idx, week_idx in enumerate(weeks):
        data = parse(instance_dir, week=week_idx, history=history_variant)

        if seq_idx == 0:
            nurse_info_w0 = data["nurse_info"]
            contracts = data.get("contracts", {})

        if carry_nurse_info is not None:
            for n_idx in range(len(data["nurse_info"])):
                data["nurse_info"][n_idx]["history"] = carry_nurse_info[n_idx]["history"]

        model = MilpModel(data)
        model.build()
        schedule_matrix, _ = model.solve(time_limit=time_limit)

        weekly_schedules.append(schedule_matrix)
        penalties = evaluate(schedule_matrix, data)
        results.append({"week": week_idx, **penalties})

        carry_nurse_info = _end_of_week_history(schedule_matrix, data["nurse_info"])

    global_result = evaluate_global_s6_s7(weekly_schedules, nurse_info_w0, contracts)
    return results, global_result


def _report(results: list) -> None:
    """Print a per-week penalty breakdown table with accumulated total."""
    col = "{:>6} | {:>8} | {:>9} | {:>8} | {:>8} | {:>7} | {:>7}"
    header = col.format("Week", "S1_cov", "S2_cwork", "S3_coff", "S4_pref", "Forbid", "Total")
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    accumulated = 0
    for r in results:
        print(col.format(
            r["week"],
            r["S1_coverage"],
            r["S2_consecutive_work"],
            r["S3_consecutive_off"],
            r["S4_preferences"],
            r["forbidden_succession_violations"],
            r["total"],
        ))
        accumulated += r["total"]
    print(sep)
    print(col.format("TOTAL", "", "", "", "", "", accumulated))
    print(sep)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run MILP solver across multiple INRC-II weeks with history carry-forward."
    )
    parser.add_argument(
        "--instance",
        required=True,
        help="Path to the instance directory (Sc-*.json, WD-*.json, H0-*.json)",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        nargs="+",
        default=[0, 1, 2, 3],
        help="Week indices to run in order (default: 0 1 2 3)",
    )
    parser.add_argument(
        "--history",
        type=int,
        default=0,
        help="Initial H0 history variant index (default: 0)",
    )
    parser.add_argument(
        "--time-limit",
        type=int,
        default=30,
        help="CBC solver time limit per week in seconds (default: 30)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    try:
        results, global_result = run_with_global(
            args.instance, args.weeks, args.history, args.time_limit)
        _report(results)
        print(f"\nGlobal (end-of-horizon, Ceschia 2019 §2.5.2):")
        print(f"  S6_total_assignments : {global_result['S6_total_assignments']}")
        print(f"  S7_total_weekends    : {global_result['S7_total_weekends']}")
        print(f"  total_global         : {global_result['total_global']}")
    except (FileNotFoundError, ValueError, KeyError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
