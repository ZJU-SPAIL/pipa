#!/bin/bash

# =================================================================
# Pipa Showcase: MySQL - 环境配置文件
# =================================================================

# --- 用户可配置区域 ---
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
# 1. 定义 Lua 脚本所在的目录 (Directory)
export SYSBENCH_LUA_DIR="$SYSBENCH_INSTALL_DIR/share/sysbench"
# 2. 定义默认的脚本名称 (Name Only)
export SYSBENCH_LUA=${SYSBENCH_LUA:-"oltp_read_write"}
# 3. 完整的 Lua 脚本路径
export SYSBENCH_LUA_SCRIPT_PATH="$SYSBENCH_LUA_DIR/$SYSBENCH_LUA.lua"
# --- 压测参数 (对齐合同要求) ---
# [合同] 验收用例: MySQL 8.0版本, Sysbench读写场景
# [合同] 数据规模: 64张表, 每张表1000万条记录 (本次演示采用 100万 用于快速验证)
export SYSBENCH_TABLES=64
export SYSBENCH_TABLE_SIZE=10000000

# 默认并发 (华为指南 P22 建议 128-512)
export SYSBENCH_THREADS=32

# --- Default Fallbacks (全局默认值) ---
# 1. MySQL 配置默认值
export MYSQL_BUFF_POOL=${MYSQL_BUFF_POOL:-"128M"}
export MYSQL_IO_CAPACITY=${MYSQL_IO_CAPACITY:-"2000"}
# === 锁死: 全局统一 4G 日志，方便数据复用 ===
export MYSQL_LOG_SIZE=${MYSQL_LOG_SIZE:-"4G"}
export MYSQL_MAX_CONNECTIONS=${MYSQL_MAX_CONNECTIONS:-"2000"} # 必须足够大
export INNODB_FLUSH_TRX=${INNODB_FLUSH_TRX:-"1"}
export INNODB_SYNC_BINLOG=${INNODB_SYNC_BINLOG:-"1"}
export INNODB_FLUSH_METHOD=${INNODB_FLUSH_METHOD:-"O_DIRECT"}

# --- 扩展调优默认值 ---
export INNODB_BP_INSTANCES=${INNODB_BP_INSTANCES:-"8"}
export INNODB_AHI=${INNODB_AHI:-"ON"}
export INNODB_SPIN_WAIT_DELAY=${INNODB_SPIN_WAIT_DELAY:-"6"}
export INNODB_LRU_SCAN_DEPTH=${INNODB_LRU_SCAN_DEPTH:-"1024"}

# 2. CPU 亲和性默认值 (显式优于隐式)
# 默认: MySQL 用前一半核，Sysbench 用后一半核 (由 nproc 动态计算，作为兜底)
TOTAL_CORES=$(nproc)
HALF_CORES=$((TOTAL_CORES / 2))
export MYSQL_CPU_AFFINITY=${MYSQL_CPU_AFFINITY:-"0-$((HALF_CORES - 1))"}
export SYSBENCH_CPU_AFFINITY=${SYSBENCH_CPU_AFFINITY:-"$HALF_CORES-$((TOTAL_CORES - 1))"}
export IRQ_BIND_CORES=${IRQ_BIND_CORES:-"$HALF_CORES-$((TOTAL_CORES - 1))"}
# 日志格式化输出
log_info() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] [INFO] $1"; }
log_err() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] $1"; }
