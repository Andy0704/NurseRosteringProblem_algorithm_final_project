# NRP Project Skills

Project-level skills for the INRC-II Nurse Rostering Problem solver.
All commands are run from the repository root unless noted.

---

## skill_compile_and_test

Rebuild the C++ heuristic from scratch and confirm the binary is produced.

```bash
cd inner_heuristic && mkdir -p build && cd build \
  && cmake .. -DCMAKE_BUILD_TYPE=Release \
  && make -j4 \
  && echo "BUILD OK"
```

**What to check:** CMake configure must not report missing headers; `make` must
exit 0; `BUILD OK` must appear at the end. Any error in JSON parsing or
`heuristic.h` inclusion means `nlohmann/json.hpp` is missing — re-run:
```bash
curl -L https://github.com/nlohmann/json/releases/latest/download/json.hpp \
  -o inner_heuristic/include/nlohmann/json.hpp
```

---

## skill_run_pipeline

Parse one INRC-II instance week, run the C++ binary against it, then
validate the output schema.

```bash
# Step 1 — convert INRC-II files to exchange format
python3 outer_milp/utils/inrc2_parser.py \
    --instance data/raw_inrc2/testdatasets_json/n005w4 \
    --week 0 \
    --history 0 \
    --output data/exchange/problem_exchange.json

# Step 2 — run heuristic (reads AND writes back to the same file in-place)
inner_heuristic/build/nrp_heuristic data/exchange/problem_exchange.json

# Step 3 — validate the updated exchange file
python3 outer_milp/utils/validate_schema.py data/exchange/problem_exchange.json
```

**Notes:**
- `nrp_heuristic` takes exactly one argument (the exchange file path) and
  overwrites it with the result. There is no separate output path.
- Instance path includes `testdatasets_json/` subdirectory.
- The current heuristic is a stub (returns data unchanged); the pipeline
  still exercises the full parse → binary → validate chain.

---

## skill_check_penalty

Validate a problem_exchange.json file against the INRC-II exchange schema.

```bash
python3 outer_milp/utils/validate_schema.py data/exchange/problem_exchange.json
```

Exits `0` and prints `VALID`; exits `1` with a descriptive message on the
first schema violation found.

**TODO:** `--verbose` mode (show per-field details) is not yet implemented in
`validate_schema.py`. Add a `--verbose` flag there when soft-constraint
penalty reporting is needed.

---

## skill_git_checkpoint

Stage all changes and commit with a datestamp message.

```bash
git add -A && git commit -m "checkpoint: $(date +%Y%m%d_%H%M)"
```

**When to use:** After each completed implementation step (per CLAUDE.md Rule 6:
step-by-step reporting). Do not use to skip pre-commit hooks (`--no-verify`).

---

## skill_inrc2_benchmark

Run the full parse → heuristic pipeline across all 10 week-data files for
`n005w4` and report per-week validation status.

```bash
for week in $(seq 0 9); do
    python3 outer_milp/utils/inrc2_parser.py \
        --instance data/raw_inrc2/testdatasets_json/n005w4 \
        --week "$week" \
        --history 0 \
        --output data/exchange/problem_exchange.json \
    && inner_heuristic/build/nrp_heuristic data/exchange/problem_exchange.json \
    && result=$(python3 outer_milp/utils/validate_schema.py data/exchange/problem_exchange.json 2>&1) \
    && echo "Week $week: $result" \
    || echo "Week $week: FAILED"
done
```
## skill_resume_session
- 描述：銜接上次進度，掃描最近修改的檔案並總結狀態
- 執行：find . -type f -newer CLAUDE.md -not -path './.git/*' | head -20

## skill_full_benchmark
- 描述：對 n005w4 跑完整 4 週並輸出 penalty 報告
- 執行：python3 outer_milp/utils/multi_week_runner.py --instance data/raw_inrc2/testdatasets_json/n005w4

## skill_run_tests
- 描述：跑完整測試套件
- 執行：cd /mnt/c/Project/NRP_algorithm_lab/NRP_Claude_Agent && python3 -m pytest tests/ -v

## skill_git_checkpoint
- 描述：提交當前進度到 git
- 執行：git add -A && git commit -m "checkpoint: $(date +%Y%m%d_%H%M)"

## skill_chinese_output
- 描述：切換 Claude 本次對話的回覆語言為繁體中文，程式碼、變數名稱、註解維持全英文
- 使用方式：在 prompt 開頭加入以下指令
- 指令內容：
  For this response and all subsequent responses in this session:
  - Reply in Traditional Chinese (繁體中文) for all explanations, summaries, and reports
  - Keep ALL code, variable names, function names, comments, and file paths in English
  - Format: [中文說明] → [English code block]


**Notes:**
- MILP (`MilpModel.build/solve`) is not yet implemented; this skill exercises
  the parser + C++ stub only.
- Once `MilpModel` is implemented, insert
  `python3 outer_milp/main.py --config config.json` between parse and heuristic
  steps and replace the inline loop with a proper config-driven run.
- "Total penalty per week" requires a penalty evaluator (not yet built).
  Add `outer_milp/utils/penalty_evaluator.py` and call it here when ready.
