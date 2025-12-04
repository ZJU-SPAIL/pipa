#!/bin/bash
# showcases/mysql/stop_mysql_graceful.sh

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"
SHUTDOWN_TIMEOUT=${1:-600} # 默认等待 10 分钟

echo "[关机] 正在执行优雅关停 (最长等待 ${SHUTDOWN_TIMEOUT}s)..."

if pgrep -f "${MYSQL_INSTALL_DIR}/bin/mysqld" >/dev/null; then
    "$MYSQL_INSTALL_DIR/bin/mysqladmin" -u root -S "$MYSQL_SOCKET_PATH" shutdown >/dev/null 2>&1 &

    elapsed=0
    while [ $elapsed -lt $SHUTDOWN_TIMEOUT ]; do
        if ! pgrep -f "${MYSQL_INSTALL_DIR}/bin/mysqld" >/dev/null; then
            echo -e "\n[关机] ✅ MySQL 已优雅关闭。"
            # 清理文件
            rm -f "$MYSQL_SOCKET_PATH" "$MYSQL_PID_PATH" "$MYSQL_DATA_DIR/mysql.sock.lock"
            exit 0
        fi
        sleep 2; elapsed=$((elapsed + 2)); echo -n "."
    done

    echo -e "\n[关机] ❌ 错误: 超时！MySQL 未能优雅关闭。请手动检查或强制关闭。"
    exit 1
else
    echo "[关机] MySQL 未在运行。"
fi
