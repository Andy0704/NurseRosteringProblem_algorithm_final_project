"""INRC-II JSON → problem_exchange.json converter.

Reads the three official INRC-II files for a single planning week:
  Sc-{id}.json       — scenario (nurses, contracts, shift types, skills)
  WD-{id}-{week}.json — week data (requirements, shift-off requests)
  H0-{id}-{hist}.json — nurse history (consecutive counters, last shift)

Produces a problem_exchange.json conforming to our exchange schema.

Usage:
    python outer_milp/utils/inrc2_parser.py \
        --instance data/raw_inrc2/testdatasets_json/n005w4 \
        --week 0 \
        [--history 0] \
        --output data/exchange/problem_exchange.json
"""

import argparse
import glob
import json
import os
import sys

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _load(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"inrc2_parser: file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse(instance_dir: str, week: int, history: int) -> dict:
    """Convert one INRC-II week into a problem_exchange dict.

    Assumptions / complexity:
      - O(N_nurses * N_days) for schedule init
      - O(N_requirements * N_days) for demand matrix build
      - All arrays are 0-indexed; Off shift is always index 0
    """
    # --- locate Scenario file and derive instance ID ---
    sc_glob = glob.glob(os.path.join(instance_dir, "Sc-*.json"))
    if not sc_glob:
        raise FileNotFoundError(
            f"inrc2_parser: no Sc-*.json found in {instance_dir}"
        )
    sc_path = sc_glob[0]
    instance_id = os.path.basename(sc_path)[3:-5]  # strip "Sc-" prefix and ".json"

    wd_path = os.path.join(instance_dir, f"WD-{instance_id}-{week}.json")
    h0_path = os.path.join(instance_dir, f"H0-{instance_id}-{history}.json")

    sc = _load(sc_path)
    wd = _load(wd_path)
    h0 = _load(h0_path)

    # --- shift mapping: Off=0, then INRC-II shiftTypes in order ---
    shift_index = {"None": 0}
    shift_mapping = [{"index": 0, "id": "None", "is": "Off"}]
    for i, st in enumerate(sc["shiftTypes"], start=1):
        shift_index[st["id"]] = i
        shift_mapping.append({
            "index": i,
            "id": st["id"],
            "name": st["id"],
            "min_consecutive": st["minimumNumberOfConsecutiveAssignments"],
            "max_consecutive": st["maximumNumberOfConsecutiveAssignments"],
        })
    num_shift_types = len(shift_mapping)          # includes Off
    num_work_shifts = num_shift_types - 1          # excludes Off

    # --- nurses and index ---
    nurses = sc["nurses"]
    num_nurses = len(nurses)
    nurse_order = {n["id"]: i for i, n in enumerate(nurses)}

    # --- history lookup ---
    history_map = {h["nurse"]: h for h in h0["nurseHistory"]}

    # --- nurse_info ---
    nurse_info = []
    for i, nurse in enumerate(nurses):
        nid = nurse["id"]
        if nid not in history_map:
            raise ValueError(
                f"inrc2_parser: nurse '{nid}' in Scenario not found in history file"
            )
        hist = history_map[nid]
        last_shift_str = hist.get("lastAssignedShiftType", "None")
        nurse_info.append({
            "index": i,
            "id": nid,
            "contract_id": nurse["contract"],
            "skills": nurse["skills"],
            "history": {
                "consecutive_working_days": hist["numberOfConsecutiveWorkingDays"],
                "consecutive_days_off": hist["numberOfConsecutiveDaysOff"],
                "last_shift_index": shift_index.get(last_shift_str, 0),
                "num_assignments": hist["numberOfAssignments"],
                "num_working_weekends": hist["numberOfWorkingWeekends"],
                "num_consecutive_shift_assignments": hist.get("numberOfConsecutiveAssignments", 0),
            },
        })

    # --- demand matrices ---
    # demand_by_skill[skill][day][shift_rel_idx (0-based in non-Off shifts)] = minimum
    skills = sc["skills"]
    demand_by_skill = {s: [[0] * num_work_shifts for _ in range(7)] for s in skills}
    optimal_by_skill = {s: [[0] * num_work_shifts for _ in range(7)] for s in skills}

    for req in wd.get("requirements", []):
        st_id = req["shiftType"]
        skill_id = req["skill"]
        if st_id not in shift_index or skill_id not in demand_by_skill:
            continue
        shift_rel = shift_index[st_id] - 1  # 0-indexed within work shifts
        for day_idx, day_name in enumerate(_DAY_NAMES):
            entry = req.get(f"requirementOn{day_name}", {})
            demand_by_skill[skill_id][day_idx][shift_rel] = entry.get("minimum", 0)
            optimal_by_skill[skill_id][day_idx][shift_rel] = entry.get("optimal", 0)

    # Aggregate 2D demand_matrix = sum of minimums across all skills [day][shift_rel]
    demand_matrix = [
        [sum(demand_by_skill[s][d][sr] for s in skills) for sr in range(num_work_shifts)]
        for d in range(7)
    ]

    # --- contracts keyed by contract ID ---
    contracts = {c["id"]: c for c in sc["contracts"]}

    # --- forbidden shift successions ---
    forbidden = {
        fs["precedingShiftType"]: fs["succeedingShiftTypes"]
        for fs in sc.get("forbiddenShiftTypeSuccessions", [])
    }

    # --- blank initial schedule (all Off) ---
    current_schedule = [[0] * 7 for _ in range(num_nurses)]

    return {
        "metadata": {
            "instance_id": instance_id,
            "num_nurses": num_nurses,
            "num_days": 7,
            "num_shift_types": num_shift_types,
            "week": week,
            "history_variant": history,
        },
        "shift_mapping": shift_mapping,
        "skills": skills,
        "contracts": contracts,
        "shift_type_constraints": {
            "forbidden_successions": forbidden,
        },
        "nurse_info": nurse_info,
        "requirements": {
            "demand_matrix": demand_matrix,
            "demand_by_skill": demand_by_skill,
            "optimal_by_skill": optimal_by_skill,
        },
        "shift_off_requests": wd.get("shiftOffRequests", []),
        "current_schedule": current_schedule,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert INRC-II JSON files to problem_exchange.json format."
    )
    parser.add_argument(
        "--instance",
        required=True,
        help="Path to the instance folder containing Sc-*.json, WD-*.json, H0-*.json",
    )
    parser.add_argument(
        "--week",
        type=int,
        default=0,
        help="Week index to load (selects WD-{id}-{week}.json, default: 0)",
    )
    parser.add_argument(
        "--history",
        type=int,
        default=0,
        help="History variant index (selects H0-{id}-{history}.json, default: 0)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for the problem_exchange.json file",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    try:
        data = parse(args.instance, args.week, args.history)
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[inrc2_parser] Written: {args.output}", file=sys.stderr)
        print(
            f"  Nurses: {data['metadata']['num_nurses']}, "
            f"Shifts: {data['metadata']['num_shift_types']}, "
            f"Week: {args.week}, History: {args.history}"
        )
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
