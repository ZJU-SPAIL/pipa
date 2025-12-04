#!/bin/bash
# showcases/mysql/stop_mysql_force.sh

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

echo "[强制关闭] 正在执行 kill -9..."
pkill -9 -f "${MYSQL_INSTALL_DIR}/bin/mysqld" 2>/dev/null || true
pkill -9 -f "mysqld_safe" 2>/dev/null || true
sleep 0.5
rm -f "$MYSQL_SOCKET_PATH" "$MYSQL_PID_PATH" "$MYSQL_DATA_DIR/mysql.sock.lock"
echo "[强制关闭] ✅ 清理完毕。"
