#!/bin/bash
set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

THREADS=${1:-16} # 默认使用 16 个线程

echo "--- 运行 Sysbench 压测 (threads=${THREADS}) ---"

# 将压测命令放在后台运行，以便我们可以同时用 pipa 监控
LD_LIBRARY_PATH=${MYSQL_INSTALL_DIR}/lib taskset -c $(($(nproc)/2))-$(($(nproc)-1)) ${SYSBENCH_INSTALL_DIR}/bin/sysbench \
    ${SYSBENCH_LUA_SCRIPT_PATH} \
    --mysql-host=127.0.0.1 --mysql-port=${MYSQL_PORT} --mysql-user=root --mysql-password=${MYSQL_ROOT_PASSWORD} \
    --mysql-db=sbtest --tables=${SYSBENCH_TABLES} --table-size=${SYSBENCH_TABLE_SIZE} \
    --threads=${THREADS} --time=300 run &

SYSBENCH_PID=$!
echo "✅ Sysbench 已在后台启动，PID: ${SYSBENCH_PID}"
echo "它将运行 300 秒。请在此期间运行 'pipa sample' 命令。"
