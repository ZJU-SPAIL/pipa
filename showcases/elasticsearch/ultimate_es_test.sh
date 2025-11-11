#!/bin/bash
set -e
set -o pipefail

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
    log "测试结束，调用终极清理脚本..."
    # 调用我们统一的、全功能的停止脚本
    "$SHOWCASE_DIR/stop_es.sh"
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

# --- 步骤 2: 启动负载并探测真实日志文件 ---
log "步骤 2: 启动 esrally 负载并主动探测其真实日志..."
# 定义 esrally 真正的日志文件路径
ESRALLY_REAL_LOG_FILE="$HOME/.rally/logs/rally.log"
log "   -> 目标日志文件: ${ESRALLY_REAL_LOG_FILE}"

# 关键步骤：在启动前清空日志，确保我们只看到本次运行的输出
# The > operator will create the file if it doesn't exist.
# > 操作符会在文件不存在时创建它。
> "$ESRALLY_REAL_LOG_FILE"
log "   -> 已清空目标日志文件以进行干净的探测。"

# 启动 run_load.sh，将其无关紧要的 stdout/stderr 重定向到 /dev/null
"$SHOWCASE_DIR/run_load.sh" > /dev/null 2>&1 &
ESRALLY_PID=$!
log "   -> esrally 已在后台启动 (PID: ${ESRALLY_PID})."

# 探测循环：现在我们监视的是真正的日志文件
log "   -> 正在等待 esrally 发出 'Racing on track' 信号 (最长等待 ${ESRALLY_PROBE_TIMEOUT} 秒)..."
ELAPSED=0
LOAD_STARTED=false
WORKLOAD_SIGNAL="Loading component [${ES_RALLY_TRACK}]"

while [ $ELAPSED -lt $ESRALLY_PROBE_TIMEOUT ]; do
    # 使用 -F 进行固定字符串搜索，确保健壮性
    if grep -q -F "$WORKLOAD_SIGNAL" "$ESRALLY_REAL_LOG_FILE"; then
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
    log "❌ 致命错误: 在 ${ESRALLY_PROBE_TIMEOUT} 秒内未在真实日志中探测到 esrally 负载开始信号。"
    log "请检查日志: ${ESRALLY_REAL_LOG_FILE}"
    exit 1
fi

log "步骤 3: 运行 $PIPA_CMD healthcheck..."
$PIPA_CMD healthcheck

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
