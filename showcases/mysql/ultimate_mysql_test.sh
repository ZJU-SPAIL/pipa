#!/bin/bash
set -e

# =================================================================
# PIPA 终极试炼：鲲鹏 MySQL @ 256 线程
# =================================================================

# 获取项目根目录（脚本所在目录的两级父目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../" && pwd)"

# --- 动态文件名生成 ---
FOLDER_NAME=$(basename "$SCRIPT_DIR")
SNAPSHOT_FILE="${FOLDER_NAME}_snapshot.pipa"
REPORT_FILE="${FOLDER_NAME}_report.html"
FLAMEGRAPH_FILE="${FOLDER_NAME}_flamegraph.svg"

# 自动激活虚拟环境
VENV_DIR="${PROJECT_ROOT}/.venv"
if [ -d "${VENV_DIR}" ]; then
    source "${VENV_DIR}/bin/activate"
    echo "✓ Virtual environment activated: ${VENV_DIR}"
else
    echo "⚠ Warning: Virtual environment not found at ${VENV_DIR}"
fi

LOG_PREFIX="[UltimateTest]"

log() {
    echo ""
    echo "--- ${LOG_PREFIX} $1 ---"
}

cleanup() {
    log "Cleaning up environment..."
    pkill -f sysbench || true
    if pgrep -x mysqld > /dev/null; then
        "${PROJECT_ROOT}/showcases/mysql/stop_mysql.sh"
    fi
    echo "✅ Test finished."
}
trap cleanup EXIT

# --- 步骤 0: 自动化环境准备 (防呆) ---
log "Step 0: Ensuring environment is ready..."
# 这一步是安全的，因为 setup.sh 内部有幂等性检查。
# 如果已安装，它会瞬间结束；如果未安装，它会救命。
$SCRIPT_DIR/setup.sh

# --- 1. 环境准备 ---
log "Step 1: Preparing MySQL and Sysbench environment..."
# 加载 showcase 配置
source "${PROJECT_ROOT}/showcases/mysql/env.sh"
# 启动 MySQL 服务器
"${PROJECT_ROOT}/showcases/mysql/start_mysql.sh"
MYSQL_PID=$(pgrep -x mysqld)
echo "   -> MySQL is running with PID: ${MYSQL_PID}"

# --- 2. 健康检查 (最佳实践) ---
log "Step 2: Performing healthcheck..."
pipa healthcheck
echo "   -> pipa_static_info.yaml created in current directory."

# --- 3. 施加极限负载 ---
log "Step 3: Applying EXTREME load (256 threads)..."
# 在后台启动一个持续 5 分钟的、256 线程的 sysbench 压测
"${PROJECT_ROOT}/showcases/mysql/run_sysbench.sh" 256 &
SYSBENCH_PID=$!
echo "   -> Sysbench is running in the background with PID: ${SYSBENCH_PID}"
echo "   -> Waiting 15 seconds for the load to stabilize..."
sleep 15

# --- 4. 执行 PIPA 标准快照 ---
log "Step 4: Executing PIPA's standardized two-phase snapshot..."
# 我们将执行一个 60s (stat) + 60s (record) 的完整快照
# 注意：我们不再需要任何 collectors.yaml 或 events.yaml！
# Pipa 会自动使用我们内置的专家知识。
pipa sample \
    --attach-to-pid "${MYSQL_PID}" \
    --duration-stat 60 \
    --duration-record 60 \
    --output "${SNAPSHOT_FILE}"

echo "   -> Snapshot capture complete."

# --- 动态构建预期 CPU 列表 ---
# MySQL 占下半区，Sysbench 占上半区 -> 也就是所有核心 (0 到 N-1)
TOTAL_CORES=$(nproc)
LAST_CORE=$((TOTAL_CORES - 1))
EXPECTED_CPUS="0-${LAST_CORE}"

log "   -> 预期活跃 CPU 列表 (MySQL+Sysbench 覆盖全核): ${EXPECTED_CPUS}"

# --- 5. 分析战果 ---
log "Step 5: Analyzing the ultimate snapshot..."
pipa analyze \
    --input "${SNAPSHOT_FILE}" \
    --output "${REPORT_FILE}" \
    --expected-cpus "${EXPECTED_CPUS}"

# --- 6. 生成火焰图 (可选但推荐) ---
log "Step 6: Generating Flame Graph..."
pipa flamegraph \
    --input "${SNAPSHOT_FILE}" \
    --output "${FLAMEGRAPH_FILE}"


echo ""
echo "====================================================="
echo "✅ ULTIMATE TEST COMPLETE!"
echo "➡️  Your final analysis report is ready: ${REPORT_FILE}"
echo "➡️  Your flame graph is ready: ${FLAMEGRAPH_FILE}"
echo "====================================================="
