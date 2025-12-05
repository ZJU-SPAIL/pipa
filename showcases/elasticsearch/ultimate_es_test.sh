#!/bin/bash
set -e
set -o pipefail

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
SHOWCASE_DIR="$SCRIPT_DIR"
PROJECT_ROOT=$(cd "$SHOWCASE_DIR/../../" && pwd)

# --- 日志函数（必须先定义）---
log() {
    echo ""
    echo "--- [UltimateTest-ES] $1 ---"
}

# ==================== 安全检查 ====================
SAFETY_GUARD_SCRIPT="$PROJECT_ROOT/showcases/safety-guard.sh"
if [ -f "$SAFETY_GUARD_SCRIPT" ]; then
    source "$SAFETY_GUARD_SCRIPT"
else
    echo "⚠️ 警告: 未找到安全检查脚本: $SAFETY_GUARD_SCRIPT"
fi
# =======================================================

# --- 核心配置区 ---
# 魔改: 只跑 60s + 60s
DURATION_STAT=60
DURATION_RECORD=60
ESRALLY_PROBE_TIMEOUT=1200 # 最长等待 5 分钟

# --- Evidence 目录与场景定义 ---
SCENARIO="es_geonames_race"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EVIDENCE_DIR="$PROJECT_ROOT/evidence/${TIMESTAMP}_${SCENARIO}"
mkdir -p "$EVIDENCE_DIR"

# --- 动态文件名生成 ---
FOLDER_NAME=$(basename "$SHOWCASE_DIR")

# --- Pipa 环境校验 ---
VENV_PATH="$PROJECT_ROOT/.venv"
PIPA_CMD="$VENV_PATH/bin/pipa"

if [ ! -x "$PIPA_CMD" ]; then
    log "❌ 致命错误: Pipa 命令未在 '$PIPA_CMD' 找到或不可执行。"
    log "   -> 请确保你已在项目根目录成功运行过 './setup.sh'。"
    exit 1
fi
log "   -> Pipa command found at: ${PIPA_CMD}"

# --- 健壮的清理机制 ---
cleanup() {
    log "测试结束，调用清理脚本..."
    # 调用我们统一的、全功能的停止脚本
    "$SHOWCASE_DIR/stop_es.sh"
    rm -f /tmp/pipa_es_probe.log
}
trap cleanup EXIT

# --- 步骤 0: 自动化环境准备 (防呆) ---
log "Step 0: Ensuring environment is ready..."
# 这一步是安全的，因为 setup.sh 内部有幂等性检查。
# 如果已安装，它会瞬间结束；如果未安装，它会救命。
"$SHOWCASE_DIR/setup.sh"

log "步骤 1: 运行 $PIPA_CMD healthcheck..."
$PIPA_CMD healthcheck

# --- 步骤 2: 启动 Elasticsearch 集群并捕获 PIDs ---
log "步骤 2: 启动 Elasticsearch 集群..."
source "$SHOWCASE_DIR/env.sh"
START_OUTPUT=$("$SHOWCASE_DIR/start_es.sh")
ES_PIDS=$(echo "${START_OUTPUT}" | grep "PIDs for pipa:" | awk '{print $NF}')

if [ -z "$ES_PIDS" ]; then
    log "❌ 致命错误: 未能从 start_es.sh 的输出中捕获到 PIDs。"
    exit 1
fi
log "   -> ES 集群已运行, PIDs: ${ES_PIDS}"

#--- 步骤 3: 启动负载并从简洁的 stdout 探测信号 ---
log "步骤 3: 启动 esrally 负载并主动探测其真实日志..."
# 定义 esrally 真正的日志文件路径
ESRALLY_REAL_LOG_FILE="$HOME/.rally/logs/rally.log"
log "   -> 目标日志文件: ${ESRALLY_REAL_LOG_FILE}"

# 关键步骤：在启动前清空日志
> "$ESRALLY_REAL_LOG_FILE"
log "   -> 已清空目标日志文件以进行干净的探测。"

# 启动 run_load.sh，将其 stdout/stderr 重定向到 Evidence 目录
"$SHOWCASE_DIR/run_load.sh" > "$EVIDENCE_DIR/esrally.log" 2>&1 &
ESRALLY_PID=$!
log "   -> esrally 已在后台启动 (PID: ${ESRALLY_PID}). 日志: esrally.log"

# 探测循环：监视真正的日志文件
log "   -> 正在等待 esrally 发出核心负载信号 (最长等待 ${ESRALLY_PROBE_TIMEOUT} 秒)..."
ELAPSED=0
LOAD_STARTED=false
# 使用从 env.sh 中读取的、动态的、真实的信号！
WORKLOAD_SIGNAL="${ES_RALLY_WORKLOAD_SIGNAL}"

while [ $ELAPSED -lt $ESRALLY_PROBE_TIMEOUT ]; do
    if grep -q -F "$WORKLOAD_SIGNAL" "$ESRALLY_REAL_LOG_FILE"; then
        log "   -> ✅ 探测到核心负载信号: '${WORKLOAD_SIGNAL}'！立即开始采样！"
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
    log "❌ 致命错误: 在 ${ESRALLY_PROBE_TIMEOUT} 秒内未在真实日志中探测到核心负载信号。"
    log "请检查 esrally 的详细日志: ${ESRALLY_REAL_LOG_FILE}"
    exit 1
fi

# --- 步骤 4: 执行 Pipa 标准快照 ---
log "步骤 4: 执行 Pipa 标准两阶段快照 (${DURATION_STAT}s stat + ${DURATION_RECORD}s record)..."
$PIPA_CMD sample \
    --attach-to-pid "${ES_PIDS}" \
    --duration-stat "${DURATION_STAT}" \
    --duration-record "${DURATION_RECORD}" \
    --output "$EVIDENCE_DIR/snapshot.pipa"

log "   -> 快照捕获完成。"

# --- 动态构建预期 CPU 列表 ---
# 拼接所有组件的绑核范围（严格服务端审计，剔除 Rally）
EXPECTED_CPUS="${ES_NODE_1_CPU_AFFINITY},${ES_NODE_2_CPU_AFFINITY},${ES_NODE_3_CPU_AFFINITY}"
log "   -> 预期活跃 CPU 列表 (用于审计): ${EXPECTED_CPUS}"

# --- 步骤 5: 分析快照并生成报告 ---
log "步骤 5: 分析快照..."
$PIPA_CMD analyze \
    --input "$EVIDENCE_DIR/snapshot.pipa" \
    --output "$EVIDENCE_DIR/report.html" \
    --expected-cpus "${EXPECTED_CPUS}"

# --- 步骤 6: 生成火焰图 ---
log "步骤 6: 生成火焰图..."
$PIPA_CMD flamegraph \
    --input "$EVIDENCE_DIR/snapshot.pipa" \
    --output "$EVIDENCE_DIR/flamegraph.svg"

# --- 步骤 7: 配置留痕 ---
log "步骤 7: 配置留痕..."
cp "$SHOWCASE_DIR/env.sh" "$EVIDENCE_DIR/env_snapshot.sh"
# 拷贝节点1的配置作为代表
if [ -d "$ES_INSTALL_DIR" ]; then
    if [ -f "$ES_INSTALL_DIR/$ES_NODE_1_NAME/config/elasticsearch.yml" ]; then
        cp "$ES_INSTALL_DIR/$ES_NODE_1_NAME/config/elasticsearch.yml" "$EVIDENCE_DIR/node1_elasticsearch.yml"
    fi
    if [ -f "$ES_INSTALL_DIR/$ES_NODE_1_NAME/config/jvm.options" ]; then
        cp "$ES_INSTALL_DIR/$ES_NODE_1_NAME/config/jvm.options" "$EVIDENCE_DIR/jvm.options"
    fi
fi

echo ""
echo "====================================================="
echo "✅ ELASTICSEARCH 终极测试完成!"
echo "📂 证据已归档至: $EVIDENCE_DIR"
echo "➡️  分析报告: report.html"
echo "➡️  火焰图: flamegraph.svg"
echo "====================================================="
