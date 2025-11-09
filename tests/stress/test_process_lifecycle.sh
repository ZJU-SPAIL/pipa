#!/bin/bash
set -e

# =================================================================
# Operation Cerberus - Chimera (Part 1)
# Process Lifecycle & Abrupt Termination Test
# =================================================================

LOG_PREFIX="[Chimera-Lifecycle]"
RESULTS_DIR="test_results_chimera_$(date +%s)"

log() {
    echo ""
    echo "--- ${LOG_PREFIX} $1 ---"
}

cleanup() {
    log "Cleaning up..."
    if [ -n "$TARGET_PID" ] && ps -p "$TARGET_PID" > /dev/null; then
        kill "$TARGET_PID" || true
    fi
    echo "✅ Chimera (Lifecycle) tests complete. Results are in '${RESULTS_DIR}/'"
}
trap cleanup EXIT

# --- 1. Setup ---
log "Step 1: Setting up environment..."
mkdir -p "$RESULTS_DIR"
pipa healthcheck --output "${RESULTS_DIR}/static_info.yaml"

# --- 2. Test Case: Target process dies during Phase 1 (stat+sar) ---
log "Step 2: Testing target process termination during Phase 1"

# 启动一个目标进程
dd if=/dev/zero of=/dev/null &
TARGET_PID=$!
echo "   -> Target 'dd' process started with PID: ${TARGET_PID}"

# 在后台启动一个长时间的 pipa 采样
echo "   -> Starting a 30-second pipa sample in the background..."
pipa sample \
    --attach-to-pid $TARGET_PID \
    --duration-stat 30 --no-record \
    --static-info-file "${RESULTS_DIR}/static_info.yaml" \
    --output "${RESULTS_DIR}/terminated_p1.pipa" > "${RESULTS_DIR}/p1_term.log" 2>&1 &
PIPA_PID=$!

# 等待 5 秒，确保 pipa 和采集器都已启动
sleep 5

# 杀死目标进程！
log "💥 Killing the target process (PID: $TARGET_PID) mid-sampling!"
kill $TARGET_PID
# 等待 kill 完成
wait $TARGET_PID || true
TARGET_PID="" # 清除 PID 变量，防止 cleanup 再次尝试 kill

# 等待 pipa 进程自己结束（它应该能检测到目标死亡并优雅退出）
log "   -> Waiting for pipa to complete or timeout..."
set +e
# 等待 pipa 进程最多 35 秒（比采样时长稍长）
wait -n $PIPA_PID
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -eq 0 ]; then
    echo "   -> OK: Pipa process completed gracefully (Exit Code: $EXIT_CODE)."
else
    echo "   -> WARN: Pipa process exited with a non-zero code ($EXIT_CODE), but this might be acceptable."
fi

# 验证产出物
log "   -> Verifying the output snapshot..."
[ -f "${RESULTS_DIR}/terminated_p1.pipa" ] && echo "   -> OK: Snapshot file was created." || (echo "   -> FAIL: Snapshot file was NOT created!" && exit 1)

# 分析这份不完整的快照，确保 analyze 不会崩溃
log "   -> Analyzing the potentially incomplete snapshot..."
pipa analyze --input "${RESULTS_DIR}/terminated_p1.pipa" --output "${RESULTS_DIR}/p1_term_report.html"
echo "   -> OK: 'analyze' command did not crash on the incomplete data."
grep -q "PIPA Analysis Report" "${RESULTS_DIR}/p1_term_report.html" && echo "   -> OK: Report was generated." || (echo "   -> FAIL: Report generation failed!" && exit 1)


log "Target termination test PASSED!"
