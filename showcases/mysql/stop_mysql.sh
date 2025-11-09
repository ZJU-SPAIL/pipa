#!/bin/bash
set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

echo "--- 停止 MySQL 服务器 ---"
if pgrep -x mysqld > /dev/null; then
    LD_LIBRARY_PATH=${MYSQL_INSTALL_DIR}/lib ${MYSQL_INSTALL_DIR}/bin/mysqladmin -u root -p${MYSQL_ROOT_PASSWORD} --socket=${MYSQL_SOCKET_PATH} shutdown
    echo "✅ MySQL 服务器已停止。"
else
    echo "MySQL 服务器未在运行。"
fi
