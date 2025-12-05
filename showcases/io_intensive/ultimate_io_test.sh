#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Ultimate IO - 终极测试脚本 (FIO版)
# =================================================================

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../" && pwd)

# --- 日志函数（必须先定义）---
log() {
    echo ""
    echo "--- [Ultimate-IO] $1 ---"
}

# ==================== 安全检查 ====================
SAFETY_GUARD_SCRIPT="$PROJECT_ROOT/showcases/safety-guard.sh"
if [ -f "$SAFETY_GUARD_SCRIPT" ]; then
    source "$SAFETY_GUARD_SCRIPT"
else
    echo "⚠️ 警告: 未找到安全检查脚本: $SAFETY_GUARD_SCRIPT"
fi
# =======================================================

source "$SCRIPT_DIR/env.sh"

VENV_PATH="$PROJECT_ROOT/.venv"
PIPA_CMD="$VENV_PATH/bin/pipa"

# --- Evidence 目录与场景定义 ---
SCENARIO="io_intensive_fio"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EVIDENCE_DIR="$PROJECT_ROOT/evidence/${TIMESTAMP}_${SCENARIO}"
mkdir -p "$EVIDENCE_DIR"
log "📂 Evidence Directory: $EVIDENCE_DIR"

# --- 输出定义 ---
FOLDER_NAME="io_intensive"

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
# 重定向输出到 Evidence 目录
"$SCRIPT_DIR/run_load.sh" > "$EVIDENCE_DIR/fio_run.log" 2>&1 &
LOAD_PID=$!

log "   -> FIO running (PID: $LOAD_PID). Logs: fio_run.log"
log "   -> Waiting 10 seconds for IO saturation..."
sleep 10

# 4. 采样
log "Step 4: PIPA Sampling..."
$PIPA_CMD sample \
    --system-wide \
    --duration-stat 60 \
    --no-record \
    --output "$EVIDENCE_DIR/snapshot.pipa"

# 5. 分析
log "Step 5: Analyzing..."
$PIPA_CMD analyze \
    --input "$EVIDENCE_DIR/snapshot.pipa" \
    --output "$EVIDENCE_DIR/report.html"

# 6. 配置留痕
log "Step 6: Archiving evidence..."
cp "$SCRIPT_DIR/env.sh" "$EVIDENCE_DIR/env_snapshot.sh"

echo ""
echo "====================================================="
echo "✅ IO TEST COMPLETE"
echo "📂 证据已归档至: $EVIDENCE_DIR"
echo "➡️  分析报告: report.html"
echo "====================================================="
