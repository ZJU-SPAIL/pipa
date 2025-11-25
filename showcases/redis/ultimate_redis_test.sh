#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Redis - 终极自动化测试脚本
# =================================================================

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../" && pwd)
source "$SCRIPT_DIR/env.sh"

# --- 动态文件名生成 ---
FOLDER_NAME=$(basename "$SCRIPT_DIR")
SNAPSHOT_FILE="${FOLDER_NAME}_snapshot.pipa"
REPORT_FILE="${FOLDER_NAME}_report.html"
FLAMEGRAPH_FILE="${FOLDER_NAME}_flamegraph.svg"

# --- Pipa 环境校验 ---
VENV_PATH="$PROJECT_ROOT/.venv"
PIPA_CMD="$VENV_PATH/bin/pipa"

log() {
    echo ""
    echo "--- [UltimateTest-Redis] $1 ---"
}

if [ ! -x "$PIPA_CMD" ]; then
    log "❌ 致命错误: Pipa 命令未在 '$PIPA_CMD' 找到或不可执行。"
    exit 1
fi

# --- 健壮的清理机制 ---
cleanup() {
    log "测试结束，调用终极清理脚本..."
    "$SCRIPT_DIR/stop_redis.sh"
}
trap cleanup EXIT

# --- 步骤 0: 自动化环境准备 ---
log "步骤 0: 确保环境已准备就绪..."
"$SCRIPT_DIR/setup.sh"

# --- 步骤 1: 健康检查 ---
log "步骤 1: 运行 Pipa healthcheck..."
$PIPA_CMD healthcheck

# --- 步骤 2: 启动 Redis 并捕获 PID ---
log "步骤 2: 启动 Redis 服务器..."
START_OUTPUT=$("$SCRIPT_DIR/start_redis.sh")
REDIS_PID=$(echo "${START_OUTPUT}" | grep "PIDs for pipa:" | awk '{print $NF}')

if [ -z "$REDIS_PID" ]; then
    log "❌ 致命错误: 未能从 start_redis.sh 的输出中捕获到 PID。"
    exit 1
fi
log "   -> Redis 已运行, PID: ${REDIS_PID}"

# --- 步骤 3: 启动负载 ---
log "步骤 3: 在后台启动 redis-benchmark 负载..."
"$SCRIPT_DIR/run_load.sh" > /dev/null 2>&1 &
LOAD_PID=$!
log "   -> redis-benchmark 已在后台启动 (PID: ${LOAD_PID}). 等待 5 秒以稳定负载..."
sleep 5

# --- 步骤 4: 执行 Pipa 标准快照 ---
log "步骤 4: 执行 Pipa 标准两阶段快照 (${DURATION_STAT}s stat + ${DURATION_RECORD}s record)..."
$PIPA_CMD sample \
    --attach-to-pid "${REDIS_PID}" \
    --duration-stat "${DURATION_STAT}" \
    --duration-record "${DURATION_RECORD}" \
    --output "${SNAPSHOT_FILE}"

log "   -> 快照捕获完成: ${SNAPSHOT_FILE}"

# --- 步骤 5: 分析快照并生成报告 ---
log "步骤 5a: 分析快照并生成报告..."
$PIPA_CMD analyze \
    --input "${SNAPSHOT_FILE}" \
    --output "${REPORT_FILE}"

log "步骤 5b: 生成火焰图..."
$PIPA_CMD flamegraph \
    --input "${SNAPSHOT_FILE}" \
    --output "${FLAMEGRAPH_FILE}"

echo ""
echo "====================================================="
echo "✅ REDIS 终极测试完成!"
echo "➡️  分析报告已生成: ${REPORT_FILE}"
echo "➡️  火焰图已生成: ${FLAMEGRAPH_FILE}"
echo "====================================================="
