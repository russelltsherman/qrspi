#!/bin/bash
set -euo pipefail

# QRSPI Eval Loop — Orchestrates one full optimization cycle
#
# Usage:
#   ./run_loop.sh <skill_path> <eval_suite> [max_iterations] [target_score]
#
# Example:
#   ./run_loop.sh .qrspi/agents/01-questions.md evals/suite.json 5 0.85

SKILL_PATH=${1:?Usage: run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]}
EVAL_SUITE=${2:?Usage: run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]}
MAX_ITER=${3:-5}
TARGET_SCORE=${4:-0.85}
TRIALS=${TRIALS:-3}
WORKERS=${WORKERS:-4}

echo "╔══════════════════════════════════════════╗"
echo "║        QRSPI Eval Optimization Loop      ║"
echo "╠══════════════════════════════════════════╣"
echo "║ Skill:    ${SKILL_PATH}"
echo "║ Suite:    ${EVAL_SUITE}"
echo "║ Max iter: ${MAX_ITER}"
echo "║ Target:   ${TARGET_SCORE}"
echo "║ Trials:   ${TRIALS}"
echo "╚══════════════════════════════════════════╝"
echo ""

PREVIOUS_SCORE=0

for i in $(seq 1 "$MAX_ITER"); do
    VERSION="v${i}"
    OUTPUT_DIR="results/${VERSION}"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Iteration ${i}/${MAX_ITER}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # ── Step 1: Run evals ──
    echo "[1/4] Running eval suite (${TRIALS} trials per case)..."
    python3 scripts/run_eval.py \
        --skill "$SKILL_PATH" \
        --suite "$EVAL_SUITE" \
        --output "$OUTPUT_DIR" \
        --trials "$TRIALS" \
        --workers "$WORKERS"
    echo ""

    # ── Step 2: Grade ──
    echo "[2/4] Grading results..."
    python3 scripts/grade.py \
        --results "${OUTPUT_DIR}/results.json" \
        --suite "$EVAL_SUITE"
    echo ""

    # ── Step 3: Check target ──
    SCORE=$(python3 -c "
import json
with open('${OUTPUT_DIR}/grades.json') as f:
    g = json.load(f)
print(g.get('test_score', 0))
")

    echo "  Score: ${SCORE} (target: ${TARGET_SCORE})"

    # Check if target met
    TARGET_MET=$(python3 -c "print(1 if float('${SCORE}') >= float('${TARGET_SCORE}') else 0)")
    if [ "$TARGET_MET" = "1" ]; then
        echo ""
        echo "  ✓ Target score reached!"
        break
    fi

    # Check for regression
    REGRESSED=$(python3 -c "
prev = float('${PREVIOUS_SCORE}')
curr = float('${SCORE}')
threshold = 0.05
print(1 if prev > 0 and (prev - curr) > threshold else 0)
")

    if [ "$REGRESSED" = "1" ]; then
        echo ""
        echo "  ⚠ Regression detected (${PREVIOUS_SCORE} → ${SCORE})"
        echo "  Rolling back last revision..."
        # In a real loop: git checkout HEAD~1 -- "$SKILL_PATH"
        echo "  (rollback would restore previous skill version)"
        continue
    fi

    # ── Step 4: Diagnose + Revise ──
    echo ""
    echo "[3/4] Diagnosing failures..."
    python3 scripts/diagnose.py \
        --grades "${OUTPUT_DIR}/grades.json" \
        --skill "$SKILL_PATH" \
        --output "${OUTPUT_DIR}/diagnosis.json"
    echo ""

    echo "[4/4] Proposing revisions..."
    python3 scripts/revise.py \
        --skill "$SKILL_PATH" \
        --diagnosis "${OUTPUT_DIR}/diagnosis.json" \
        --output "$SKILL_PATH"
    echo ""

    PREVIOUS_SCORE=$SCORE
    echo "  Continuing to next iteration..."
    echo ""
done

# ── Final report ──
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Generating final report"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 scripts/report.py \
    --results-dir results/ \
    --output results/report.json
