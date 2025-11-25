#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Ultimate IO - 终极测试脚本 (FIO版)
# =================================================================

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../" && pwd)
source "$SCRIPT_DIR/env.sh"

# --- 输出定义 ---
FOLDER_NAME="io_intensive"
SNAPSHOT_FILE="${FOLDER_NAME}_snapshot.pipa"
REPORT_FILE="${FOLDER_NAME}_report.html"

VENV_PATH="$PROJECT_ROOT/.venv"
PIPA_CMD="$VENV_PATH/bin/pipa"

log() {
    echo ""
    echo "--- [Ultimate-IO] $1 ---"
}

if [ ! -x "$PIPA_CMD" ]; then
    log "❌ Pipa 未安装。请检查是否激活了虚拟环境。"
    exit 1
fi

# 清理钩子
cleanup() {
    log "清理后台进程..."
    pkill -f "fio" || true
}
trap cleanup EXIT

# 1. 环境检查
log "Step 1: Checking Environment..."
"$SCRIPT_DIR/setup.sh"

# 2. 健康检查
log "Step 2: Running Healthcheck..."
$PIPA_CMD healthcheck

# 3. 启动负载
log "Step 3: Starting FIO in background..."
# 重定向输出，避免刷屏
"$SCRIPT_DIR/run_load.sh" > "$SCRIPT_DIR/fio_run.log" 2>&1 &
LOAD_PID=$!

log "   -> FIO running (PID: $LOAD_PID). Logs: $SCRIPT_DIR/fio_run.log"
log "   -> Waiting 10 seconds for IO saturation..."
sleep 10

# 4. 采样
log "Step 4: PIPA Sampling..."
$PIPA_CMD sample \
    --system-wide \
    --duration-stat 60 \
    --no-record \
    --output "$SNAPSHOT_FILE"

# 5. 分析
log "Step 5: Analyzing..."
$PIPA_CMD analyze \
    --input "$SNAPSHOT_FILE" \
    --output "$REPORT_FILE"

echo ""
echo "====================================================="
echo "✅ IO TEST COMPLETE"
echo "➡️  Report: $REPORT_FILE"
echo "====================================================="
