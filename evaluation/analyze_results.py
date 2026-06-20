"""Analysis and plotting for the EVAL-段3 overnight batch (60 instance×mode jobs).

Loads results/batch_2026-06-20/*.json into a DataFrame, joins the
organiser-validated best-known costs (references/eval_design_notes.md §3,
Rank_LateInstances_ValidatedResults.xlsx), and renders P1-P5 to
results/batch_2026-06-20/plots/. P6 (summary table) is printed as markdown
to stdout for embedding in the writeup.

Run from NRP_Claude_Agent/:
    python3 evaluation/analyze_results.py
"""

import glob
import json
import os
import re

import matplotlib.pyplot as plt
import pandas as pd

RESULTS_DIR = "results/batch_2026-06-20"
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")

# Organiser-validated best-known cost per dataset, rolled up as the min across
# 9 validated teams x the dataset's 2 late instances (eval_design_notes.md §3).
# Testdatasets (n005/n012/n021) are not part of the competition's public
# testbed and have no entry here.
BEST_KNOWN = {
    "n030w4": 1755, "n030w8": 1900, "n040w4": 1730, "n040w8": 2700,
    "n050w4": 1480, "n050w8": 5410, "n060w4": 2815, "n060w8": 2765,
    "n080w4": 3535, "n080w8": 4995, "n100w4": 1445, "n100w8": 3055,
    "n120w4": 2435, "n120w8": 3510,
}

MODE_ORDER = ["milp", "fo", "full"]
MODE_COLORS = {"milp": "#4C72B0", "fo": "#DD8452", "full": "#55A868"}
WEEK_MARKERS = {4: "o", 8: "s"}


def _parse_size(dataset: str) -> tuple:
    m = re.match(r"n(\d+)w(\d+)", dataset)
    return int(m.group(1)), int(m.group(2))


def dataset_order(df: pd.DataFrame) -> list:
    uniq = df["dataset"].unique().tolist()
    return sorted(uniq, key=_parse_size)


def load_dataframe() -> pd.DataFrame:
    rows = []
    for path in sorted(glob.glob(os.path.join(RESULTS_DIR, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            rec = json.load(f)[0]
        n_nurses, n_weeks = _parse_size(rec["dataset"])
        rows.append({
            "dataset": rec["dataset"],
            "n_nurses": n_nurses,
            "n_weeks": n_weeks,
            "nurse_count": n_nurses,
            "week_count": n_weeks,
            "instance_id": rec["instance_id"],
            "mode": rec["mode"],
            "total_inrc2_cost": rec["total_inrc2_cost"],
            "per_week_cost": [w["total"] for w in rec["per_week"]],
            "global_s6": rec["global_s6"],
            "global_s7": rec["global_s7"],
            "h2_clean_all_weeks": rec["h2_clean_all_weeks"],
            "h3_clean_all_weeks": rec["h3_clean_all_weeks"],
            "wall_clock_total_seconds": rec["wall_clock_total_seconds"],
        })
    df = pd.DataFrame(rows)
    df["best_known_cost"] = df["dataset"].map(BEST_KNOWN)
    df["gap_pct"] = (
        (df["total_inrc2_cost"] - df["best_known_cost"]) / df["best_known_cost"] * 100
    )
    return df


def plot_p1(df: pd.DataFrame, path: str) -> None:
    datasets = dataset_order(df)
    width = 0.25
    offsets = {"milp": -width, "fo": 0, "full": width}
    fig, ax = plt.subplots(figsize=(14, 6))
    for mode in MODE_ORDER:
        data, positions = [], []
        for i, ds in enumerate(datasets):
            vals = df[(df["dataset"] == ds) & (df["mode"] == mode)]["total_inrc2_cost"].tolist()
            if vals:
                data.append(vals)
                positions.append(i + offsets[mode])
        if not data:
            continue
        bp = ax.boxplot(data, positions=positions, widths=width * 0.8,
                         patch_artist=True, manage_ticks=False,
                         medianprops={"color": MODE_COLORS[mode]})
        for patch in bp["boxes"]:
            patch.set_facecolor(MODE_COLORS[mode])
            patch.set_alpha(0.7)
    ax.set_xticks(range(len(datasets)))
    ax.set_xticklabels(datasets, rotation=45, ha="right")
    ax.set_yscale("log")
    ax.set_ylabel("Total INRC-II cost (log scale)")
    ax.set_title("P1: Cost distribution per dataset, grouped by mode\n"
                 "(n=1 boxes are single points; only testdataset 'full' has n>1 replicates)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=MODE_COLORS[m]) for m in MODE_ORDER]
    ax.legend(handles, MODE_ORDER, title="mode")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_p2(df: pd.DataFrame, path: str) -> None:
    datasets = dataset_order(df)
    means = df.groupby(["dataset", "mode"])["total_inrc2_cost"].mean().unstack().reindex(datasets)
    width = 0.25
    fig, ax = plt.subplots(figsize=(14, 6))
    for j, mode in enumerate(MODE_ORDER):
        xs = [i + (j - 1) * width for i in range(len(datasets))]
        ax.bar(xs, means[mode], width=width, label=mode, color=MODE_COLORS[mode])
    for i, ds in enumerate(datasets):
        bk = BEST_KNOWN.get(ds)
        if bk is not None:
            ax.hlines(bk, i - 1.5 * width, i + 1.5 * width, colors="black",
                       linestyles="--", linewidth=1.5)
    ax.set_xticks(range(len(datasets)))
    ax.set_xticklabels(datasets, rotation=45, ha="right")
    ax.set_yscale("log")
    ax.set_ylabel("Mean total INRC-II cost (log scale)")
    ax.set_title("P2: Mean cost per dataset x mode (dashed line = best-known)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_p3(df: pd.DataFrame, path: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=False)
    for ax, w in zip(axes, (4, 8)):
        sub_w = df[df["week_count"] == w]
        ns = sorted(sub_w["nurse_count"].unique())
        for mode in MODE_ORDER:
            means = sub_w[sub_w["mode"] == mode].groupby("nurse_count")["total_inrc2_cost"].mean()
            means = means.reindex(ns)
            ax.plot(ns, means, marker="o", color=MODE_COLORS[mode], label=mode)
        bk_ns = [n for n in ns if df.loc[(df["nurse_count"] == n) & (df["week_count"] == w),
                                          "dataset"].iloc[0] in BEST_KNOWN]
        bk_vals = [BEST_KNOWN[df.loc[(df["nurse_count"] == n) & (df["week_count"] == w),
                                      "dataset"].iloc[0]] for n in bk_ns]
        if bk_ns:
            ax.plot(bk_ns, bk_vals, marker="X", linestyle="--", color="black", label="best-known")
        ax.set_yscale("log")
        ax.set_xlabel("Number of nurses (N)")
        ax.set_ylabel("Total INRC-II cost (log scale)")
        ax.set_title(f"W={w}")
        ax.legend(fontsize=8)
    fig.suptitle("P3: Cost vs. instance size, by mode")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_p4(df: pd.DataFrame, path: str) -> None:
    datasets = dataset_order(df)
    width = 0.25
    offsets = {"milp": -width, "fo": 0, "full": width}
    fig, ax = plt.subplots(figsize=(14, 6))
    for mode in MODE_ORDER:
        xs, ys = [], []
        for i, ds in enumerate(datasets):
            rows = df[(df["dataset"] == ds) & (df["mode"] == mode)]
            if rows.empty or rows["gap_pct"].isna().all():
                continue
            xs.append(i + offsets[mode])
            ys.append(rows["gap_pct"].mean())
        ax.bar(xs, ys, width=width * 0.9, color=MODE_COLORS[mode], label=mode)
    for i, ds in enumerate(datasets):
        if ds not in BEST_KNOWN:
            ax.text(i, 0, "no benchmark", ha="center", va="bottom", fontsize=7,
                     rotation=90, color="gray")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(range(len(datasets)))
    ax.set_xticklabels(datasets, rotation=45, ha="right")
    ax.set_ylabel("Gap to best-known (%)")
    ax.set_title("P4: Gap to organiser-validated best-known cost, by mode")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_p5(df: pd.DataFrame, path: str) -> None:
    fig, ax = plt.subplots(figsize=(9, 6))
    for mode in MODE_ORDER:
        for w in (4, 8):
            sub = df[(df["mode"] == mode) & (df["week_count"] == w)]
            if sub.empty:
                continue
            ax.scatter(sub["nurse_count"], sub["wall_clock_total_seconds"],
                       color=MODE_COLORS[mode], marker=WEEK_MARKERS[w], alpha=0.8,
                       label=f"{mode} (W={w})")
    n_range = sorted(n for n in df["nurse_count"].unique() if n >= 20)
    for w, ls in ((4, "--"), (8, ":")):
        budget = [(10 + 3 * (n - 20)) * w for n in n_range]
        ax.plot(n_range, budget, color="black", linestyle=ls, linewidth=1.5,
                label=f"Ceschia 2019 budget (W={w})")
    ax.set_yscale("log")
    ax.set_xlabel("Number of nurses (N)")
    ax.set_ylabel("Wall-clock seconds (log scale)")
    ax.set_title("P5: Wall-clock vs. instance size, vs. Ceschia 2019 §4.2 budget\n"
                 "(budget formula undefined below N=20 — testdatasets shown without a reference line)")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def build_p6_table(df: pd.DataFrame) -> str:
    datasets = dataset_order(df)
    lines = [
        "| dataset | N | W | best-known | milp | fo | full | gap_full% |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for ds in datasets:
        sub = df[df["dataset"] == ds]
        milp_row = sub[sub["mode"] == "milp"].iloc[0]
        canon = sub[sub["instance_id"] == milp_row["instance_id"]]
        n, w = int(milp_row["n_nurses"]), int(milp_row["n_weeks"])

        def cell(mode):
            r = canon[canon["mode"] == mode]
            return str(int(r.iloc[0]["total_inrc2_cost"])) if len(r) else "—"

        milp_c, fo_c, full_c = cell("milp"), cell("fo"), cell("full")
        bk = BEST_KNOWN.get(ds)
        if bk is not None and len(canon[canon["mode"] == "full"]):
            full_val = canon[canon["mode"] == "full"].iloc[0]["total_inrc2_cost"]
            bk_str, gap_str = str(bk), f"{(full_val - bk) / bk * 100:+.1f}%"
        else:
            bk_str, gap_str = "no benchmark", "—"
        lines.append(f"| {ds} | {n} | {w} | {bk_str} | {milp_c} | {fo_c} | {full_c} | {gap_str} |")
    return "\n".join(lines)


def main() -> None:
    df = load_dataframe()
    assert len(df) == 60, f"expected 60 rows, got {len(df)}"
    os.makedirs(PLOTS_DIR, exist_ok=True)

    plot_p1(df, os.path.join(PLOTS_DIR, "p1_cost_by_dataset.png"))
    plot_p2(df, os.path.join(PLOTS_DIR, "p2_mean_cost_bar.png"))
    plot_p3(df, os.path.join(PLOTS_DIR, "p3_cost_vs_N.png"))
    plot_p4(df, os.path.join(PLOTS_DIR, "p4_gap_to_best_known.png"))
    plot_p5(df, os.path.join(PLOTS_DIR, "p5_wallclock_vs_N.png"))

    print(f"Loaded {len(df)} rows across {df['dataset'].nunique()} datasets.")
    print()
    print(build_p6_table(df))


if __name__ == "__main__":
    main()
