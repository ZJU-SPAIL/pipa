#!/bin/bash
set -e

# =================================================================
# PIPA 终极试炼：鲲鹏 MySQL @ 256 线程
# =================================================================

LOG_PREFIX="[UltimateTest]"

log() {
    echo ""
    echo "--- ${LOG_PREFIX} $1 ---"
}

cleanup() {
    log "Cleaning up environment..."
    pkill -f sysbench || true
    if pgrep -x mysqld > /dev/null; then
        ../../showcases/mysql/stop_mysql.sh
    fi
    echo "✅ Test finished."
}
trap cleanup EXIT

# --- 1. 环境准备 ---
log "Step 1: Preparing MySQL and Sysbench environment..."
# 加载 showcase 配置
source ../../showcases/mysql/env.sh
# 启动 MySQL 服务器
../../showcases/mysql/start_mysql.sh
MYSQL_PID=$(pgrep -x mysqld)
echo "   -> MySQL is running with PID: ${MYSQL_PID}"

# --- 2. 健康检查 (最佳实践) ---
log "Step 2: Performing healthcheck..."
pipa healthcheck
echo "   -> pipa_static_info.yaml created in current directory."

# --- 3. 施加极限负载 ---
log "Step 3: Applying EXTREME load (256 threads)..."
# 在后台启动一个持续 5 分钟的、256 线程的 sysbench 压测
../../showcases/mysql/run_sysbench.sh 256 &
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
    --output ultimate_snapshot.pipa

echo "   -> Snapshot capture complete."

# --- 5. 分析战果 ---
log "Step 5: Analyzing the ultimate snapshot..."
pipa analyze \
    --input ultimate_snapshot.pipa \
    --output ultimate_report.html

# --- 6. 生成火焰图 (可选但推荐) ---
log "Step 6: Generating Flame Graph..."
pipa flamegraph \
    --input ultimate_snapshot.pipa \
    --output ultimate_flamegraph.svg


echo ""
echo "====================================================="
echo "✅ ULTIMATE TEST COMPLETE!"
echo "➡️  Your final analysis report is ready: ultimate_report.html"
echo "➡️  Your flame graph is ready: ultimate_flamegraph.svg"
echo "====================================================="
