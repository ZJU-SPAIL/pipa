#!/bin/bash
set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
# 注意：这里加载 env.sh 是为了获取路径等基础信息
# 如果是由 run_with_profile.sh 调用的，环境变量已经被 export，这里 source 不会覆盖已有的 export
source "$SCRIPT_DIR/env.sh"

echo "--- 启动 MySQL 服务器 ---"
echo "配置: CPU Affinity=${MYSQL_CPU_AFFINITY}"

if pgrep -x mysqld > /dev/null; then
    echo "MySQL 服务器似乎已在运行。"
else
    LD_LIBRARY_PATH=${MYSQL_INSTALL_DIR}/lib \
    taskset -c "${MYSQL_CPU_AFFINITY}" \
    ${MYSQL_INSTALL_DIR}/bin/mysqld_safe --defaults-file=${MY_CNF_PATH} &

    echo "等待 MySQL 服务器就绪..."
    retries=120
    while ! "${MYSQL_INSTALL_DIR}/bin/mysqladmin" ping --silent --socket="${MYSQL_SOCKET_PATH}" && [ $retries -gt 0 ]; do
        sleep 2
        ((retries--))
    done

    if [ $retries -eq 0 ]; then
        echo "❌ 错误: MySQL 服务器在 60 秒内未能启动。"
        tail -n 10 "${MYSQL_LOGS_DIR}/error.log"
        exit 1
    fi
fi

PID=$(pgrep -x mysqld)
echo "✅ MySQL 服务器已在运行，PID: ${PID}"
