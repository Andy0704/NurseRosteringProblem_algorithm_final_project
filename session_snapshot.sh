#!/usr/bin/env bash
# Session-end snapshot: collect the core handoff set for upload to project files.
# Place this in NRP_Claude_Agent/ root (same level as outer_milp/, tests/, references/).
set -e
cd "$(dirname "$0")"

OUT="session_snapshot"
rm -rf "$OUT" && mkdir -p "$OUT/references" "$OUT/skills"

# 1. core handoff files (real paths)
cp CLAUDE.md PROJECT_STATUS.md ARCHITECTURE.md README.md config.json "$OUT/" 2>/dev/null || true
cp data/exchange/problem_exchange.json "$OUT/" 2>/dev/null || true
cp skills/SKILL.md "$OUT/skills/" 2>/dev/null || true
cp references/SA_IDENTITY_DIAGNOSTIC.md references/benchmark_results.md "$OUT/references/" 2>/dev/null || true

# 2. fresh source tree (replaces the old structure.txt)
find . -type f \( -name '*.py' -o -name '*.cpp' -o -name '*.h' -o -name '*.md' -o -name '*.json' \) \
  -not -path './.git/*' -not -path './build/*' -not -path './inner_heuristic/build/*' \
  -not -path './data/raw_inrc2/*' -not -path "./$OUT/*" -not -path './.pytest_cache/*' \
  | sort > "$OUT/TREE.txt"

# 3. test status (so status claims are backed by reality)
python3 -m pytest tests/ -q > "$OUT/TEST_STATUS.txt" 2>&1 || true

# 4. git state
{ echo "HEAD: $(git rev-parse --short HEAD)"; echo "--- status ---"; git status --short; } \
  > "$OUT/GIT_STATE.txt" 2>&1 || true

echo "Snapshot ready in ./$OUT/  — upload its contents to project files."
ls -R "$OUT"
