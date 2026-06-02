"""Baseline vs Proposed (F&O) comparison on n030w4, 4 weeks.

Baseline : MILP-only per-week solve (multi_week_runner.run)
Proposed : MILP + Fix-and-Optimize (free_count=2, 1 pass, 15 nurse-pairs) per week

Run from NRP_Claude_Agent/:
    python3 compare_fo_n030w4.py

Outputs:
  - Per-week penalty breakdown for each method
  - Compact comparison table (for Computational Results section)
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from outer_milp.models.milp_model import MilpModel
from outer_milp.utils.inrc2_parser import parse
from outer_milp.utils.penalty_evaluator import evaluate
from outer_milp.utils.multi_week_runner import (
    run as run_baseline,
    _end_of_week_history,
)

# ── Experiment parameters ──────────────────────────────────────────────────────
INSTANCE_DIR = "data/raw_inrc2/datasets_json/n030w4"
WEEKS = [0, 1, 2, 3]
HISTORY = 0
MILP_TIME = 60    # CBC time limit per week (seconds)
FO_TIME   = 10    # CBC time limit per F&O subproblem (seconds)
FO_PASSES = 1     # number of full sweeps through all nurse pairs per week
FREE_COUNT = 2    # nurses freed per F&O call (nurse decomposition width)


def _run_proposed(instance_dir, weeks, history_variant,
                  milp_time, fo_time, fo_passes, free_count):
    """MILP + F&O multi-week runner.

    Mirrors multi_week_runner.run() but adds Fix-and-Optimize passes after each
    weekly MILP solve, using the sliding-window nurse decomposition from main.py.
    """
    results = []
    carry = None

    for week_idx in weeks:
        t0 = time.time()
        data = parse(instance_dir, week=week_idx, history=history_variant)

        if carry is not None:
            for n_idx in range(len(data["nurse_info"])):
                data["nurse_info"][n_idx]["history"] = carry[n_idx]["history"]

        # MILP full solve
        model = MilpModel(data)
        model.build()
        schedule, milp_pen = model.solve(time_limit=milp_time)
        data["current_schedule"] = schedule
        print(f"  [W{week_idx}] MILP  penalty={milp_pen:8.1f}  "
              f"elapsed={time.time()-t0:.1f}s")

        # Fix-and-Optimize passes
        N = data["metadata"]["num_nurses"]
        pen = milp_pen
        accepted_total = 0

        for _ in range(fo_passes):
            for i in range(0, N - free_count + 1, free_count):
                free = list(range(i, i + free_count))
                fo_m = MilpModel(data)
                new_sched, new_pen, ok = fo_m.fix_and_optimize(
                    free, pen, time_limit=fo_time
                )
                if ok:
                    pen = new_pen
                    data["current_schedule"] = new_sched
                    schedule = new_sched
                    accepted_total += 1

        print(f"  [W{week_idx}] F&O   accepted={accepted_total:2d}/{N // free_count}  "
              f"post-F&O_pen={pen:8.1f}  elapsed={time.time()-t0:.1f}s")

        penalties = evaluate(schedule, data)
        results.append({"week": week_idx, **penalties})

        carry = _end_of_week_history(schedule, data["nurse_info"])

    return results


# ── Reporting helpers ──────────────────────────────────────────────────────────

_COL = "{:>6} | {:>8} | {:>9} | {:>8} | {:>8} | {:>7} | {:>7}"
_HDR = _COL.format("Week", "S1_cov", "S2_cwork", "S3_coff", "S4_pref", "Forbid", "Total")
_SEP = "-" * len(_HDR)


def _print_breakdown(label, results):
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(_SEP)
    print(_HDR)
    print(_SEP)
    total = 0
    for r in results:
        print(_COL.format(
            r["week"],
            r["S1_coverage"],
            r["S2_consecutive_work"],
            r["S3_consecutive_off"],
            r["S4_preferences"],
            r["forbidden_succession_violations"],
            r["total"],
        ))
        total += r["total"]
    print(_SEP)
    print(_COL.format("SUM", "", "", "", "", "", total))
    print(_SEP)
    return total


def _print_comparison(base_results, prop_results,
                       base_total, prop_total,
                       base_time, prop_time):
    """Compact comparison table ready for paper (Computational Results)."""
    delta = base_total - prop_total
    pct = 100.0 * delta / base_total if base_total > 0 else 0.0

    print(f"\n{'=' * 70}")
    print(f"  COMPARISON TABLE — n030w4 (30 nurses, 4 weeks, History=0)")
    print(f"{'=' * 70}")

    hdr = f"{'Method':<30} | {'W0':>6} | {'W1':>6} | {'W2':>6} | {'W3':>6} | {'Total':>7} | {'Time(s)':>8}"
    sep2 = "-" * len(hdr)
    print(sep2)
    print(hdr)
    print(sep2)

    def _row(label, results, total, runtime):
        vals = [r["total"] for r in results]
        return (f"{label:<30} | {vals[0]:>6} | {vals[1]:>6} | {vals[2]:>6} | {vals[3]:>6} "
                f"| {total:>7} | {runtime:>8.0f}")

    print(_row("Baseline (MILP only)",
               base_results, base_total, base_time))
    print(_row(f"Proposed (MILP+F&O, k={FREE_COUNT})",
               prop_results, prop_total, prop_time))
    print(sep2)
    print(f"{'Improvement (Δ)':<30} | {'':>6} | {'':>6} | {'':>6} | {'':>6} "
          f"| {delta:>+7} | {'':>8}")
    print(f"{'Improvement (%)':<30} | {'':>6} | {'':>6} | {'':>6} | {'':>6} "
          f"| {pct:>7.1f}% | {'':>8}")
    print(sep2)


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  NRP n030w4 — Baseline vs Proposed (F&O) Benchmark")
    print(f"  MILP_TIME={MILP_TIME}s  FO_TIME={FO_TIME}s  "
          f"FREE_COUNT={FREE_COUNT}  FO_PASSES={FO_PASSES}")
    print("=" * 60)

    # Phase 1: Baseline (MILP only)
    print("\n[PHASE 1] Baseline — MILP only (multi_week_runner.run)")
    t0 = time.time()
    base_results = run_baseline(
        INSTANCE_DIR, WEEKS, HISTORY, time_limit=MILP_TIME
    )
    base_time = time.time() - t0
    print(f"  Baseline done in {base_time:.0f}s")

    # Phase 2: Proposed (MILP + F&O)
    print(f"\n[PHASE 2] Proposed — MILP + F&O (free_count={FREE_COUNT})")
    t0 = time.time()
    prop_results = _run_proposed(
        INSTANCE_DIR, WEEKS, HISTORY,
        MILP_TIME, FO_TIME, FO_PASSES, FREE_COUNT,
    )
    prop_time = time.time() - t0
    print(f"  Proposed done in {prop_time:.0f}s")

    # Per-method breakdown tables
    base_total = _print_breakdown("Baseline (MILP only)", base_results)
    prop_total = _print_breakdown(
        f"Proposed (MILP + F&O, free_count={FREE_COUNT})", prop_results
    )

    # Compact comparison for paper
    _print_comparison(
        base_results, prop_results,
        base_total, prop_total,
        base_time, prop_time,
    )
