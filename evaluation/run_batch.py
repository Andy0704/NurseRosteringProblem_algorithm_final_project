"""Fault-tolerant batch wrapper around run_ablation.py for the overnight
14-dataset INRC-II evaluation.

Each (instance, mode) job runs in its own subprocess, so a CBC hang or a
crash on one instance cannot take down the rest of the batch. Per-instance
JSON is written immediately by run_ablation.py itself, so an interrupt only
loses the in-progress job, not prior results — re-running with --resume
picks up where it left off.

Run from NRP_Claude_Agent/:
    python3 evaluation/run_batch.py \
        --instances-file evaluation/finalist_instances.txt \
        --modes milp,fo,full \
        --output-dir results/batch_2026-06-20/ \
        --log-file results/batch_2026-06-20/batch.log \
        --time-limit-per-week 310 \
        [--resume]

Instances file format, one line per instance (blank lines / lines
starting with '#' are skipped):
    dataset history_id week_sequence_comma_separated [mode_override]
The optional 4th field pins that instance to a single mode regardless of
--modes (used for the testdataset SA-stability extras, which only run in
'full' mode).
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time

RUN_ABLATION = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_ablation.py")

_shutdown_requested = False


def _request_shutdown(signum, frame) -> None:
    global _shutdown_requested
    _shutdown_requested = True


def _parse_instances_file(path: str) -> list:
    instances = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            tokens = line.split()
            if len(tokens) not in (3, 4):
                raise ValueError(
                    f"{path}:{lineno}: expected 3 or 4 fields, got "
                    f"{len(tokens)}: {line!r}"
                )
            dataset, history, weeks_csv = tokens[0], int(tokens[1]), tokens[2]
            mode_override = tokens[3] if len(tokens) == 4 else None
            instances.append({
                "dataset": dataset,
                "history": history,
                "weeks_csv": weeks_csv,
                "num_weeks": len(weeks_csv.split(",")),
                "mode_override": mode_override,
            })
    return instances


def _instance_label(instance: dict) -> str:
    return (f"{instance['dataset']}_{instance['history']}_"
            f"{instance['weeks_csv'].replace(',', '-')}")


def _log(log_file: str, msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    print(line)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _is_valid_json(path: str) -> bool:
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, OSError):
        return False


def _write_failure(output_path: str, instance_label: str, mode: str, reason: str) -> None:
    placeholder = [{
        "instance_id": instance_label,
        "mode": mode,
        "status": "FAILED",
        "reason": reason,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }]
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(placeholder, f, indent=2)


def run_one(instance: dict, mode: str, output_dir: str, log_file: str,
            time_limit_per_week: int, resume: bool) -> None:
    label = _instance_label(instance)
    output_path = os.path.join(output_dir, f"{label}_{mode}.json")

    if resume and _is_valid_json(output_path):
        _log(log_file, f"SKIP    {label} mode={mode} (already complete)")
        return

    cmd = [
        sys.executable, RUN_ABLATION,
        "--dataset", instance["dataset"],
        "--history", str(instance["history"]),
        "--weeks", instance["weeks_csv"],
        "--mode", mode,
        "--output", output_path,
        "--time-limit-per-week", str(time_limit_per_week),
    ]
    # Generous per-job ceiling to catch infinite loops, not a tight budget:
    # 2x the Ceschia per-instance MILP-only wall-clock estimate.
    timeout_seconds = max(60, instance["num_weeks"] * time_limit_per_week * 2)

    t0 = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=timeout_seconds)
        elapsed = time.time() - t0
        if result.returncode != 0:
            _write_failure(output_path, label, mode,
                            f"exit {result.returncode}: {result.stderr.strip()[-500:]}")
            _log(log_file, f"FAIL    {label} mode={mode} "
                            f"exit={result.returncode} elapsed={elapsed:.1f}s")
        else:
            _log(log_file, f"DONE    {label} mode={mode} elapsed={elapsed:.1f}s")
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        _write_failure(output_path, label, mode,
                        f"timed out after {timeout_seconds}s")
        _log(log_file, f"TIMEOUT {label} mode={mode} elapsed={elapsed:.1f}s")


def main() -> None:
    args = _parse_args()
    signal.signal(signal.SIGINT, _request_shutdown)
    signal.signal(signal.SIGTERM, _request_shutdown)

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(os.path.dirname(args.log_file) or ".", exist_ok=True)

    instances = _parse_instances_file(args.instances_file)
    requested_modes = args.modes.split(",")

    jobs = []
    for inst in instances:
        modes = [inst["mode_override"]] if inst["mode_override"] else requested_modes
        for mode in modes:
            jobs.append((inst, mode))

    _log(args.log_file, f"START batch: {len(jobs)} (instance, mode) jobs, "
                         f"resume={args.resume}")

    completed = 0
    for inst, mode in jobs:
        if _shutdown_requested:
            _log(args.log_file, "INTERRUPTED by user — stopping before next job "
                                 "(in-progress job, if any, already finished cleanly)")
            break
        run_one(inst, mode, args.output_dir, args.log_file,
                args.time_limit_per_week, args.resume)
        completed += 1

    _log(args.log_file, f"SUMMARY: {completed}/{len(jobs)} jobs attempted")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fault-tolerant batch wrapper over run_ablation.py."
    )
    p.add_argument("--instances-file", required=True)
    p.add_argument("--modes", required=True,
                   help="Comma-separated modes applied to every instance "
                        "lacking a per-line mode override, e.g. milp,fo,full")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--log-file", required=True)
    p.add_argument("--resume", action="store_true",
                   help="Skip instances whose output JSON already exists and is valid")
    p.add_argument("--time-limit-per-week", type=int, default=30,
                   help="Passed through to run_ablation.py (default: 30)")
    return p.parse_args()


if __name__ == "__main__":
    main()
