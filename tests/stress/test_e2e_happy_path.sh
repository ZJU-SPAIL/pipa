#!/bin/bash
set -e

# =================================================================
# Operation Cerberus - Orthrus
# Core E2E Happy Path Smoke Test
# =================================================================

LOG_PREFIX="[Orthrus]"
RESULTS_DIR="test_results_$(date +%s)"

log() {
    echo ""
    echo "--- ${LOG_PREFIX} $1 ---"
}

cleanup() {
    log "Cleaning up..."
    if [ -n "$TARGET_PID" ] && kill -0 "$TARGET_PID" 2>/dev/null; then
        kill "$TARGET_PID"
    fi
    # rm -rf "$RESULTS_DIR" # 保留结果以便检查
    echo "✅ Test finished. Results are in '${RESULTS_DIR}/'"
}
trap cleanup EXIT

# --- 1. Setup ---
log "Step 1: Setting up environment..."
mkdir -p "$RESULTS_DIR"
# 启动一个会消耗一些 CPU 的目标进程
dd if=/dev/zero of=/dev/null &
TARGET_PID=$!
echo "   -> Target 'dd' process started with PID: ${TARGET_PID}"

# --- 2. Healthcheck ---
log "Step 2: Running 'pipa healthcheck'"
pipa healthcheck --output "${RESULTS_DIR}/static_info.yaml"
[ -f "${RESULTS_DIR}/static_info.yaml" ] && echo "   -> OK: static_info.yaml created." || (echo "   -> FAIL!" && exit 1)

# --- 3. Sample (Full Two-Phase) ---
log "Step 3: Running 'pipa sample' for a full snapshot"
pipa sample \
    --attach-to-pid "${TARGET_PID}" \
    --duration-stat 10 --duration-record 10 \
    --static-info-file "${RESULTS_DIR}/static_info.yaml" \
    --output "${RESULTS_DIR}/full_snapshot.pipa"
[ -f "${RESULTS_DIR}/full_snapshot.pipa" ] && echo "   -> OK: full_snapshot.pipa created." || (echo "   -> FAIL!" && exit 1)

# --- 4. Analyze ---
log "Step 4: Running 'pipa analyze'"
pipa analyze --input "${RESULTS_DIR}/full_snapshot.pipa" --output "${RESULTS_DIR}/analysis_report.html"
[ -f "${RESULTS_DIR}/analysis_report.html" ] && echo "   -> OK: analysis_report.html created." || (echo "   -> FAIL!" && exit 1)
grep -q "Decision Tree Visualization" "${RESULTS_DIR}/analysis_report.html" && echo "   -> OK: Report content looks valid." || (echo "   -> FAIL!" && exit 1)

# --- 5. Flamegraph ---
log "Step 5: Running 'pipa flamegraph'"
pipa flamegraph --input "${RESULTS_DIR}/full_snapshot.pipa" --output "${RESULTS_DIR}/flamegraph.svg"
[ -f "${RESULTS_DIR}/flamegraph.svg" ] && echo "   -> OK: flamegraph.svg created." || (echo "   -> FAIL!" && exit 1)
grep -q "<title>dd" "${RESULTS_DIR}/flamegraph.svg" && echo "   -> OK: Flamegraph content seems to target 'dd'." || (echo "   -> WARN: Could not validate flamegraph content." && sleep 1)

# --- 6. Compare ---
log "Step 6: Running 'pipa compare'"
# 创建一个简单的 "stat-only" 快照用于对比
pipa sample \
    --attach-to-pid "${TARGET_PID}" \
    --duration-stat 5 --no-record \
    --static-info-file "${RESULTS_DIR}/static_info.yaml" \
    --output "${RESULTS_DIR}/stat_only.pipa"
pipa compare \
    --input-a "${RESULTS_DIR}/stat_only.pipa" \
    --input-b "${RESULTS_DIR}/full_snapshot.pipa" \
    --output "${RESULTS_DIR}/comparison.html"
[ -f "${RESULTS_DIR}/comparison.html" ] && echo "   -> OK: comparison.html created." || (echo "   -> FAIL!" && exit 1)
grep -q "PIPA Performance Comparison Report" "${RESULTS_DIR}/comparison.html" && echo "   -> OK: Comparison report content looks valid." || (echo "   -> FAIL!" && exit 1)

log "All happy path tests PASSED!"
