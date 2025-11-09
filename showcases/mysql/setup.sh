#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: MySQL 环境准备脚本 (v2 - 配置解耦版)
# 职责: 编译、安装、初始化 MySQL 和 Sysbench。
# 特性: 依赖 env.sh 作为配置中心，实现关注点分离。
# =================================================================

# 获取脚本自身所在的目录
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

# 检查 env.sh 是否存在，如果不存在则报错退出
if [ ! -f "$SCRIPT_DIR/env.sh" ]; then
    echo "❌ 错误: 配置文件 env.sh 未找到！" >&2
    exit 1
fi

# 加载环境变量，这是所有后续操作的基础
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - $1"
}

# --- 内部配置 (软件版本等) ---
SRC_DIR="$BASE_DIR/src"
MYSQL_VERSION="8.0.28"
SYSBENCH_VERSION="1.0.20"
MYSQL_SRC_DIR_NAME="mysql-${MYSQL_VERSION}"
MYSQL_DOWNLOAD_URL="https://downloads.mysql.com/archives/get/p/23/file/mysql-boost-${MYSQL_VERSION}.tar.gz"
SYSBENCH_DOWNLOAD_URL="https://github.com/akopytov/sysbench/archive/refs/tags/${SYSBENCH_VERSION}.tar.gz"
BUILD_CORES=$(nproc)

# --- 核心逻辑 ---

# 幂等性检查：如果成功标志存在，则直接退出
SUCCESS_FLAG="$BASE_DIR/.setup_success"
if [ -f "$SUCCESS_FLAG" ]; then
    log "✅ 检测到成功标志，环境已准备就绪。跳过所有步骤。"
    log "如需强制重新准备，请先删除目录: rm -rf $SUCCESS_FLAG"
    exit 0
fi

# 1. 安装依赖
log "--- 步骤 1/5: 安装编译依赖 ---"
sudo yum groupinstall -y "Development Tools"
sudo yum install -y cmake ncurses-devel openssl-devel libtirpc-devel rpcgen automake libtool bzip2 libaio

# 2. 创建目录
log "--- 步骤 2/5: 创建目录结构 ---"
mkdir -p "$SRC_DIR" "$MYSQL_INSTALL_DIR" "$MYSQL_DATA_DIR" "$MYSQL_LOGS_DIR" "$SYSBENCH_INSTALL_DIR"

# 3. 编译 MySQL
log "--- 步骤 3/5: 编译和安装 MySQL ${MYSQL_VERSION} ---"
cd "$SRC_DIR"
if [ ! -d "$MYSQL_SRC_DIR_NAME" ]; then
    wget -q --show-progress -O "mysql.tar.gz" "$MYSQL_DOWNLOAD_URL"
    tar -zxf "mysql.tar.gz"
fi
cd "$MYSQL_SRC_DIR_NAME"
cmake . -DCMAKE_INSTALL_PREFIX="$MYSQL_INSTALL_DIR" \
    -DDEFAULT_CHARSET=utf8mb4 \
    -DDEFAULT_COLLATION=utf8mb4_general_ci \
    -DWITH_INNOBASE_STORAGE_ENGINE=1 \
    -DMYSQL_DATADIR="$MYSQL_DATA_DIR" \
    -DSYSCONFDIR="$MYSQL_INSTALL_DIR/etc" \
    -DWITH_BOOST="$SRC_DIR/$MYSQL_SRC_DIR_NAME/boost" \
    -DFORCE_INSOURCE_BUILD=1
make -j"$BUILD_CORES"
make install

# 4. 编译 Sysbench
log "--- 步骤 4/5: 编译和安装 Sysbench ${SYSBENCH_VERSION} ---"
cd "$SRC_DIR"
if [ ! -d "sysbench-${SYSBENCH_VERSION}" ]; then
    wget -q --show-progress -O "sysbench.tar.gz" "$SYSBENCH_DOWNLOAD_URL"
    tar -zxf "sysbench.tar.gz"
fi
cd "sysbench-${SYSBENCH_VERSION}"
./autogen.sh
./configure --prefix="$SYSBENCH_INSTALL_DIR" --with-mysql-includes="$MYSQL_INSTALL_DIR/include" --with-mysql-libs="$MYSQL_INSTALL_DIR/lib"
make -j"$BUILD_CORES"
make install

# 5. 初始化数据库并准备数据
log "--- 步骤 5/5: 初始化 MySQL 并准备 Sysbench 数据 ---"

if [ -d "$MYSQL_DATA_DIR/mysql" ]; then
    log "检测到 MySQL 数据目录已存在。跳过初始化和数据准备。"
else
    # 生成配置文件（所有变量来自 env.sh）
    MY_CNF_TEMPLATE="$SHOWCASE_DIR/config/my.cnf.template"
    mkdir -p "$(dirname "$MY_CNF_PATH")"
    # 使用 envsubst 动态替换模板中的变量（env.sh 已导出所有需要的变量）
    envsubst < "$MY_CNF_TEMPLATE" > "$MY_CNF_PATH"

    # 初始化
    "$MYSQL_INSTALL_DIR/bin/mysqld" --defaults-file="$MY_CNF_PATH" --initialize-insecure --user="$(whoami)"

    # 启动临时服务器
    "$MYSQL_INSTALL_DIR/bin/mysqld_safe" --defaults-file="$MY_CNF_PATH" &
    MYSQL_PID=$!

    # --- 核心修复：用主动探测，替代盲目等待 ---
    log "Waiting for temporary MySQL server to become ready..."
    retries=30
    while ! "$MYSQL_INSTALL_DIR/bin/mysqladmin" ping --silent --socket="$MYSQL_SOCKET_PATH" && [ $retries -gt 0 ]; do
        log "  ... waiting ($retries retries left)"
        sleep 2
        ((retries--))
    done

    if [ $retries -eq 0 ]; then
        log "❌ 错误: 临时 MySQL 服务器在 60 秒内未能启动。"
        cat "$MYSQL_LOGS_DIR/error.log"
        exit 1
    fi
    log "✅ 临时 MySQL 服务器已就绪。"

    # 额外等待 5 秒，确保 MySQL 完全初始化
    log "Waiting for MySQL to fully initialize system tables..."
    sleep 5

    # 设置密码
    log "Setting root password..."
    "$MYSQL_INSTALL_DIR/bin/mysql" -u root --socket="$MYSQL_SOCKET_PATH" <<-EOF
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';
EOF

    # 强制重建数据库（使用密码）
    log "Dropping and recreating sbtest database..."
    "$MYSQL_INSTALL_DIR/bin/mysql" -u root -p"${MYSQL_ROOT_PASSWORD}" --socket="$MYSQL_SOCKET_PATH" <<-EOF
DROP DATABASE IF EXISTS sbtest;
CREATE DATABASE sbtest;
EOF

    log "Preparing sysbench data (fresh database)..."
    LD_LIBRARY_PATH="$MYSQL_INSTALL_DIR/lib" "$SYSBENCH_INSTALL_DIR/bin/sysbench" \
        "$SYSBENCH_LUA_SCRIPT_PATH" \
        --mysql-host=127.0.0.1 --mysql-port=${MYSQL_PORT} --mysql-user=root --mysql-password="$MYSQL_ROOT_PASSWORD" \
        --mysql-db=sbtest --tables="$SYSBENCH_TABLES" --table-size="$SYSBENCH_TABLE_SIZE" \
        prepare

    # 关闭临时服务器
    "$MYSQL_INSTALL_DIR/bin/mysqladmin" -u root -p"$MYSQL_ROOT_PASSWORD" --socket="$MYSQL_SOCKET_PATH" shutdown
    wait $MYSQL_PID || true
fi

# --- 完成 ---
touch "$SUCCESS_FLAG"
log "✅ MySQL Showcase 环境准备完成！"
log ""
log "--- 🚀 快速开始：一个典型的分析流程 ---"
log "你可以直接复制并粘贴以下命令来体验 Pipa:"
log ''
log '1. 启动服务并施加负载 (后台运行):'
log '   ./showcases/mysql/start_mysql.sh && ./showcases/mysql/run_sysbench.sh 32 &'
log ''
log '2. 对 MySQL 进行 60 秒的性能快照:'
log '   MYSQL_PID=$(pgrep -x mysqld) && pipa sample \'
log '       --attach-to-pid "${MYSQL_PID}" \'
log '       --duration 60 \'
log '       --collectors-config showcases/mysql/mysql_collectors.yaml \'
log '       --output mysql_snapshot.pipa'
log ''
log '3. 分析快照并生成报告:'
log '   pipa analyze --input mysql_snapshot.pipa --output report.html'
log ''
log '4. (完成后) 清理环境:'
log '   pkill sysbench; ./showcases/mysql/stop_mysql.sh'
log "-------------------------------------------"
