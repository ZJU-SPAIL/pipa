#!/usr/bin/env bash

set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Nginx - 终极自动化测试脚本 (v2)
# 职责: 编排一次完整的、可重复的 Nginx 性能分析实验。
# =================================================================

# --- 核心配置区 (可从 env.sh 覆盖) ---
DURATION_STAT=${DURATION_STAT:-60}
DURATION_RECORD=${DURATION_RECORD:-60}

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../" && pwd)
source "$SCRIPT_DIR/env.sh"

# --- Pipa 环境校验 ---
VENV_PATH="$PROJECT_ROOT/.venv"
PIPA_CMD="$VENV_PATH/bin/pipa"

log() {
    echo ""
    echo "--- [UltimateTest-Nginx] $1 ---"
}

if [ ! -x "$PIPA_CMD" ]; then
    log "❌ 致命错误: Pipa 命令未在 '$PIPA_CMD' 找到或不可执行。"
    log "   -> 请确保你已在项目根目录成功运行过 './setup.sh'。"
    exit 1
fi
log "   -> Pipa command found at: ${PIPA_CMD}"

# --- 健壮的清理机制 ---
cleanup() {
    log "测试结束，调用终极清理脚本..."
    "$SCRIPT_DIR/stop_nginx.sh"
}
trap cleanup EXIT

# --- 步骤 1: 环境准备与健康检查 ---
log "步骤 1: 运行 Pipa healthcheck..."
$PIPA_CMD healthcheck

# --- 步骤 2: 启动 Nginx 并捕获 PIDs ---
log "步骤 2: 启动 Nginx 服务器..."
START_OUTPUT=$("$SCRIPT_DIR/start_nginx.sh")
NGINX_PIDS=$(echo "${START_OUTPUT}" | grep "PIDs for pipa:" | awk '{print $NF}')

if [ -z "$NGINX_PIDS" ]; then
    log "❌ 致命错误: 未能从 start_nginx.sh 的输出中捕获到 PIDs。"
    exit 1
fi
log "   -> Nginx worker 进程已运行, PIDs: ${NGINX_PIDS}"

# --- 步骤 3: 启动负载 ---
log "步骤 3: 启动 WRK 负载..."
# 在后台启动一个持续时间足够长的负载
"$SCRIPT_DIR/run_load.sh" &
WRK_PID=$!
log "   -> WRK 已在后台启动 (PID: ${WRK_PID}). 等待 5 秒以稳定负载..."
sleep 5

# --- 步骤 4: 执行 Pipa 标准快照 ---
log "步骤 4: 执行 Pipa 标准两阶段快照 (${DURATION_STAT}s stat + ${DURATION_RECORD}s record)..."
SNAPSHOT_FILE="nginx_snapshot.pipa"
$PIPA_CMD sample \
    --attach-to-pid "${NGINX_PIDS}" \
    --duration-stat "${DURATION_STAT}" \
    --duration-record "${DURATION_RECORD}" \
    --output "${SNAPSHOT_FILE}"

log "   -> 快照捕获完成: ${SNAPSHOT_FILE}"

# --- 步骤 4: 自动分析并生成报告 ---
REPORT_FILE="nginx_report.html"
FLAMEGRAPH_FILE="nginx_flamegraph.svg"

log "步骤 4a: 分析快照并生成报告..."
$PIPA_CMD analyze \
    --input "${SNAPSHOT_FILE}" \
    --output "${REPORT_FILE}"

log "步骤 4b: 生成火焰图..."
$PIPA_CMD flamegraph \
    --input "${SNAPSHOT_FILE}" \
    --output "${FLAMEGRAPH_FILE}"

echo ""
echo "====================================================="
echo "✅ PIPA 性能收集与分析完成!"
echo "➡️  分析报告已生成: ${REPORT_FILE}"
echo "➡️  火焰图已生成: ${FLAMEGRAPH_FILE}"
echo "====================================================="
