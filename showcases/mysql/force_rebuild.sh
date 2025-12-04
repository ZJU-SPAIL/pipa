#!/bin/bash
# showcases/mysql/force_rebuild.sh - 唯一的数据准备脚本
set -e

# ==================== 路径锚定与环境检查 ====================
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../" && pwd)

VENV_ACTIVATE="$PROJECT_ROOT/.venv/bin/activate"
if [ -f "$VENV_ACTIVATE" ]; then
    source "$VENV_ACTIVATE"
fi

if ! command -v pipa &> /dev/null; then echo "❌ 致命错误: 未找到 'pipa' 命令！" >&2; exit 127; fi
if ! command -v envsubst &> /dev/null; then echo "❌ 致命错误: 未找到 'envsubst' 命令！" >&2; exit 127; fi

SAFETY_GUARD_SCRIPT="$PROJECT_ROOT/showcases/safety-guard.sh"
if [ -f "$SAFETY_GUARD_SCRIPT" ]; then
    source "$SAFETY_GUARD_SCRIPT"
fi
# ===============================================================

echo "💣 即将执行破坏性操作：彻底删除并重建 MySQL 数据集！此过程耗时较长。"
echo "⌛ 将在 3 秒后自动继续执行..."
for i in 3 2 1; do echo "   继续倒计时: $i"; sleep 1; done

echo "[重建] [阶段 1] 强制停止所有现有服务..."
"$SCRIPT_DIR/stop_mysql_force.sh"

echo "[重建] [阶段 2] 启动高速基建模式..."
source "$SCRIPT_DIR/env.sh"
source "$SCRIPT_DIR/profiles/baseline/env.sh"
export MYSQL_AUTOINC_LOCK_MODE=2

rm -rf "$MYSQL_DATA_DIR"
mkdir -p "$MYSQL_DATA_DIR"
# 渲染高性能 my.cnf
envsubst < "$SCRIPT_DIR/config/my.cnf.template" > "$MYSQL_INSTALL_DIR/etc/my.cnf"

# 初始化
"$MYSQL_INSTALL_DIR/bin/mysqld" --defaults-file="$MYSQL_INSTALL_DIR/etc/my.cnf" --initialize-insecure --user="$(whoami)"

echo "   -> [2.1] 启动临时实例..."
"$SCRIPT_DIR/start_mysql.sh"
"$MYSQL_INSTALL_DIR/bin/mysql" -u root -S "$MYSQL_SOCKET_PATH" -e "CREATE DATABASE IF NOT EXISTS sbtest;"

echo "   -> [2.2] 准备 Sysbench 数据 (全速模式)..."
PREPARE_LUA_SCRIPT="$SYSBENCH_LUA_DIR/oltp_read_write.lua"
LD_LIBRARY_PATH="$MYSQL_INSTALL_DIR/lib" "$SYSBENCH_INSTALL_DIR/bin/sysbench" "$PREPARE_LUA_SCRIPT" --mysql-socket="$MYSQL_SOCKET_PATH" --mysql-user=root --tables="$SYSBENCH_TABLES" --table-size="$SYSBENCH_TABLE_SIZE" --threads="$SYSBENCH_THREADS" prepare

echo "[重建] [阶段 3] 基建完成，正在执行优雅关停..."
"$SCRIPT_DIR/stop_mysql_graceful.sh"

echo "✅ 数据集已成功构建并安全关闭。现在可以运行 run_with_profile.sh 了。"
