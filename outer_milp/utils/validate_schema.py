"""CLI-callable schema validator for problem_exchange.json (INRC-II exchange format).

Usage:
    python outer_milp/utils/validate_schema.py <path/to/problem_exchange.json>

Exits 0 and prints VALID on success; exits 1 and prints the failure reason to stderr.
"""

import argparse
import json
import sys


def validate(data: dict) -> bool:
    """Validate a problem_exchange dict against the INRC-II exchange schema.

    Raises ValueError with a descriptive message on the first failed check.
    Returns True if the data is valid.
    """
    required_top = {"metadata", "shift_mapping", "nurse_info", "requirements", "current_schedule"}
    missing = required_top - data.keys()
    if missing:
        raise ValueError(f"Missing top-level keys: {sorted(missing)}")

    # --- metadata ---
    meta = data["metadata"]
    for field in ("num_nurses", "num_days", "num_shift_types"):
        if field not in meta:
            raise ValueError(f"metadata missing field: {field}")
        if not isinstance(meta[field], int) or meta[field] <= 0:
            raise ValueError(
                f"metadata.{field} must be a positive integer, got: {meta[field]!r}"
            )

    num_nurses = meta["num_nurses"]
    num_days = meta["num_days"]
    num_shifts = meta["num_shift_types"]

    # --- shift_mapping ---
    shift_map = data["shift_mapping"]
    if not isinstance(shift_map, list) or len(shift_map) != num_shifts:
        raise ValueError(
            f"shift_mapping must be a list of length num_shift_types={num_shifts}, "
            f"got: {len(shift_map) if isinstance(shift_map, list) else type(shift_map).__name__}"
        )
    for i, entry in enumerate(shift_map):
        for field in ("index", "id"):
            if field not in entry:
                raise ValueError(f"shift_mapping[{i}] missing field: {field}")

    # --- nurse_info ---
    nurse_info = data["nurse_info"]
    if not isinstance(nurse_info, list):
        raise ValueError("nurse_info must be a list")
    for i, nurse in enumerate(nurse_info):
        for field in ("index", "id", "contract_id", "history"):
            if field not in nurse:
                raise ValueError(f"nurse_info[{i}] missing field: {field}")
        hist = nurse["history"]
        for hfield in ("consecutive_working_days", "consecutive_days_off", "last_shift_index"):
            if hfield not in hist:
                raise ValueError(f"nurse_info[{i}].history missing field: {hfield}")
            if not isinstance(hist[hfield], int):
                raise ValueError(
                    f"nurse_info[{i}].history.{hfield} must be int, "
                    f"got: {type(hist[hfield]).__name__}"
                )

    # --- requirements ---
    demand = data["requirements"].get("demand_matrix")
    if not isinstance(demand, list) or len(demand) == 0:
        raise ValueError("requirements.demand_matrix must be a non-empty list")
    if not all(isinstance(row, list) for row in demand):
        raise ValueError("requirements.demand_matrix must be a list of lists")

    # --- current_schedule ---
    # Row count may be less than num_nurses for partial datasets; each present row
    # must have exactly num_days columns with shift indices in [0, num_shift_types).
    schedule = data["current_schedule"]
    if not isinstance(schedule, list) or len(schedule) == 0:
        raise ValueError("current_schedule must be a non-empty list")
    for i, row in enumerate(schedule):
        if not isinstance(row, list) or len(row) != num_days:
            raise ValueError(
                f"current_schedule[{i}] must be a list of length num_days={num_days}, "
                f"got: {row!r}"
            )
        for j, val in enumerate(row):
            if not isinstance(val, int) or not (0 <= val < num_shifts):
                raise ValueError(
                    f"current_schedule[{i}][{j}]={val!r} out of valid range [0, {num_shifts})"
                )

    return True


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a problem_exchange.json file against the INRC-II exchange schema."
    )
    parser.add_argument("filepath", help="Path to the problem_exchange.json file to validate")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    try:
        with open(args.filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        validate(data)
        print("VALID")
        sys.exit(0)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        sys.exit(1)
