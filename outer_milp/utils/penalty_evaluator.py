"""INRC-II soft-constraint penalty evaluator for a single planning week.

Assumptions / complexity:
  - O(N_nurses * N_days * N_skills) for coverage check
  - O(N_nurses * N_days) for consecutive-run and forbidden-succession checks
  - Shift index 0 is always Off; work shifts are 1..num_shift_types-1
  - Only runs that END before day 6 (Sunday) are penalized — open-ended runs
    at the week boundary are deferred to the next week's evaluation.

Usage (CLI):
    python outer_milp/utils/penalty_evaluator.py <path/to/problem_exchange.json>
"""

import argparse
import json
import sys

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_DAY_TO_IDX = {d: i for i, d in enumerate(_DAY_NAMES)}

_W_COVERAGE = 30
# Ceschia 2019 p.176 §2.5.1: S2 CS2c/d (any-shift consec work days) = 30,
# S3 (consec days off) = 30. Both use this constant.
# NOTE: S2 CS2a/b (same-shift-type consec, spec weight 15) is not yet
# implemented; when added in W-4 it will need a separate _W_CONSEC_SAME = 15.
_W_CONSEC = 30
_W_PREF = 10


def _count_backward(row: list, end_day: int, working: bool) -> int:
    """Count consecutive days ending at end_day where the shift matches the working flag."""
    count = 0
    for d in range(end_day, -1, -1):
        is_work = row[d] > 0
        if is_work == working:
            count += 1
        else:
            break
    return count


def _compute_s1(schedule: list, nurse_info: list, requirements: dict,
                skills: list, shift_mapping: list) -> int:
    demand_by_skill = requirements.get("demand_by_skill", {})
    num_nurses = len(nurse_info)
    num_work_shifts = len(shift_mapping) - 1  # exclude Off

    nurse_skill_sets = [set(n["skills"]) for n in nurse_info]
    s1 = 0

    if demand_by_skill and skills:
        for skill in skills:
            skill_demand = demand_by_skill[skill]  # [7][num_work_shifts]
            for day in range(7):
                for shift_rel in range(num_work_shifts):
                    demand = skill_demand[day][shift_rel]
                    if demand <= 0:
                        continue
                    shift_abs = shift_rel + 1
                    assigned = sum(
                        1 for n in range(num_nurses)
                        if schedule[n][day] == shift_abs and skill in nurse_skill_sets[n]
                    )
                    s1 += max(0, demand - assigned) * _W_COVERAGE
    else:
        demand_matrix = requirements["demand_matrix"]  # [day][shift_rel]
        for day in range(7):
            for shift_rel in range(num_work_shifts):
                demand = demand_matrix[day][shift_rel]
                if demand <= 0:
                    continue
                shift_abs = shift_rel + 1
                assigned = sum(
                    1 for n in range(num_nurses)
                    if schedule[n][day] == shift_abs
                )
                s1 += max(0, demand - assigned) * _W_COVERAGE

    return s1


def _compute_s2_s3(schedule: list, nurse_info: list, contracts: dict) -> tuple:
    s2 = 0
    s3 = 0

    for n_idx, nurse in enumerate(nurse_info):
        row = schedule[n_idx]
        hist = nurse["history"]
        contract = contracts.get(nurse["contract_id"], {})

        min_cw = contract.get("minimumNumberOfConsecutiveWorkingDays", 0)
        max_cw = contract.get("maximumNumberOfConsecutiveWorkingDays", 999)
        min_co = contract.get("minimumNumberOfConsecutiveDaysOff", 0)
        max_co = contract.get("maximumNumberOfConsecutiveDaysOff", 999)

        prior_work = hist.get("consecutive_working_days", 0)
        prior_off = hist.get("consecutive_days_off", 0)

        for d in range(6):  # day 6 (Sunday) is never a run-end
            today_work = row[d] > 0
            next_work = row[d + 1] > 0

            if today_work and not next_work:
                # Working run ends at day d
                run_len = _count_backward(row, d, working=True)
                if run_len == d + 1:
                    run_len += prior_work
                if run_len < min_cw:
                    s2 += (min_cw - run_len) * _W_CONSEC
                elif run_len > max_cw:
                    s2 += (run_len - max_cw) * _W_CONSEC

            elif not today_work and next_work:
                # Off run ends at day d
                run_len = _count_backward(row, d, working=False)
                if run_len == d + 1:
                    run_len += prior_off
                if run_len < min_co:
                    s3 += (min_co - run_len) * _W_CONSEC
                elif run_len > max_co:
                    s3 += (run_len - max_co) * _W_CONSEC

    return s2, s3


def _compute_s4(schedule: list, nurse_info: list,
                shift_off_requests: list, shift_mapping: list) -> int:
    nurse_id_to_idx = {n["id"]: n["index"] for n in nurse_info}
    shift_id_to_abs = {sm["id"]: sm["index"] for sm in shift_mapping}
    s4 = 0

    for req in shift_off_requests:
        n_idx = nurse_id_to_idx.get(req["nurse"])
        if n_idx is None:
            continue
        day_idx = _DAY_TO_IDX.get(req.get("day", ""), -1)
        if day_idx < 0:
            continue
        assigned = schedule[n_idx][day_idx]
        shift_type = req.get("shiftType", "Any")
        if shift_type == "Any":
            if assigned != 0:
                s4 += _W_PREF
        else:
            if assigned == shift_id_to_abs.get(shift_type, -1):
                s4 += _W_PREF

    return s4


def _compute_forbidden_successions(schedule: list, nurse_info: list,
                                   shift_mapping: list, forbidden: dict) -> int:
    shift_id_to_abs = {sm["id"]: sm["index"] for sm in shift_mapping}
    shift_abs_to_id = {sm["index"]: sm["id"] for sm in shift_mapping}

    # Pre-build index-based forbidden lookup
    forbidden_next = {}
    for pred_id, succ_ids in forbidden.items():
        pred_abs = shift_id_to_abs.get(pred_id)
        if pred_abs is not None:
            forbidden_next[pred_abs] = {shift_id_to_abs[s] for s in succ_ids
                                        if s in shift_id_to_abs}

    count = 0
    for n_idx, nurse in enumerate(nurse_info):
        row = schedule[n_idx]
        last_abs = nurse["history"].get("last_shift_index", 0)

        # Cross-week boundary: history last shift → week day 0
        if last_abs > 0 and row[0] > 0:
            if row[0] in forbidden_next.get(last_abs, set()):
                count += 1

        # Within-week: day d → day d+1
        for d in range(6):
            if row[d] > 0 and row[d + 1] > 0:
                if row[d + 1] in forbidden_next.get(row[d], set()):
                    count += 1

    return count


def evaluate(schedule_matrix: list, problem_data: dict) -> dict:
    """Compute INRC-II soft-constraint penalties for a single-week schedule.

    Args:
        schedule_matrix: 2D list [nurse_index][day_index] -> shift_index (0 = Off)
        problem_data: dict conforming to problem_exchange.json schema

    Returns:
        dict with keys:
          total, S1_coverage, S2_consecutive_work, S3_consecutive_off,
          S4_preferences, forbidden_succession_violations
    """
    nurse_info = problem_data["nurse_info"]
    contracts = problem_data.get("contracts", {})
    shift_mapping = problem_data["shift_mapping"]
    requirements = problem_data["requirements"]
    skills = problem_data.get("skills", [])
    shift_off_requests = problem_data.get("shift_off_requests", [])
    forbidden = (
        problem_data.get("shift_type_constraints", {})
        .get("forbidden_successions", {})
    )

    s1 = _compute_s1(schedule_matrix, nurse_info, requirements, skills, shift_mapping)
    s2, s3 = _compute_s2_s3(schedule_matrix, nurse_info, contracts)
    s4 = _compute_s4(schedule_matrix, nurse_info, shift_off_requests, shift_mapping)
    fsv = _compute_forbidden_successions(schedule_matrix, nurse_info, shift_mapping, forbidden)

    return {
        "total": s1 + s2 + s3 + s4,
        "S1_coverage": s1,
        "S2_consecutive_work": s2,
        "S3_consecutive_off": s3,
        "S4_preferences": s4,
        "forbidden_succession_violations": fsv,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate INRC-II soft-constraint penalties for current_schedule."
    )
    parser.add_argument("filepath", help="Path to the problem_exchange.json file")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    try:
        with open(args.filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = evaluate(data["current_schedule"], data)
        print(json.dumps(result, indent=2))
        sys.exit(0)
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
