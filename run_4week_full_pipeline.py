"""4-week full pipeline benchmark: MILP → F&O → C++ SA, per week.

Designed as a read-only diagnostic — does NOT modify any existing source files.
Writes only to data/exchange/pipeline_bench.json (temp exchange file).

For each week records:
  milp_obj     : PuLP objective value returned by model.solve()
  post_fo_obj  : best MILP-scale penalty after all F&O calls
  sa_initial   : SA's fullCost() on the incoming schedule  (from metadata)
  sa_final     : SA's best cost found                      (from metadata)
  eval_sa      : penalty_evaluator.evaluate() on SA output schedule

Key diagnostics:
  NOTE (2026-06-03): ratio/scale-gap diagnostics below are SUPERSEDED.
    Root cause is implementation drift, not scale — see SA_IDENTITY_DIAGNOSTIC.md.
    Correct standard is per-item identity (<1e-6), NOT ratio. Use tests/test_sa_identity.py.
  sa_initial vs milp_obj  → scale mismatch (SA weight ≠ MILP weight)
  sa_final   vs sa_initial → did SA actually move? (hard-coverage lock?)
  eval_sa    vs milp_obj  → real-world quality of SA output

Run from NRP_Claude_Agent/:
    python3 run_4week_full_pipeline.py --instance n021w4
    python3 run_4week_full_pipeline.py --instance n012w8
"""

import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from outer_milp.models.milp_model import MilpModel
from outer_milp.utils.inrc2_parser import parse
from outer_milp.utils.json_handler import save_problem
from outer_milp.utils.penalty_evaluator import evaluate, evaluate_global_s6_s7
from outer_milp.utils.multi_week_runner import _end_of_week_history

# ── Tunable parameters ────────────────────────────────────────────────────────
MILP_TIME  = 30    # CBC time limit per week (seconds) — enough for ≤21 nurses
FO_TIME    = 10    # CBC time limit per F&O sub-problem
FO_PASSES  = 1
FREE_COUNT = 2
BINARY     = "inner_heuristic/build/nrp_heuristic"
EXCHANGE   = "data/exchange/pipeline_bench.json"  # dedicated temp file


def _run_fo(data: dict, milp_penalty: float) -> tuple:
    """Run one sweep of Fix-and-Optimize. Returns (schedule, best_penalty)."""
    N = data["metadata"]["num_nurses"]
    pen = milp_penalty
    accepted = 0
    for _ in range(FO_PASSES):
        for i in range(0, N - FREE_COUNT + 1, FREE_COUNT):
            free = list(range(i, i + FREE_COUNT))
            fo_m = MilpModel(data)
            new_sched, new_pen, ok = fo_m.fix_and_optimize(
                free, pen, time_limit=FO_TIME
            )
            if ok:
                pen = new_pen
                data["current_schedule"] = new_sched
                accepted += 1
    return data["current_schedule"], pen, accepted


def _run_sa(exchange_path: str) -> dict:
    """Invoke C++ SA binary. Returns the loaded output JSON."""
    result = subprocess.run(
        [BINARY, exchange_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"SA binary failed (code {result.returncode}): {result.stderr.strip()}"
        )
    with open(exchange_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_instance(instance_id: str, weeks: list, history: int) -> tuple:
    instance_dir = f"data/raw_inrc2/testdatasets_json/{instance_id}"
    rows = []
    carry = None
    weekly_schedules = []
    nurse_info_w0 = None
    contracts = None

    for seq_idx, week_idx in enumerate(weeks):
        t0 = time.time()
        print(f"\n── Week {week_idx} ────────────────────────────────────────")

        # 1. Parse
        data = parse(instance_dir, week=week_idx, history=history)
        if seq_idx == 0:
            nurse_info_w0 = data["nurse_info"]
            contracts = data.get("contracts", {})
        if carry is not None:
            for n_idx in range(len(data["nurse_info"])):
                data["nurse_info"][n_idx]["history"] = carry[n_idx]["history"]

        # 2. MILP
        model = MilpModel(data)
        is_final_week = (seq_idx == len(weeks) - 1)
        model.build(is_final_week=is_final_week, cur_week=seq_idx + 1,
                    num_weeks=len(weeks))
        schedule, milp_obj = model.solve(time_limit=MILP_TIME)
        data["current_schedule"] = schedule
        print(f"  MILP obj          = {milp_obj:8.1f}   ({time.time()-t0:.1f}s)")

        # 3. F&O
        schedule, post_fo_obj, fo_accepted = _run_fo(data, milp_obj)
        data["current_schedule"] = schedule
        N = data["metadata"]["num_nurses"]
        fo_pairs = N // FREE_COUNT
        print(f"  F&O post_obj      = {post_fo_obj:8.1f}   "
              f"accepted {fo_accepted}/{fo_pairs} pairs ({time.time()-t0:.1f}s)")

        # 4. SA — write exchange, run binary, read back
        save_problem(data, EXCHANGE)
        sa_out = _run_sa(EXCHANGE)
        sa_initial = sa_out["metadata"].get("initial_cost", float("nan"))
        sa_final   = sa_out["metadata"].get("final_cost",   float("nan"))
        sa_sched   = sa_out["current_schedule"]
        data["current_schedule"] = sa_sched
        weekly_schedules.append(sa_sched)
        print(f"  SA initial_cost   = {sa_initial:8.1f}   (SA's own scale)")
        print(f"  SA final_cost     = {sa_final:8.1f}   delta={sa_final - sa_initial:+.1f}")

        # 5. Evaluate SA output with Python evaluator (consistent scale)
        eval_sa = evaluate(sa_sched, data)["total"]
        print(f"  eval(SA output)   = {eval_sa:8.1f}   (Python evaluator)")
        print(f"  ── scale check: milp_obj={milp_obj:.0f}  sa_initial={sa_initial:.0f}  "
              f"ratio={sa_initial/milp_obj:.2f}" if milp_obj > 0 else
              f"  ── scale check: milp_obj=0, sa_initial={sa_initial:.0f}")

        rows.append({
            "week":        week_idx,
            "milp_obj":    milp_obj,
            "post_fo_obj": post_fo_obj,
            "sa_initial":  sa_initial,
            "sa_final":    sa_final,
            "sa_delta":    sa_final - sa_initial,
            "eval_sa":     eval_sa,
            "elapsed":     round(time.time() - t0, 1),
        })

        carry = _end_of_week_history(sa_sched, data["nurse_info"])

    global_result = evaluate_global_s6_s7(weekly_schedules, nurse_info_w0, contracts)
    return rows, global_result


def _print_report(instance_id: str, rows: list, global_result: dict) -> None:
    print(f"\n{'='*80}")
    print(f"  FULL PIPELINE REPORT — {instance_id}  (MILP→F&O→SA, 1 iter/week)")
    print(f"{'='*80}")
    hdr = (f"{'Wk':>3} | {'milp_obj':>9} | {'post_fo':>8} | "
           f"{'sa_init':>8} | {'sa_final':>9} | {'sa_Δ':>7} | "
           f"{'eval_sa':>8} | {'ratio':>6} | {'t(s)':>6}")
    sep = "-" * len(hdr)
    print(sep)
    print(hdr)
    print(sep)
    for r in rows:
        ratio = (r["sa_initial"] / r["milp_obj"]) if r["milp_obj"] > 0 else float("nan")
        print(f"{r['week']:>3} | {r['milp_obj']:>9.1f} | {r['post_fo_obj']:>8.1f} | "
              f"{r['sa_initial']:>8.1f} | {r['sa_final']:>9.1f} | {r['sa_delta']:>+7.1f} | "
              f"{r['eval_sa']:>8} | {ratio:>6.2f} | {r['elapsed']:>6}")
    print(sep)
    total_eval = sum(r["eval_sa"] for r in rows)
    total_milp = sum(r["milp_obj"] for r in rows)
    print(f"{'SUM':>3} | {total_milp:>9.1f} | {'':>8} | {'':>8} | {'':>9} | {'':>7} | "
          f"{total_eval:>8} |")
    print(sep)
    print()
    print(f"Global (end-of-horizon, Ceschia 2019 §2.5.2):")
    print(f"  S6_total_assignments : {global_result['S6_total_assignments']}")
    print(f"  S7_total_weekends    : {global_result['S7_total_weekends']}")
    print(f"  total_global         : {global_result['total_global']}")
    print(f"  TOTAL INRC-II        : {total_eval + global_result['total_global']}")
    print()
    print("Diagnostics:")
    for r in rows:
        ratio = (r["sa_initial"] / r["milp_obj"]) if r["milp_obj"] > 0 else float("nan")
        frozen = abs(r["sa_delta"]) < 1.0
        scale_gap = ratio > 1.5 or ratio < 0.5
        flags = []
        if frozen:    flags.append("SA-FROZEN")
        if scale_gap: flags.append(f"SCALE-GAP(ratio={ratio:.2f})")
        if r["eval_sa"] > r["milp_obj"]: flags.append("SA-DEGRADED-EVAL")
        status = ", ".join(flags) if flags else "ok"
        print(f"  W{r['week']}: {status}")
    print(f"{'='*80}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="4-week full pipeline benchmark (MILP→F&O→SA)")
    parser.add_argument("--instance", required=True,
                        choices=["n005w4", "n012w8", "n021w4"],
                        help="Instance ID (testdatasets_json)")
    parser.add_argument("--weeks", type=int, nargs="+", default=None,
                        help="Week indices (default: full horizon per the "
                             "instance's Sc-*.json numberOfWeeks)")
    parser.add_argument("--history", type=int, default=0)
    args = parser.parse_args()

    if args.weeks is None:
        sc_path = (f"data/raw_inrc2/testdatasets_json/{args.instance}/"
                   f"Sc-{args.instance}.json")
        with open(sc_path, "r", encoding="utf-8") as f:
            args.weeks = list(range(json.load(f)["numberOfWeeks"]))

    print(f"Instance : {args.instance}")
    print(f"Weeks    : {args.weeks}")
    print(f"MILP_TIME={MILP_TIME}s  FO_TIME={FO_TIME}s  FREE_COUNT={FREE_COUNT}")
    print(f"Binary   : {BINARY}")

    rows, global_result = run_instance(args.instance, args.weeks, args.history)
    _print_report(args.instance, rows, global_result)
