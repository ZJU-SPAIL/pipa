#!/bin/bash
set -e

# =================================================================
# Operation Cerberus - Sphinx
# Boundary Conditions & Invalid Input Test
# =================================================================

LOG_PREFIX="[Sphinx]"
RESULTS_DIR="test_results_sphinx_$(date +%s)"

log() {
    echo ""
    echo "--- ${LOG_PREFIX} $1 ---"
}

cleanup() {
    log "Cleaning up..."
    # rm -rf "$RESULTS_DIR"
    echo "✅ Sphinx tests complete. Results are in '${RESULTS_DIR}/'"
}
trap cleanup EXIT

# --- 1. Setup ---
log "Step 1: Setting up environment..."
mkdir -p "$RESULTS_DIR"
pipa healthcheck --output "${RESULTS_DIR}/static_info.yaml"
echo "   -> A valid static info file has been created for tests."

# --- 2. Test Case: Sampling a Non-Existent PID ---
log "Step 2: Testing 'pipa sample' with a non-existent PID"
NON_EXISTENT_PID="999999"
set +e # 允许命令失败
pipa sample --attach-to-pid $NON_EXISTENT_PID --duration-stat 5 --no-record --output "${RESULTS_DIR}/fail.pipa" > "${RESULTS_DIR}/non_existent_pid.log" 2>&1
EXIT_CODE=$?
set -e
if [ $EXIT_CODE -ne 0 ]; then
    echo "   -> OK: Command failed as expected."
    grep -q "Process with PID '999999' does not exist" "${RESULTS_DIR}/non_existent_pid.log" && echo "   -> OK: Correct pre-flight check error message." || (echo "   -> FAIL: Incorrect error message!" && exit 1)
else
    echo "   -> FAIL: Command should have failed but it succeeded!"
    exit 1
fi

# --- 3. Test Case: Sampling with --no-stat and --no-record ---
log "Step 3: Testing 'pipa sample' with both phases disabled"
set +e
pipa sample --attach-to-pid 123 --no-stat --no-record --output "${RESULTS_DIR}/fail.pipa" > "${RESULTS_DIR}/no_phases.log" 2>&1
EXIT_CODE=$?
set -e
if [ $EXIT_CODE -ne 0 ]; then
    echo "   -> OK: Command failed as expected."
    grep -q "Cannot specify both --no-stat and --no-record" "${RESULTS_DIR}/no_phases.log" && echo "   -> OK: Correct error message." || (echo "   -> FAIL: Incorrect error message!" && exit 1)
else
    echo "   -> FAIL: Command should have failed but it succeeded!"
    exit 1
fi

# --- 4. Test Case: Analyzing a snapshot with MISSING perf.data ---
log "Step 4: Testing 'pipa analyze' on a snapshot without perf.data"
# 启动一个目标
sleep 300 &
TARGET_PID=$!
# 创建一个只有 stat 的快照
pipa sample \
    --attach-to-pid $TARGET_PID \
    --duration-stat 5 --no-record \
    --static-info-file "${RESULTS_DIR}/static_info.yaml" \
    --output "${RESULTS_DIR}/stat_only.pipa"
kill $TARGET_PID
# 分析它
pipa analyze --input "${RESULTS_DIR}/stat_only.pipa" --output "${RESULTS_DIR}/stat_only_report.html"
echo "   -> OK: 'analyze' command completed without crashing."
# 深度内容验证
grep -q "sar_cpu_all" "${RESULTS_DIR}/stat_only_report.html" && echo "   -> OK: SAR plot is present." || (echo "   -> FAIL: SAR plot is missing!" && exit 1)
grep -v -q "perf_stat" "${RESULTS_DIR}/stat_only_report.html" && echo "   -> OK: Perf plot is correctly absent." || (echo "   -> FAIL: Perf plot should be absent but was found!" && exit 1)
grep -q "perf.data not found" "${RESULTS_DIR}/stat_only_report.html" && echo "   -> OK: A warning for missing perf.data is present." || (echo "   -> FAIL: Missing perf.data warning not found!" && exit 1)

# --- 5. Test Case: Generating a flamegraph from a snapshot WITHOUT perf.data ---
log "Step 5: Testing 'pipa flamegraph' on a snapshot without perf.data"
set +e
pipa flamegraph --input "${RESULTS_DIR}/stat_only.pipa" --output "${RESULTS_DIR}/fail.svg" > "${RESULTS_DIR}/no_perf_data.log" 2>&1
EXIT_CODE=$?
set -e
if [ $EXIT_CODE -ne 0 ]; then
    echo "   -> OK: Command failed as expected."
    grep -q "perf.data not found" "${RESULTS_DIR}/no_perf_data.log" && echo "   -> OK: Correct error message." || (echo "   -> FAIL: Incorrect error message!" && exit 1)
else
    echo "   -> FAIL: Command should have failed but it succeeded!"
    exit 1
fi

log "All boundary condition tests PASSED!"
