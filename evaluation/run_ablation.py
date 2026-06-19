"""Mode-gated MILP / Fix-and-Optimize / SA ablation runner for INRC-II instances.

Imports existing pipeline helpers only (parse, MilpModel, F&O, SA subprocess
wrapper) — does not reimplement any of them. Each mode runs a strict
superset of the lower mode's work on the same MILP seed:
    milp -> MILP only
    fo   -> MILP, then Fix-and-Optimize
    full -> MILP, then F&O, then C++ SA

Run from NRP_Claude_Agent/:
    python3 evaluation/run_ablation.py --dataset n005w4 --history 0 \
        --weeks 0,1,2,3 --mode full --output results/ablation_<ts>.json
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from outer_milp.models.milp_model import MilpModel
from outer_milp.utils.inrc2_parser import parse
from outer_milp.utils.json_handler import save_problem
from outer_milp.utils.penalty_evaluator import evaluate, evaluate_global_s6_s7
from outer_milp.utils.multi_week_runner import _end_of_week_history
from run_4week_full_pipeline import _run_fo, _run_sa

MILP_TIME = 30  # CBC time limit per week (seconds); matches run_4week_full_pipeline.py
EXCHANGE = "data/exchange/ablation_bench.json"  # dedicated temp file, not pipeline_bench.json
DATASET_ROOTS = ("data/raw_inrc2/testdatasets_json", "data/raw_inrc2/datasets_json")


def _resolve_instance_dir(dataset: str) -> str:
    for root in DATASET_ROOTS:
        candidate = os.path.join(root, dataset)
        if os.path.isdir(candidate):
            return candidate
    raise FileNotFoundError(
        f"run_ablation: dataset {dataset!r} not found under {DATASET_ROOTS}"
    )


def _git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def run_instance(dataset: str, weeks: list, history: int, mode: str) -> tuple:
    """Run one instance through the mode-gated pipeline, week by week.

    Returns (per_week: list[dict], global_result: dict).
    """
    instance_dir = _resolve_instance_dir(dataset)
    per_week = []
    weekly_schedules = []
    nurse_info_w0 = None
    contracts = None
    carry = None

    for seq_idx, week_idx in enumerate(weeks):
        data = parse(instance_dir, week=week_idx, history=history)
        if seq_idx == 0:
            nurse_info_w0 = data["nurse_info"]
            contracts = data.get("contracts", {})
        if carry is not None:
            for n_idx in range(len(data["nurse_info"])):
                data["nurse_info"][n_idx]["history"] = carry[n_idx]["history"]

        is_final_week = (seq_idx == len(weeks) - 1)
        model = MilpModel(data)
        model.build(is_final_week=is_final_week, cur_week=seq_idx + 1,
                    num_weeks=len(weeks))

        t0 = time.time()
        schedule, milp_obj = model.solve(time_limit=MILP_TIME)
        wall_milp = time.time() - t0
        data["current_schedule"] = schedule

        wall_fo = 0.0
        wall_sa = 0.0

        if mode in ("fo", "full"):
            t1 = time.time()
            schedule, _, _ = _run_fo(data, milp_obj)
            wall_fo = time.time() - t1
            data["current_schedule"] = schedule

        if mode == "full":
            t2 = time.time()
            save_problem(data, EXCHANGE)
            sa_out = _run_sa(EXCHANGE)
            schedule = sa_out["current_schedule"]
            data["current_schedule"] = schedule
            wall_sa = time.time() - t2

        weekly_schedules.append(schedule)
        penalties = evaluate(schedule, data)
        per_week.append({
            "week_idx": week_idx,
            "S1": penalties["S1_coverage"],
            "S2": penalties["S2_consecutive_work"],
            "S3": penalties["S3_consecutive_off"],
            "S4": penalties["S4_preferences"],
            "forbidden": penalties["forbidden_succession_violations"],
            "total": penalties["total"],
            "wall_clock_milp": round(wall_milp, 4),
            "wall_clock_fo": round(wall_fo, 4),
            "wall_clock_sa": round(wall_sa, 4),
        })

        carry = _end_of_week_history(schedule, data["nurse_info"])

    global_result = evaluate_global_s6_s7(weekly_schedules, nurse_info_w0, contracts)
    return per_week, global_result


def build_record(dataset: str, history: int, weeks: list, mode: str,
                  per_week: list, global_result: dict,
                  wall_clock_total: float) -> dict:
    total_inrc2_cost = sum(w["total"] for w in per_week) + global_result["total_global"]
    return {
        "dataset": dataset,
        "history_id": history,
        "week_sequence": weeks,
        "instance_id": f"{dataset}_{history}_{'-'.join(str(w) for w in weeks)}",
        "mode": mode,
        "git_sha": _git_sha(),
        "per_week": per_week,
        "global_s6": global_result["S6_total_assignments"],
        "global_s7": global_result["S7_total_weekends"],
        "total_inrc2_cost": total_inrc2_cost,
        "h2_clean_all_weeks": all(w["S1"] == 0 for w in per_week),
        "h3_clean_all_weeks": all(w["forbidden"] == 0 for w in per_week),
        "wall_clock_total_seconds": round(wall_clock_total, 4),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def _append_record(output_path: str, record: dict) -> None:
    """Append one record to a list-of-records JSON file, creating it if absent."""
    records = []
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        records = existing if isinstance(existing, list) else [existing]
    records.append(record)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def _parse_weeks(s: str) -> list:
    return [int(tok) for tok in s.split(",")]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Mode-gated MILP / Fix-and-Optimize / SA ablation runner for "
                     "INRC-II instances."
    )
    p.add_argument("--dataset", required=True,
                   help="Dataset name, e.g. n005w4 (testdatasets_json or datasets_json)")
    p.add_argument("--history", type=int, default=0,
                   help="H0 history variant index used for week 0 (default: 0)")
    p.add_argument("--weeks", required=True, type=_parse_weeks,
                   help="Comma-separated week indices in order, e.g. 0,1,2,3")
    p.add_argument("--mode", required=True, choices=["milp", "fo", "full"])
    p.add_argument("--output", required=True,
                   help="Path to output JSON file (list-of-records; appended to)")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    t0 = time.time()
    per_week, global_result = run_instance(
        args.dataset, args.weeks, args.history, args.mode)
    wall_clock_total = time.time() - t0
    record = build_record(args.dataset, args.history, args.weeks, args.mode,
                           per_week, global_result, wall_clock_total)
    _append_record(args.output, record)
    print(f"[run_ablation] {record['instance_id']} mode={args.mode} "
          f"total_inrc2_cost={record['total_inrc2_cost']} "
          f"h2_clean={record['h2_clean_all_weeks']} "
          f"h3_clean={record['h3_clean_all_weeks']} "
          f"wall_clock={wall_clock_total:.1f}s -> {args.output}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, KeyError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
