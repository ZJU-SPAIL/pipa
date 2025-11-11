#!/bin/bash
set -e
set -o pipefail

# =================================================================
# PIPA 终极试炼: Elasticsearch Showcase (v3 - 信号驱动 & 配置化)
# 职责: 自动化执行一个完整的“启动->施压->采样->分析”工作流。
# 这是对 pipa 观察者哲学的终极展示。
# =================================================================

# --- 核心配置区 ---
DURATION_STAT=60
DURATION_RECORD=60
ESRALLY_PROBE_TIMEOUT=300 # 最长等待 5 分钟

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
SHOWCASE_DIR="$SCRIPT_DIR"
PROJECT_ROOT=$(cd "$SHOWCASE_DIR/../../" && pwd)

# --- Pipa 环境校验 ---
VENV_PATH="$PROJECT_ROOT/.venv"
PIPA_CMD="$VENV_PATH/bin/pipa"

log() {
    echo ""
    echo "--- [UltimateTest-ES] $1 ---"
}

if [ ! -x "$PIPA_CMD" ]; then
    log "❌ 致命错误: Pipa 命令未在 '$PIPA_CMD' 找到或不可执行。"
    log "   -> 请确保你已在项目根目录成功运行过 './setup.sh'。"
    exit 1
fi
log "   -> Pipa command found at: ${PIPA_CMD}"

# --- 健壮的清理机制 ---
cleanup() {
    log "执行清理..."
    pkill -f esrally || true
    "$SHOWCASE_DIR/stop_es.sh"
    # 清理临时日志文件
    rm -f /tmp/esrally_ultimate_test.log
    log "✅ 测试结束。"
}
trap cleanup EXIT

# --- 步骤 1: 启动 Elasticsearch 集群并捕获 PIDs ---
log "步骤 1: 启动 Elasticsearch 集群..."
source "$SHOWCASE_DIR/env.sh"
START_OUTPUT=$("$SHOWCASE_DIR/start_es.sh")
ES_PIDS=$(echo "${START_OUTPUT}" | grep "PIDs for pipa:" | awk '{print $NF}')

if [ -z "$ES_PIDS" ]; then
    log "❌ 致命错误: 未能从 start_es.sh 的输出中捕获到 PIDs。"
    exit 1
fi
log "   -> ES 集群已运行, PIDs: ${ES_PIDS}"

# --- 步骤 2: 启动负载并等待“开始”信号 ---
log "步骤 2: 启动 esrally 负载并主动探测其状态..."
ESRALLY_LOG_FILE="/tmp/esrally_ultimate_test.log"
rm -f "$ESRALLY_LOG_FILE"
"$SHOWCASE_DIR/run_load.sh" > "$ESRALLY_LOG_FILE" 2>&1 &
ESRALLY_PID=$!
log "   -> esrally 已在后台启动 (PID: ${ESRALLY_PID})，日志输出至 ${ESRALLY_LOG_FILE}"

log "   -> 正在等待 esrally 发出 'Running challenge' 信号 (最长等待 ${ESRALLY_PROBE_TIMEOUT} 秒)..."
ELAPSED=0
LOAD_STARTED=false
CHALLENGE_SIGNAL="Running challenge [${ES_RALLY_CHALLENGE}]"

while [ $ELAPSED -lt $ESRALLY_PROBE_TIMEOUT ]; do
    if grep -q -F -e "$CHALLENGE_SIGNAL" "$ESRALLY_LOG_FILE"; then
        log "   -> ✅ 探测到负载信号！立即开始采样！"
        LOAD_STARTED=true
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if (( ELAPSED % 10 == 0 )); then
        log "   -> ...已等待 ${ELAPSED} 秒..."
    fi
done

if ! $LOAD_STARTED; then
    log "❌ 致命错误: 在 ${ESRALLY_PROBE_TIMEOUT} 秒内未探测到 esrally 负载开始信号。"
    log "请检查日志: ${ESRALLY_LOG_FILE}"
    exit 1
fi

# --- 步骤 3: 运行 Pipa 健康检查 (最佳实践) ---
log "步骤 3: 运行 $PIPA_CMD healthcheck..."
$PIPA_CMD healthcheck
``
# --- 步骤 4: 执行 Pipa 标准快照 ---
log "步骤 4: 执行 Pipa 标准两阶段快照 (${DURATION_STAT}s stat + ${DURATION_RECORD}s record)..."
$PIPA_CMD sample \
    --attach-to-pid "${ES_PIDS}" \
    --duration-stat "${DURATION_STAT}" \
    --duration-record "${DURATION_RECORD}" \
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
