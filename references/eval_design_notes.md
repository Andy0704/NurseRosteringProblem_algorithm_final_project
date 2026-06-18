# EVAL-段0: Full Evaluation Matrix — Scope Discovery (Design Notes)

Read-only scope discovery for the planned full 14-dataset evaluation against
published INRC-II competition results. No pipeline/runner code was written or
modified in this segment — this is a design note only, per the segment's
read-only guardrail.

Confirmed user decisions going in:
- Scope: all 14 production datasets in `data/raw_inrc2/datasets_json/`.
- Instance selection: the same instances the INRC-II finalists were
  evaluated on (Ceschia 2019 §3.2: 28 instances, 2 per public dataset),
  fallback to a spec-default instance only if those IDs could not be
  recovered.
- New runner file: `evaluation/run_ablation.py` (sketch only this segment;
  `run_4week_full_pipeline.py` and `multi_week_runner.py` untouched).
- Source priority for finalist data: `http://mobiz.vives.be/inrc2/` first,
  fallback to Mischek 2019 Table 2 / Ceschia 2019 §6.

---

## 1. Dataset inventory

Every one of the 14 production datasets and the 3 test datasets was listed
directly (`ls`) and cross-checked against `Sc-*.json`'s `numberOfWeeks` and
nurse count. All 17 directories match the Ceschia 2019 §3.1 file-count spec
exactly: **1 scenario file + 3 initial-history files (`H0-*-{0,1,2}.json`) +
10 week-data files (`WD-*-{0..9}.json`)**, regardless of whether the dataset
is `w4` or `w8` — the pool of week-data files is always 10; the scenario's
`numberOfWeeks` only determines how many of those 10 are *selected* (with
repetition allowed) into a given instance's week-sequence. This is confirmed
directly by Ceschia 2019 p.178 §3.2 (see §2 below).

| Dataset | N nurses | W weeks | WD files | H0 files | OK? |
|---|---:|---:|---:|---:|---|
| n030w4 | 30 | 4 | 10 | 3 | ✅ |
| n030w8 | 30 | 8 | 10 | 3 | ✅ |
| n040w4 | 40 | 4 | 10 | 3 | ✅ |
| n040w8 | 40 | 8 | 10 | 3 | ✅ |
| n050w4 | 50 | 4 | 10 | 3 | ✅ |
| n050w8 | 50 | 8 | 10 | 3 | ✅ |
| n060w4 | 60 | 4 | 10 | 3 | ✅ |
| n060w8 | 60 | 8 | 10 | 3 | ✅ |
| n080w4 | 80 | 4 | 10 | 3 | ✅ |
| n080w8 | 80 | 8 | 10 | 3 | ✅ |
| n100w4 | 100 | 4 | 10 | 3 | ✅ |
| n100w8 | 100 | 8 | 10 | 3 | ✅ |
| n120w4 | 120 | 4 | 10 | 3 | ✅ |
| n120w8 | 120 | 8 | 10 | 3 | ✅ |
| n005w4 (test) | 5 | 4 | 10 | 3 | ✅ |
| n012w8 (test) | 12 | 8 | 10 | 3 | ✅ |
| n021w4 (test) | 21 | 4 | 10 | 3 | ✅ |

Bonus finding: the 3 **test** datasets additionally ship
`Solution_H_<idx>-WD_<sequence>/` reference-solution directories (e.g.
`n005w4/Solution_H_0-WD_1-2-3-3/Sol-n005w4-1-0.json`), confirming the
official `H_<history>-WD_<week-list>` naming convention directly from data
ahead of finding it in the literature (§2). The 14 **production** datasets
have no such embedded solutions (that's the actual competition challenge),
so §2's recovery had to come from the website/papers, not local files.

---

## 2. Finalist instance IDs — FULL recovery (28/28)

**Status: complete recovery, no fallback needed.**

Source: `http://mobiz.vives.be/inrc2/?page_id=20` ("Data" page) links a file
named **"28 late instances"** at
`http://mobiz.vives.be/inrc2/wp-content/uploads/2014/08/late-instances.txt`,
fetched directly via `WebFetch`. It contains exactly 28 instance IDs, 2 per
dataset, in the format `<dataset>_<history-index>_<week-index-list>`.

Cross-validated against the literature: Ceschia 2019 p.178 §3.2 states *"the
string n040w4_2_6-1-0-6 identifies the instance belonging to the dataset
n040w4, completed with the history file number 2 and the sequence of
week-data files number 6, 1, 0, and 4"* — and `n040w4_2_6-1-0-6` is **literally
instance #6 in the fetched list below**, an exact string match. Ceschia 2019
§6 (p.181) further confirms: *"All 15 participants supplied their solutions
for the 28 instances extracted from the public datasets... 2 weeks before the
deadline."* This is the preliminary round (used to select the 7 finalists),
run on our 14 in-scope public datasets — distinct from the separate
60-instance hidden-testbed final round (§3 below).

Full list (citation: `late-instances.txt`, fetched 2026-06-20):

| Dataset | Instance A | Instance B |
|---|---|---|
| n030w4 | `n030w4_1_6-2-9-1` | `n030w4_1_6-7-5-3` |
| n030w8 | `n030w8_1_2-7-0-9-3-6-0-6` | `n030w8_1_6-7-5-3-5-6-2-9` |
| n040w4 | `n040w4_0_2-0-6-1` | `n040w4_2_6-1-0-6` |
| n040w8 | `n040w8_0_0-6-8-9-2-6-6-4` | `n040w8_2_5-0-4-8-7-1-7-2` |
| n050w4 | `n050w4_0_0-4-8-7` | `n050w4_0_7-2-7-2` |
| n050w8 | `n050w8_1_1-7-8-5-7-4-1-8` | `n050w8_1_9-7-5-3-8-8-3-1` |
| n060w4 | `n060w4_1_6-1-1-5` | `n060w4_1_9-6-3-8` |
| n060w8 | `n060w8_0_6-2-9-9-0-8-1-3` | `n060w8_2_1-0-3-4-0-3-9-1` |
| n080w4 | `n080w4_2_4-3-3-3` | `n080w4_2_6-0-4-8` |
| n080w8 | `n080w8_1_4-4-9-9-3-6-0-5` | `n080w8_2_0-4-0-9-1-9-6-2` |
| n100w4 | `n100w4_0_1-1-0-8` | `n100w4_2_0-6-4-6` |
| n100w8 | `n100w8_0_0-1-7-8-9-1-5-4` | `n100w8_1_2-4-7-9-3-9-2-8` |
| n120w4 | `n120w4_1_4-6-2-6` | `n120w4_1_5-6-9-8` |
| n120w8 | `n120w8_0_0-9-9-4-5-1-0-3` | `n120w8_1_7-2-6-4-5-2-0-2` |

ID semantics (Ceschia 2019 §3.2, p.178): `<dataset>_<H0 index>_<WD index
list, one per week, repetition allowed>`. The history index selects
`H0-<dataset>-<idx>.json` and is only used for week 0 (subsequent weeks'
history comes from simulated carry-forward, not from re-reading `H0` —
confirmed by reading `multi_week_runner.py`'s loop, §6 below). Each number in
the week-index list selects `WD-<dataset>-<num>.json` for that position in
the sequence; the same WD file may repeat (e.g. `n080w4_2_4-3-3-3` reuses
`WD-3` three times).

No fallback convention is needed since recovery is complete.

---

## 3. Best-known cost reference table — FULL recovery (28/28 instances)

**Status: complete recovery from the competition's own validated results.**

Source: `http://mobiz.vives.be/inrc2/?page_id=226` ("Finalists" page) links
**`Rank_LateInstances_ValidatedResults.xlsx`**
(`http://mobiz.vives.be/inrc2/wp-content/uploads/2015/07/Rank_LateInstances_ValidatedResults.xlsx`),
described on the page as the organiser-validated (re-checked) results for
exactly these 28 late instances, across 9 teams (the 7 finalists +
`ScheduleNurse` + `INF_UFRGS`, who did not advance to the final round but
submitted valid late-instance results). `WebFetch` cannot parse `.xlsx`
binary content directly, but it preserved the raw bytes to a local temp file;
parsed with Python's stdlib `zipfile` + `xml.etree.ElementTree` (no
package install — see data-quality note below on why this was necessary
instead of `openpyxl`).

Best-known cost = minimum across all 9 validated teams, per instance,
rolled up per dataset (min across the dataset's 2 instances = best-known;
range and per-instance detail reported per the task spec):

| Dataset | Best-known | Range | Best team |
|---|---:|---|---|
| n030w4 | **1755** | 1755–1935 | NurseOptimizers |
| n030w8 | **1900** | 1900–2340 | NurseOptimizers |
| n040w4 | **1730** | 1730–1880 | NurseOptimizers |
| n040w8 | **2700** | 2700–3310 | INF_UFRGS / NurseOptimizers |
| n050w4 | **1480** | 1480–1490 | NurseOptimizers |
| n050w8 | **5410** | 5410–5435 | NurseOptimizers |
| n060w4 | **2815** | 2815–2950 | NurseOptimizers / Polytechnique Montreal |
| n060w8 | **2765** | 2765–3065 | NurseOptimizers |
| n080w4 | **3535** | 3535–3570 | NurseOptimizers |
| n080w8 | **4995** | 4995–5030 | NurseOptimizers |
| n100w4 | **1445** | 1445–2100 | Polytechnique Montreal |
| n100w8 | **3055** | 3055–3080 | Polytechnique Montreal / NurseOptimizers |
| n120w4 | **2435** | 2435–2485 | NurseOptimizers |
| n120w8 | **3510** | 3510–3615 | NurseOptimizers |

No dataset is marked "no public benchmark" — all 14 have a validated
best-known cost.

**Data-quality note (Rule 10):** a second spreadsheet,
`Rank_LateInstances_SubmitedResults.xlsx` (self-reported, pre-validation,
16 teams), was also fetched for cross-check. Most rows are close to the
validated numbers, but `INF_UFRGS` shows one large discrepancy on
`n040w8_2_5-0-4-8-7-1-7-2` (submitted 4755 vs. validated 2700) — too large
for rounding/re-validation noise. Treating **Validated** as authoritative
(explicitly the organiser-rechecked set) and flagging rather than silently
picking a number. Spot-checking the wider 16-team submitted table confirms
no non-finalist team undercuts the validated minimum on any instance, so
the validated 9-team minimum is also the true global minimum across all 15
original participants.

**Mischek 2019 Table 2 / Ceschia 2019's hidden-testbed results — confirmed
NOT applicable to this table.** I initially expected Mischek 2019's Table 2
to give per-instance numbers for our 14 datasets, per the source-priority
list. Reading it directly (pdfplumber, pages 17–19) shows it instead reports
results on the **60-instance hidden testbed** (`n035`/`n070`/`n110`,
sets `{35,70,110}×{4,8}`, Ceschia 2019 §3.1 p.177) — a *different* set of 6
datasets used only for the competition's final ranking stage, disjoint from
our 14 public datasets (`{30,40,50,60,80,100,120}×{4,8}`). The
`Final-Ranking-20150826.xlsx` spreadsheet is the same hidden-testbed data.
Both are good context (and a 5th finalist's per-run numbers, useful if we
ever extend scope to `n035`/`n070`/`n110`) but were **not used** in the
table above — `Rank_LateInstances_ValidatedResults.xlsx` already gives exact
coverage of our actual 28 instances and is the stronger source.

---

## 4. Wall-clock budget

Formula confirmed verbatim in Ceschia 2019 p.180 §4.2: *"the benchmark
program will grant the participant approximately 10+3∗(N−20) seconds for
each stage, in which N is the number of nurses."* Computed per dataset
(conservative: full pipeline run = `seconds_per_week × num_weeks`; 3 configs
≈ 3× that single-run figure per the segment's instructions, even though in
practice `milp`-only and `milp+fo` will be faster than `full`):

| Dataset | N | W | sec/week | 1 run (s) | 3 configs, 1 instance (s) | 3 configs, 2 instances (s) |
|---|---:|---:|---:|---:|---:|---:|
| n030w4 | 30 | 4 | 40 | 160 | 480 | 960 |
| n030w8 | 30 | 8 | 40 | 320 | 960 | 1,920 |
| n040w4 | 40 | 4 | 70 | 280 | 840 | 1,680 |
| n040w8 | 40 | 8 | 70 | 560 | 1,680 | 3,360 |
| n050w4 | 50 | 4 | 100 | 400 | 1,200 | 2,400 |
| n050w8 | 50 | 8 | 100 | 800 | 2,400 | 4,800 |
| n060w4 | 60 | 4 | 130 | 520 | 1,560 | 3,120 |
| n060w8 | 60 | 8 | 130 | 1,040 | 3,120 | 6,240 |
| n080w4 | 80 | 4 | 190 | 760 | 2,280 | 4,560 |
| n080w8 | 80 | 8 | 190 | 1,520 | 4,560 | 9,120 |
| n100w4 | 100 | 4 | 250 | 1,000 | 3,000 | 6,000 |
| n100w8 | 100 | 8 | 250 | 2,000 | 6,000 | 12,000 |
| n120w4 | 120 | 4 | 310 | 1,240 | 3,720 | 7,440 |
| n120w8 | 120 | 8 | 310 | 2,480 | 7,440 | 14,880 |

### Scope options (vs. ~15h stated budget = 54,000s)

| Option | Description | Total est. | vs. budget |
|---|---|---:|---|
| (a) | Full plan: 14 datasets × 2 instances × 3 configs | 78,480s ≈ **21.8h** | **+45% over** |
| (b) | Skip n100+/n120 (10 datasets, N<100) × 2 instances × 3 configs | 38,160s ≈ **10.6h** | 29% under |
| (c) | W4-only (7 datasets) × 2 instances × 3 configs | 26,160s ≈ **7.3h** | 51% under |
| (d) | All 14 datasets × **1** instance × 3 configs | 39,240s ≈ **10.9h** | 27% under |
| hybrid | 2 instances for N<60 (6 datasets), 1 instance for N≥60 (8 datasets) | 46,800s ≈ **13.0h** | 13% under |

### Recommendation

(a) exceeds the stated budget by ~45% even under the conservative
3×-multiplier — not advisable as-is.

Leaning **(d)** over (b)/(c): P3 (cost vs. N) and P5 (wall-clock vs. size)
both need the full N-range (30→120) for a meaningful trend, and dropping
n100/n120 (b) or restricting to W4 (c) cuts off exactly the tail where CBC
solve-time is most likely to diverge from the small instances tested so
far. The cost of (d) is replication: with only 1 instance/dataset, P1's box
plot degenerates to a single point per (dataset, config) cell — note this
loses little real signal, since **CBC is already confirmed deterministic**
at tested sizes (W-10 段1A-verify) and **the SA's RNG seed is hardcoded**
(`std::mt19937 rng(42)`, `heuristic.cpp:649`, no CLI override), so two runs
of the *same* instance would be identical anyway — "2 instances" only ever
meant 2 different problems, not repeated trials. If the box-plot spread is
still wanted, the **hybrid** row (13.0h) keeps 2-instance replication where
it's cheap (N<60) and drops to 1 only where it's expensive (N≥60).

Recommendation, not a decision — flagged for human review.

---

## 5. Output schema and plotting plan

### JSON schema (`results/eval_<timestamp>.json`)

Adjusted field names to match the actual return keys of
`penalty_evaluator.evaluate()` and `evaluate_global_s6_s7()` (confirmed by
reading `outer_milp/utils/penalty_evaluator.py`), rather than the generic
`S1:.., S2:..` placeholder — avoids inventing a second, parallel naming
scheme for the same data:

```json
[
  {
    "dataset": "n040w4",
    "instance_id": "n040w4_2_6-1-0-6",
    "history_index": 2,
    "week_sequence": [6, 1, 0, 6],
    "mode": "full",
    "total_cost": 1234,
    "per_week_costs": [310, 280, 290, 354],
    "per_week_breakdown": [
      {"S1_coverage": 0, "S2_consecutive_work": 60, "S3_consecutive_off": 0,
       "S4_preferences": 10, "forbidden_succession_violations": 0, "total": 70}
    ],
    "global_s6": 0,
    "global_s7": 360,
    "h2_clean": true,
    "h3_clean": true,
    "wall_clock_seconds": 45.2,
    "timestamp": "2026-06-20T10:30:00",
    "config_hash": "ad82dfc5d6be3315b8f26489bf4698ee3e15c2cb"
  }
]
```

Notes:
- `h2_clean` = `S1_coverage == 0` for every week (the per-week H2-gate check
  already used in `tests/test_h3_gate.py` and the W-10 verification scripts).
- `h3_clean` = `forbidden_succession_violations == 0` for every week.
- `total_cost` = `sum(per_week_costs) + global_s6 + global_s7`, matching
  exactly how `run_4week_full_pipeline.py` already computes "TOTAL INRC-II".
- `config_hash` = `git rev-parse HEAD`, captured at run time.
- `history_index` / `week_sequence` are parsed once from `instance_id` and
  stored alongside it for convenience (avoids re-parsing the string for
  every plot/table downstream).

### Plot list (P1–P6)

| # | Plot | Axes / grouping |
|---|---|---|
| P1 | Box plot per dataset, grouped by config | Y: `total_cost`; X: dataset (ordered by N); box per (dataset, config) — **caveat:** with only 1–2 instances/dataset (§4), this is a thin box (n=1 or 2), not a real distribution; label it as a range, not a statistical box plot, if scope option (d) is chosen |
| P2 | Bar plot, mean cost per (dataset, config) | Y: mean `total_cost`; X: dataset; horizontal reference line per dataset = best-known (§3) |
| P3 | Line plot, cost vs. N | X: N nurses; Y: `total_cost`; 3 lines (milp/fo/full) + 1 reference line (best-known) — needs full N range, see §4 recommendation |
| P4 | Gap-to-best-known bar plot | Y: `(total_cost - best_known) / best_known × 100%`; X: dataset; grouped by config |
| P5 | Wall-clock vs. instance size | X: N (or N×W); Y: `wall_clock_seconds`; check against the §4 budget formula as a reference curve |
| P6 | Summary markdown table | Columns: dataset, MILP, MILP+F&O, Full, Best-known, Gap% — one row per dataset |

### Tooling availability — **matplotlib and pandas are NOT installed**

Checked directly (`python3 -c "import matplotlib"` / `import pandas`): both
raise `ModuleNotFoundError` in the active Python environment. Per the
segment's guardrail, **no install was attempted**. `openpyxl` is also
absent (worked around for the xlsx parsing in §3 using stdlib `zipfile` +
`xml.etree.ElementTree`, which is sufficient for one-off parsing but not
something to build a permanent plotting pipeline on).

For human decision: P1–P5 require `matplotlib` (and `pandas` would
substantially simplify the groupby/aggregation logic, though it's not
strictly required — stdlib `json` + manual aggregation can substitute).
P6 (markdown table) needs neither and can be generated with stdlib alone.
Recommend `pip install matplotlib pandas` (or confirm an existing venv with
these) before `run_ablation.py`'s plotting half is implemented; the
data-collection half (writing `eval_*.json`) has no such dependency.

---

## 6. `run_ablation.py` architecture sketch (design only — not written)

### Correction to the stated guardrail rationale (Rule 10)

The prompt's guardrail said `run_with_global()` "always runs full
pipeline" — checked against the actual code
(`outer_milp/utils/multi_week_runner.py:129-171`) and that's not accurate:
it's MILP-only (calls `model.solve()`, evaluates the raw MILP schedule, no
F&O, no SA call anywhere in the function), and it already accepts an
arbitrary non-sequential `weeks: list` + `history_variant: int` — it would
actually work as-is for `--mode milp` on any of the 28 instances. The real
reason not to reuse it: it only covers 1 of 3 needed modes, and splitting
"`milp` via `run_with_global()`, `fo`/`full` via new code" would create two
parallel MILP-build implementations — the implementation-drift risk Rule 11
warns about. **Same conclusion as the prompt** (one new mode-gated loop in
`run_ablation.py`), corrected reason (single source of truth for the
MILP-build step across all 3 modes).

### Confirmed-feasible building blocks

- `inrc2_parser.parse(instance_dir, week, history)` already takes
  independent `week` (arbitrary WD index, 0–9) and `history` (arbitrary H0
  index, 0–2) arguments — confirmed by reading
  `outer_milp/utils/inrc2_parser.py:34`. This is exactly what's needed to
  drive an arbitrary `week_sequence` like `[6, 1, 0, 6]`; no parser change
  needed.
- `history` is only meaningful for week 0 of a run — every subsequent
  week's `nurse_info[...]["history"]` is overwritten by
  `_end_of_week_history()`'s carry-forward immediately after `parse()` is
  called (confirmed in both `multi_week_runner.py` and
  `run_4week_full_pipeline.py`'s existing loops). `run_ablation.py` should
  follow the same pattern.
- **The SA seed is currently hardcoded** (`std::mt19937 rng(42);`,
  `inner_heuristic/src/heuristic.cpp:649`) with no CLI flag. The sketch
  below includes an optional `--seed N` flag per the segment's spec, but
  **that flag cannot do anything yet** — wiring it through would require
  editing `heuristic.cpp`/`main.cpp` to accept and thread a seed argument,
  which is a `.cpp` change outside this read-only segment's guardrail (and
  arguably outside the "Lead Architect, Outer-Layer Developer" boundary —
  worth flagging to the C++ teammate rather than doing unilaterally). For
  now the flag should be accepted but documented as a no-op, or omitted
  until that capability exists.

### Planned CLI interface

```
python3 evaluation/run_ablation.py \
    --instance n030w4_2_6-1-0-6 \
    --mode {milp|fo|full} \
    --output results/eval_<timestamp>.json \
    [--seed N]                      # currently a no-op, see above
    [--time-limit-per-week SECS]
```

### Planned internal structure

1. Parse `--instance` into `(dataset, history_index, week_sequence)` by
   splitting on `_` then `-` (mirrors the format confirmed in §2).
2. For `seq_idx, week_idx in enumerate(week_sequence)`:
   - `parse(instance_dir, week=week_idx, history=history_index)` (only
     `history_index` matters at `seq_idx == 0`; later weeks get carry).
   - Build + solve MILP (`model.build(is_final_week=..., cur_week=seq_idx+1,
     num_weeks=len(week_sequence))`, same call shape already used in
     `run_4week_full_pipeline.py` and `multi_week_runner.py`).
   - `if mode in ("fo", "full")`: run Fix-and-Optimize (reuse the `_run_fo`
     pattern from `run_4week_full_pipeline.py`).
   - `if mode == "full"`: write the exchange JSON and invoke the C++ binary
     (reuse the `_run_sa` pattern).
   - Evaluate the resulting schedule with `penalty_evaluator.evaluate()`;
     append to `per_week_breakdown`; carry history forward.
3. After the loop: `evaluate_global_s6_s7(weekly_schedules, nurse_info_w0,
   contracts)` for `global_s6`/`global_s7`.
4. Assemble one record per the §5 schema; append (not overwrite) to the
   `--output` JSON file, so multiple `run_ablation.py` invocations can
   accumulate into one `eval_<timestamp>.json` across a batch script.
5. Wrap the whole per-instance run in a wall-clock timer
   (`time.time()` before/after) for `wall_clock_seconds`.

Explicitly **not** done in this segment: no batch-driver script (e.g. a
loop over all 28 instances × 3 modes) was designed in detail — that's a
natural follow-up once `run_ablation.py` itself exists and the scope
question in §4 is settled, since the batch driver's iteration order depends
on which scope option is chosen.

---

## Open items for human review

1. **Finalist instance IDs**: fully recovered (28/28), high confidence
   (cross-validated against Ceschia 2019's own worked example). No fallback
   needed.
2. **Best-known costs**: fully recovered (28/28) from the organiser-validated
   spreadsheet. One data-quality discrepancy flagged (INF_UFRGS,
   submitted-vs-validated) — didn't block the table since validated is
   authoritative and cross-checked against the wider submitted set.
3. **Scope recommendation**: leaning **(d)** 1 instance/dataset × 3 configs
   (~10.9h, full N-range preserved for P3/P5) over (b)/(c), with the
   **hybrid** option (~13.0h) as a fallback if 2-instance replication for
   P1's box plots is wanted — needs your call.
4. **`run_ablation.py` architecture**: sketch above corrects the stated
   reason for not reusing `run_with_global()` (it's MILP-only, not
   "always full pipeline") but reaches the same conclusion (write one new
   mode-gated loop). Also flags that `--seed` is a no-op until `heuristic.cpp`
   is changed — needs your call on whether that's in scope for this
   evaluation effort or deferred.
5. **matplotlib/pandas**: confirmed absent, not installed per guardrail —
   needs your go-ahead to install before the plotting half of
   `run_ablation.py` (or a separate plotting script) can run.

---

## Scope Lock (2026-06-19)

The four open items above are now resolved. Locked decisions, verbatim:

1. **Scope: variant (d+).**
   - 1 instance per dataset for all 14 public-testbed datasets
     (the official finalist instance ID per recovery in 段0)
   - 3 modes per dataset: milp_only / milp_fo / full
   - Plus: in the 3 testdatasets (n005/n012/n021), run 2-3
     extra instances (random selection from available combos)
     in 'full' mode only, to get SA-on-different-seed-via-different-
     instance stability evidence
   - Estimated wall-clock: ~13 hours total, fits budget

2. **Runner architecture: B1 (new file `evaluation/run_ablation.py`).**
   - DO NOT reimplement any helper; import parse, MilpModel,
     F&O loop, runEvalOnly subprocess wrapper from existing
     modules.
   - Mode-gated execution: milp → milp+fo → milp+fo+sa
   - Per-week JSON output as designed in 段0

3. **SA seed: do NOT modify C++ in this evaluation work.**
   The heuristic.cpp hardcoded seed stays. Report it as a known
   limitation in the final write-up. SA-seed stability is
   approximated indirectly by running the testdataset extras
   on different starting instances.

4. **matplotlib/pandas: install at start of 段3, not now.**
   Command for then: `pip install --user matplotlib pandas`.

Next action is EVAL-段1 (implementation segment, writing
`evaluation/run_ablation.py`) — not started this session. Resuming
Friday morning.
