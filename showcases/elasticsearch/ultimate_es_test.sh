#!/bin/bash
set -e
set -o pipefail

# =================================================================
# PIPA 终极试炼: Elasticsearch Showcase
# 职责: 自动化执行一个完整的“启动->施压->采样->分析”工作流。
# 这是对 pipa 观察者哲学的终极展示。
# =================================================================

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
# 项目根目录是 showcase 目录的父目录
SHOWCASE_DIR="$SCRIPT_DIR"
PROJECT_ROOT=$(cd "$SHOWCASE_DIR/.." && pwd)

# --- Pipa 环境校验 ---
VENV_PATH="$PROJECT_ROOT/.venv"
PIPA_CMD="$VENV_PATH/bin/pipa"

if [ ! -x "$PIPA_CMD" ]; then
    log "❌ 致命错误: Pipa 命令未在 '$PIPA_CMD' 找到或不可执行。"
    log "   -> 请确保你已在项目根目录成功运行过 './setup.sh'。"
    exit 1
fi
log "   -> Pipa command found at: ${PIPA_CMD}"

log() {
    echo ""
    echo "--- [UltimateTest-ES] $1 ---"
}

# --- 健壮的清理机制 ---
cleanup() {
    log "执行清理..."
    # 停止负载生成器（如果仍在运行）
    pkill -f esrally || true
    # 调用标准停止脚本来停止 ES 集群
    "$SHOWCASE_DIR/stop_es.sh"
    log "✅ 测试结束。"
}
trap cleanup EXIT

# --- 步骤 1: 启动 Elasticsearch 集群并捕获 PIDs ---
log "步骤 1: 启动 Elasticsearch 集群..."
source "$SHOWCASE_DIR/env.sh"
# 执行启动脚本并捕获其所有输出
START_OUTPUT=$("$SHOWCASE_DIR/start_es.sh")
# 从输出中精确提取我们需要的 PID 列表
ES_PIDS=$(echo "${START_OUTPUT}" | grep "PIDs for pipa:" | awk '{print $NF}')

if [ -z "$ES_PIDS" ]; then
    log "❌ 致命错误: 未能从 start_es.sh 的输出中捕获到 PIDs。"
    exit 1
fi
log "   -> ES 集群已运行, PIDs: ${ES_PIDS}"

# --- 步骤 2: 在后台施加负载 ---
log "步骤 2: 在后台施加 esrally 负载..."
"$SHOWCASE_DIR/run_load.sh" &
ESRALLY_PID=$!
log "   -> esrally 已在后台启动 (PID: ${ESRALLY_PID}). 等待 30 秒让负载稳定..."
sleep 30

# --- 步骤 3: 运行 Pipa 健康检查 (最佳实践) ---
log "步骤 3: 运行 $PIPA_CMD healthcheck..."
$PIPA_CMD healthcheck

# --- 步骤 4: 执行 Pipa 标准快照 ---
log "步骤 4: 执行 Pipa 标准两阶段快照 (30s stat + 30s record)..."
$PIPA_CMD sample \
    --attach-to-pid "${ES_PIDS}" \
    --duration-stat 30 \
    --duration-record 30 \
    --output es_ultimate_snapshot.pipa

log "   -> 快照捕获完成。"

# --- 步骤 5: 分析快照并生成报告 ---
log "步骤 5: 分析快照..."
$PIPA_CMD analyze \
    --input es_ultimate_snapshot.pipa \
    --output es_ultimate_report.html

# --- 步骤 6: 生成火焰图 ---
log "步骤 6: 生成火焰图..."
$PIPA_CMD flamegraph \
    --input es_ultimate_snapshot.pipa \
    --output es_ultimate_flamegraph.svg


echo ""
echo "====================================================="
echo "✅ ELASTICSEARCH 终极测试完成!"
echo "➡️  分析报告已生成: es_ultimate_report.html"
echo "➡️  火焰图已生成: es_ultimate_flamegraph.svg"
echo "====================================================="
