#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Redis - 终极自动化测试脚本
# =================================================================

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../" && pwd)

# --- 日志函数（必须先定义）---
log() {
    echo ""
    echo "--- [UltimateTest-Redis] $1 ---"
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

# --- Pipa 环境校验 ---
VENV_PATH="$PROJECT_ROOT/.venv"
PIPA_CMD="$VENV_PATH/bin/pipa"

# --- Evidence 目录与场景定义 ---
SCENARIO="redis_benchmark"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EVIDENCE_DIR="$PROJECT_ROOT/evidence/${TIMESTAMP}_${SCENARIO}"
mkdir -p "$EVIDENCE_DIR"
log "📂 Evidence Directory: $EVIDENCE_DIR"

# --- 动态文件名生成 ---
FOLDER_NAME=$(basename "$SCRIPT_DIR")

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
"$SCRIPT_DIR/run_load.sh" > "$EVIDENCE_DIR/benchmark.log" 2>&1 &
LOAD_PID=$!
log "   -> redis-benchmark 已在后台启动 (PID: ${LOAD_PID}). 日志: benchmark.log"
sleep 5

# --- 步骤 4: 执行 Pipa 标准快照 ---
log "步骤 4: 执行 Pipa 标准两阶段快照 (${DURATION_STAT}s stat + ${DURATION_RECORD}s record)..."
$PIPA_CMD sample \
    --attach-to-pid "${REDIS_PID}" \
    --duration-stat "${DURATION_STAT}" \
    --duration-record "${DURATION_RECORD}" \
    --output "$EVIDENCE_DIR/snapshot.pipa"

log "   -> 快照捕获完成。"

# --- 动态构建预期 CPU 列表 ---
# 直接引用 env.sh 中的变量，实现完全动态
# 只关注 Redis Server (严格服务端审计，剔除 Benchmark)
EXPECTED_CPUS="${REDIS_CPU_AFFINITY}"
log "   -> 预期活跃 CPU 列表 (用于审计): ${EXPECTED_CPUS}"

# --- 步骤 5: 分析快照并生成报告 ---
log "步骤 5a: 分析快照并生成报告 (含合规性检查)..."
# 新增 --expected-cpus 参数
$PIPA_CMD analyze \
    --input "$EVIDENCE_DIR/snapshot.pipa" \
    --output "$EVIDENCE_DIR/report.html" \
    --expected-cpus "${EXPECTED_CPUS}"

log "步骤 5b: 生成火焰图..."
$PIPA_CMD flamegraph \
    --input "$EVIDENCE_DIR/snapshot.pipa" \
    --output "$EVIDENCE_DIR/flamegraph.svg"

# --- 步骤 6: 配置留痕 ---
log "步骤 6: 配置留痕..."
cp "$SCRIPT_DIR/env.sh" "$EVIDENCE_DIR/env_snapshot.sh"
if [ -f "$REDIS_CONF_PATH" ]; then
    cp "$REDIS_CONF_PATH" "$EVIDENCE_DIR/actual_redis.conf"
fi

echo ""
echo "====================================================="
echo "✅ REDIS 终极测试完成!"
echo "📂 证据已归档至: $EVIDENCE_DIR"
echo "➡️  分析报告: report.html"
echo "➡️  火焰图: flamegraph.svg"
echo "====================================================="
