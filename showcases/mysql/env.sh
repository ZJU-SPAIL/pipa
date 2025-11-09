#!/bin/bash

# =================================================================
# Pipa Showcase: MySQL - 环境配置文件
# 这是本案例的“单一事实来源”(Single Source of Truth)。
# 在运行任何脚本之前，请先 source 此文件: `source showcases/mysql/env.sh`
# =================================================================

# --- 用户可配置区域 ---
# 警告: 请务必修改此密码
export MYSQL_ROOT_PASSWORD="your_secure_password"
export MYSQL_PORT=3307

# --- 核心路径定义 ---
# 获取此脚本所在的目录，作为 showcase 的根目录
export SHOWCASE_DIR
SHOWCASE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

# 所有构建产物和数据都将存放在 showcase 目录下的 build/ 子目录中
export BASE_DIR="$SHOWCASE_DIR/build"
export MYSQL_INSTALL_DIR="$BASE_DIR/mysql"
export MYSQL_DATA_DIR="$BASE_DIR/data"
export MYSQL_LOGS_DIR="$BASE_DIR/logs"
export SYSBENCH_INSTALL_DIR="$BASE_DIR/sysbench"

# --- 衍生路径 (无需修改) ---
export MY_CNF_PATH="$MYSQL_INSTALL_DIR/etc/my.cnf"
export MYSQL_SOCKET_PATH="$MYSQL_DATA_DIR/mysql.sock"
export MYSQL_PID_PATH="$MYSQL_LOGS_DIR/mysqldb.pid"

# --- 压测参数 ---
export SYSBENCH_LUA_SCRIPT_PATH="$SYSBENCH_INSTALL_DIR/share/sysbench/oltp_read_write.lua"
export SYSBENCH_TABLES=8  # 注意: 12+ 会触发 Sysbench 1.0.20 的表重复创建 bug
export SYSBENCH_TABLE_SIZE=1000000
