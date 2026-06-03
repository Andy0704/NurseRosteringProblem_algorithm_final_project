"""Segment 3: Broad SA ≡ evaluator identity test — 800 random schedules.

Contexts: n021w4 weeks 0/1/2/3 with MILP-propagated history (4 × 200 = 800).
BLOCK (< 1e-6): S2_consecutive_work, S3_consecutive_off, forbidden_violations.
LOG only (known-divergent): S1_coverage (weight/source differ), S4_preferences (weight 5 vs 10).

On any BLOCK failure: print schedule, nurse histories, both-side breakdowns; stop immediately.
"""

import copy
import json
import os
import random
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from outer_milp.models.milp_model import MilpModel
from outer_milp.utils.inrc2_parser import parse
from outer_milp.utils.penalty_evaluator import evaluate
from outer_milp.utils.multi_week_runner import _end_of_week_history

BINARY   = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "inner_heuristic", "build", "nrp_heuristic"))
INSTANCE = "data/raw_inrc2/testdatasets_json/n021w4"
N_RANDOM = 200
RNG_SEED = 42


# ── helpers ──────────────────────────────────────────────────────────────────

def _run_eval_only(data: dict, schedule: list) -> dict:
    d = copy.deepcopy(data)
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


def _build_week_contexts():
    """Solve MILP for each week and propagate history, returning 4 data dicts."""
    contexts = []
    carry = None
    for week in range(4):
        data = parse(INSTANCE, week=week, history=0)
        if carry is not None:
            for n_idx in range(len(data["nurse_info"])):
                data["nurse_info"][n_idx]["history"] = carry[n_idx]["history"]
        contexts.append(copy.deepcopy(data))
        model = MilpModel(data)
        model.build()
        sched, _ = model.solve(time_limit=15)
        carry = _end_of_week_history(sched, data["nurse_info"])
    return contexts


def _block_fail(label: str, comp: str, sched: list, data: dict,
                sa_out: dict, ev_out: dict) -> None:
    """Print failure details and stop.  Called only when SA ≠ eval on a BLOCK item."""
    nurses = data["nurse_info"]
    print(f"\n{'='*70}")
    print(f"BLOCK FAILURE  {label}  component={comp}")
    print(f"  SA  breakdown : {sa_out}")
    print(f"  Eval breakdown: {ev_out}")
    print(f"  Schedule (nurse × day), 0=Off:")
    for n_idx, row in enumerate(sched):
        hist = nurses[n_idx]["history"]
        print(f"    N{n_idx:02d} row={row}  "
              f"hist_cw={hist['consecutive_working_days']}  "
              f"hist_co={hist['consecutive_days_off']}")
    print(f"{'='*70}")


# ── main test ─────────────────────────────────────────────────────────────────

def test_sa_identity_800():
    """800 random schedules: S2, S3, forbidden must be SA≡eval within 1e-6."""
    contexts = _build_week_contexts()
    rng = random.Random(RNG_SEED)

    s1_diffs, s4_diffs = [], []
    total_checked = 0

    for week_idx, data in enumerate(contexts):
        N = data["metadata"]["num_nurses"]
        D = data["metadata"]["num_days"]
        S = data["metadata"]["num_shift_types"]

        for i in range(N_RANDOM):
            sched = [[rng.randint(0, S - 1) for _ in range(D)] for _ in range(N)]
            label = f"W{week_idx}_#{i:03d}"

            sa_out = _run_eval_only(data, sched)

            data_ev = copy.deepcopy(data)
            data_ev["current_schedule"] = sched
            ev_out = evaluate(sched, data_ev)

            sa_s2 = sa_out["S2_consecutive_work"]
            sa_s3 = sa_out["S3_consecutive_off"]
            sa_fb = sa_out["forbidden_violations"]
            ev_s2 = ev_out["S2_consecutive_work"]
            ev_s3 = ev_out["S3_consecutive_off"]
            ev_fb = ev_out["forbidden_succession_violations"]

            # Log known-divergent (do not block)
            s1_diffs.append(abs(sa_out["S1_coverage"] - ev_out["S1_coverage"]))
            s4_diffs.append(abs(sa_out["S4_preferences"] - ev_out["S4_preferences"]))

            # BLOCK assertions
            if abs(sa_s2 - ev_s2) >= 1e-6:
                _block_fail(label, "S2", sched, data, sa_out, ev_out)
                pytest.fail(f"{label}: S2 mismatch  sa={sa_s2}  eval={ev_s2}")

            if abs(sa_s3 - ev_s3) >= 1e-6:
                _block_fail(label, "S3", sched, data, sa_out, ev_out)
                pytest.fail(f"{label}: S3 mismatch  sa={sa_s3}  eval={ev_s3}")

            if abs(sa_fb - ev_fb) >= 1e-6:
                _block_fail(label, "forbidden", sched, data, sa_out, ev_out)
                pytest.fail(f"{label}: forbidden mismatch  sa={sa_fb}  eval={ev_fb}")

            total_checked += 1

    # ── known-divergent summary ──────────────────────────────────────────────
    nonzero_s1 = sum(1 for d in s1_diffs if d > 0)
    nonzero_s4 = sum(1 for d in s4_diffs if d > 0)
    print(f"\n=== KNOWN-DIVERGENT LOG ({total_checked} schedules) ===")
    print(f"  S1_coverage  : nonzero_diff={nonzero_s1}/{total_checked}  "
          f"min={min(s1_diffs)}  max={max(s1_diffs)}  "
          f"mean={sum(s1_diffs)/len(s1_diffs):.1f}")
    print(f"  S4_preferences: nonzero_diff={nonzero_s4}/{total_checked}  "
          f"min={min(s4_diffs)}  max={max(s4_diffs)}  "
          f"mean={sum(s4_diffs)/len(s4_diffs):.1f}")
    if nonzero_s4 > 0:
        # All S4 diffs should be exactly 0.5× (weight ratio 5:10)
        ratios = [sa_out["S4_preferences"] / ev_out["S4_preferences"]
                  for (sa_out, ev_out) in []]  # can't reconstruct here; just note
        print(f"  S4 expected ratio: 0.5× (SHIFT_OFF_REQ_W=5 vs _W_PREF=10)")
    print(f"  BLOCK items (S2, S3, forbidden): ALL CLEAN ✓")
