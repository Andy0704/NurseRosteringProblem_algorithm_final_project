"""NRP MILP-Heuristic Orchestrator (INRC-II).

Coordinates the iterative loop between the Python MILP outer layer and the
C++ heuristic inner layer via file-based JSON exchange (problem_exchange.json).

Usage:
    python outer_milp/main.py --config config.json

Expected config.json fields:
    exchange_path   : path to problem_exchange.json  (default: data/exchange/problem_exchange.json)
    binary_path     : path to compiled nrp_heuristic  (default: inner_heuristic/build/nrp_heuristic)
    max_iterations  : number of MILP-Heuristic cycles (default: 1)
"""

import argparse
import os
import subprocess
import sys

# Ensure outer_milp package root is on sys.path when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from outer_milp.utils.json_handler import load_problem, save_problem
from outer_milp.utils.validate_schema import validate
from outer_milp.models import MilpModel


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NRP MILP-Heuristic Orchestrator (INRC-II)")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the JSON config file specifying runtime settings",
    )
    return parser.parse_args()


def _run_heuristic(binary_path: str, exchange_path: str) -> None:
    result = subprocess.run(
        [binary_path, exchange_path],
        capture_output=True,
        text=True,
        check=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)


def main() -> None:
    args = _parse_args()

    config = load_problem(args.config)
    exchange_path = config.get("exchange_path", "data/exchange/problem_exchange.json")
    binary_path = config.get("binary_path", "inner_heuristic/build/nrp_heuristic")
    max_iterations = config.get("max_iterations", 1)
    fo_num_free = config.get("fo_num_free", 2)
    fo_passes = config.get("fo_passes", 1)
    fo_time_limit = config.get("fo_time_limit", 15)

    data = load_problem(exchange_path)
    validate(data)

    for iteration in range(1, max_iterations + 1):
        print(f"[main] Iteration {iteration}/{max_iterations}")

        # ── MILP full solve ───────────────────────────────────────────────────
        penalty = float("inf")
        try:
            model = MilpModel(data)
            model.build()
            schedule_matrix, penalty = model.solve()
            print(f"[main] MILP penalty: {penalty:.2f}")
            data["current_schedule"] = schedule_matrix
            save_problem(data, exchange_path)
        except NotImplementedError as exc:
            print(f"[STUB] MILP step skipped: {exc}", file=sys.stderr)

        # ── Fix-and-Optimize passes ───────────────────────────────────────────
        N = data["metadata"]["num_nurses"]
        for fo_pass in range(1, fo_passes + 1):
            for i in range(0, N - fo_num_free + 1, fo_num_free):
                free = list(range(i, i + fo_num_free))
                fo_model = MilpModel(data)
                new_sched, new_penalty, accepted = fo_model.fix_and_optimize(
                    free, penalty, time_limit=fo_time_limit
                )
                tag = "ACCEPTED" if accepted else "REJECTED"
                print(
                    f"[F&O]  iter={iteration} pass={fo_pass} "
                    f"free={free} penalty={new_penalty:.2f} [{tag}]"
                )
                if accepted:
                    penalty = new_penalty
                    data["current_schedule"] = new_sched
                    save_problem(data, exchange_path)

        # ── C++ heuristic ─────────────────────────────────────────────────────
        try:
            _run_heuristic(binary_path, exchange_path)
        except FileNotFoundError:
            print(
                f"[STUB] Heuristic binary not found at {binary_path!r} — skipping",
                file=sys.stderr,
            )
        except subprocess.CalledProcessError as exc:
            print(
                f"[main] Heuristic exited with code {exc.returncode}: {exc.stderr}",
                file=sys.stderr,
            )
            sys.exit(exc.returncode)

        data = load_problem(exchange_path)

    print("[main] Done.")


if __name__ == "__main__":
    main()
