#!/usr/bin/env bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Nginx - 终极自动化测试脚本 (v2)
# 职责: 编排一次完整的、可重复的 Nginx 性能分析实验。
# =================================================================

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../" && pwd)

# --- 日志函数（必须先定义）---
log() {
    echo ""
    echo "--- [UltimateTest-Nginx] $1 ---"
}

# ==================== 安全检查 ====================
SAFETY_GUARD_SCRIPT="$PROJECT_ROOT/showcases/safety-guard.sh"
if [ -f "$SAFETY_GUARD_SCRIPT" ]; then
    source "$SAFETY_GUARD_SCRIPT"
else
    echo "⚠️ 警告: 未找到安全检查脚本: $SAFETY_GUARD_SCRIPT"
fi
# =======================================================

# --- 核心配置区 (可从 env.sh 覆盖) ---
DURATION_STAT=${DURATION_STAT:-60}
DURATION_RECORD=${DURATION_RECORD:-60}

source "$SCRIPT_DIR/env.sh"

# --- Evidence 目录与场景定义 ---
SCENARIO="nginx_high_compression"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EVIDENCE_DIR="$PROJECT_ROOT/evidence/${TIMESTAMP}_${SCENARIO}"
mkdir -p "$EVIDENCE_DIR"
log "📂 Evidence Directory: $EVIDENCE_DIR"

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
    log "测试结束，调用终极清理脚本..."
    "$SCRIPT_DIR/stop_nginx.sh"
}
trap cleanup EXIT

# --- 步骤 0: 自动化环境准备 (防呆) ---
log "Step 0: Ensuring environment is ready..."
# 这一步是安全的，因为 setup.sh 内部有幂等性检查。
# 如果已安装，它会瞬间结束；如果未安装，它会救命。
"$SHOWCASE_DIR/setup.sh"

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
# 在后台启动一个持续时间足够长的负载，日志重定向到 Evidence
"$SCRIPT_DIR/run_load.sh" > "$EVIDENCE_DIR/wrk_load.log" 2>&1 &
WRK_PID=$!
log "   -> WRK 已在后台启动 (PID: ${WRK_PID}). 日志: wrk_load.log"
sleep 5

# --- 步骤 4: 执行 Pipa 标准快照 ---
log "步骤 4: 执行 Pipa 标准两阶段快照 (${DURATION_STAT}s stat + ${DURATION_RECORD}s record)..."
$PIPA_CMD sample \
    --attach-to-pid "${NGINX_PIDS}" \
    --duration-stat "${DURATION_STAT}" \
    --duration-record "${DURATION_RECORD}" \
    --output "$EVIDENCE_DIR/snapshot.pipa"

log "   -> 快照捕获完成。"

# 只关注 Nginx Worker 的核心（严格服务端审计，剔除 WRK）
EXPECTED_CPUS="${NGINX_CPU_AFFINITY}"
log "   -> 预期活跃 CPU 列表 (用于审计): ${EXPECTED_CPUS}"

# --- 步骤 4a: 分析快照并生成报告 ---
log "步骤 4a: 分析快照并生成报告..."
$PIPA_CMD analyze \
    --input "$EVIDENCE_DIR/snapshot.pipa" \
    --output "$EVIDENCE_DIR/report.html" \
    --expected-cpus "${EXPECTED_CPUS}"

log "步骤 4b: 生成火焰图..."
$PIPA_CMD flamegraph \
    --input "$EVIDENCE_DIR/snapshot.pipa" \
    --output "$EVIDENCE_DIR/flamegraph.svg"

# --- 步骤 5: 配置留痕 ---
log "步骤 5: 配置留痕..."
cp "$SCRIPT_DIR/env.sh" "$EVIDENCE_DIR/env_snapshot.sh"
if [ -f "$NGINX_CONF_PATH" ]; then
    cp "$NGINX_CONF_PATH" "$EVIDENCE_DIR/actual_nginx.conf"
fi

echo ""
echo "====================================================="
echo "✅ PIPA 性能收集与分析完成!"
echo "📂 证据已归档至: $EVIDENCE_DIR"
echo "➡️  分析报告: report.html"
echo "➡️  火焰图: flamegraph.svg"
echo "====================================================="
