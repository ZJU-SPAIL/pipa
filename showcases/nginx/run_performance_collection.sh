#!/usr/bin/env bash

set -e
set -o pipefail

# =================================================================
# Pipa Showcase: 运行 Nginx 性能基准测试和 Pipa 数据收集 (已重构)
# 职责: 启动 WRK 压测，并使用 Pipa 对 Nginx worker 进程进行性能采样和分析。
# =================================================================

# 获取脚本自身所在的目录
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh" # 加载所有环境变量

log() {
    echo ""
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - $1"
}

# --- 假设 Pipa 在项目根目录的 .venv 中 ---
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../" && pwd)
PIPA_CMD="$PROJECT_ROOT/.venv/bin/pipa"

if [ ! -x "$PIPA_CMD" ]; then
    log "❌ 致命错误: Pipa 命令未在 '$PIPA_CMD' 找到或不可执行。"
    exit 1
fi

# --- 清理机制 ---
cleanup() {
    log "脚本结束或中断，正在清理后台进程..."
    # 使用 pkill 确保 wrk 进程被终止
    pkill -f wrk || true
    log "✅ 清理完成。"
}
trap cleanup EXIT

# --- 步骤 1: 启动 WRK 负载 (后台运行) ---
log "步骤 1: 在后台启动 WRK 负载..."
taskset -c "$WRK_CPU_AFFINITY" "$WRK_INSTALL_DIR/bin/wrk" \
    -t"$WRK_THREADS" -c"$WRK_CONNECTIONS" -d"$WRK_DURATION" \
    -H "Connection: keep-alive" "$WRK_TARGET_URL" > /dev/null 2>&1 &
WRK_PID=$!
log "   -> WRK 已在后台启动 (PID: ${WRK_PID})."

# --- 步骤 2: 查找 Nginx Worker 进程 PIDs ---
log "步骤 2: 查找 Nginx worker 进程 PIDs..."
sleep 2 # 等待 Nginx 稳定响应负载
NGINX_PIDS=$(pgrep -f "nginx: worker process" | tr '\n' ',' | sed 's/,$//')

if [ -z "$NGINX_PIDS" ]; then
    log "❌ 错误: 未能找到任何正在运行的 Nginx worker 进程。请确保 Nginx 已启动。"
    exit 1
fi
log "   -> 成功找到 Nginx worker 进程, PIDs: ${NGINX_PIDS}"

# --- 步骤 3: 运行 Pipa 进行采样 ---
log "步骤 3: 执行 Pipa 标准两阶段快照 (${DURATION_STAT}s stat + ${DURATION_RECORD}s record)..."
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

# 等待后台的 wrk 进程自然结束
wait $WRK_PID 2>/dev/null || true
