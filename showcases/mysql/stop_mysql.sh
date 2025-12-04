#!/bin/bash
# showcases/mysql/stop_mysql.sh
# 默认的停止脚本，调用优雅关停
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
"$SCRIPT_DIR/stop_mysql_graceful.sh"
