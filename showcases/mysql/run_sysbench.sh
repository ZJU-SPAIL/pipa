#!/bin/bash
set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

THREADS=${1:-${SYSBENCH_THREADS:-16}} # 优先用参数，其次用环境变量，最后默认16

echo "--- 运行 Sysbench 压测 ---"
echo "配置: Threads=${THREADS}, CPU Affinity=${SYSBENCH_CPU_AFFINITY}"

# === 使用变量 $SYSBENCH_CPU_AFFINITY 替代硬编码 ===
LD_LIBRARY_PATH=${MYSQL_INSTALL_DIR}/lib \
taskset -c "${SYSBENCH_CPU_AFFINITY}" \
${SYSBENCH_INSTALL_DIR}/bin/sysbench \
    ${SYSBENCH_LUA_SCRIPT_PATH} \
    --mysql-host=127.0.0.1 --mysql-port=${MYSQL_PORT} --mysql-user=root --mysql-password=${MYSQL_ROOT_PASSWORD} \
    --mysql-db=sbtest --tables=${SYSBENCH_TABLES} --table-size=${SYSBENCH_TABLE_SIZE} \
    --threads=${THREADS} --time=300 run &

SYSBENCH_PID=$!
echo "✅ Sysbench 已在后台启动，PID: ${SYSBENCH_PID}"
