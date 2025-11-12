#!/usr/bin/env bash

set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Nginx 环境准备脚本
# 职责: 编译、安装 Nginx 和 WRK。
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
NGINX_SRC_DIR_NAME="nginx-${NGINX_VERSION}"
BUILD_CORES=$(nproc)

# --- 核心逻辑 ---

# 幂等性检查：如果成功标志存在，则直接退出
SUCCESS_FLAG="$BASE_DIR/.setup_success"
if [ -f "$SUCCESS_FLAG" ]; then
    log "✅ 检测到成功标志，环境已准备就绪。跳过所有步骤。"
    log "如需强制重新准备，请先删除文件: rm -f $SUCCESS_FLAG"
    exit 0
fi

# 1. 安装依赖
log "--- 步骤 1/3: 安装编译依赖 ---"
sudo yum install -y pcre-devel zlib-devel openssl-devel git

# 2. 创建目录
log "--- 步骤 2/3: 创建目录结构 ---"
mkdir -p "$SRC_DIR" "$NGINX_INSTALL_DIR" "$NGINX_LOGS_DIR" "$WRK_INSTALL_DIR/bin" "$NGINX_OUTPUT_DIR"

# 3. 编译 Nginx
log "--- 步骤 3a/3: 编译和安装 Nginx ${NGINX_VERSION} ---"
cd "$SRC_DIR"
if [ ! -d "$NGINX_SRC_DIR_NAME" ]; then
    wget -q --show-progress -O "${NGINX_SRC_DIR_NAME}.tar.gz" "$NGINX_DOWNLOAD_URL"
    tar -zxf "${NGINX_SRC_DIR_NAME}.tar.gz"
fi
cd "$NGINX_SRC_DIR_NAME"

if [ ! -f "$NGINX_INSTALL_DIR/sbin/nginx" ]; then
    log "配置 Nginx..."
    ./configure \
        --prefix="$NGINX_INSTALL_DIR" \
        --error-log-path="$NGINX_LOGS_DIR/error.log" \
        --http-log-path="$NGINX_LOGS_DIR/access.log" \
        --pid-path="$NGINX_PID_PATH" \
        --with-http_ssl_module

    log "编译 Nginx (使用 ${BUILD_CORES} 个核心)..."
    make -j"$BUILD_CORES"

    log "安装 Nginx..."
    make install
else
    log "检测到 Nginx 已安装在 $NGINX_INSTALL_DIR。跳过编译。"
fi

# 4. 编译 WRK
log "--- 步骤 3b/3: 编译和安装 WRK ---"
cd "$SRC_DIR"
if [ ! -d "wrk" ]; then
    log "克隆 WRK 仓库..."
    git clone "$WRK_DOWNLOAD_URL"
fi
cd "wrk"

if [ ! -f "$WRK_INSTALL_DIR/bin/wrk" ]; then
    log "编译 WRK (使用 ${BUILD_CORES} 个核心)..."
    make -j"$BUILD_CORES"

    log "安装 WRK 可执行文件到 $WRK_INSTALL_DIR/bin/"
    cp wrk "$WRK_INSTALL_DIR/bin/"
else
    log "检测到 WRK 已安装在 $WRK_INSTALL_DIR/bin/wrk。跳过编译。"
fi

# 5. 从模板生成 nginx.conf
log "--- 步骤 5/5: 从模板生成 nginx.conf ---"
NGINX_CONF_TEMPLATE="$SHOWCASE_DIR/config/nginx.conf.template"
mkdir -p "$(dirname "$NGINX_CONF_PATH")"

if [ ! -f "$NGINX_CONF_TEMPLATE" ]; then
    log "❌ 错误: 模板文件未找到: $NGINX_CONF_TEMPLATE" >&2
    exit 1
fi

# 使用 envsubst 动态替换模板中的变量
envsubst < "$NGINX_CONF_TEMPLATE" > "$NGINX_CONF_PATH"

# --- 完成 ---
touch "$SUCCESS_FLAG"
log "✅ Nginx Showcase 环境准备完成！"
log ""
log "--- 🚀 快速开始：一个典型的测试流程 ---"
log "你可以直接复制并粘贴以下命令来体验 Pipa:"
log ''
log '1. 启动 Nginx 服务器:'
log '   ./showcases/nginx/2_start_nginx_server.sh'
log ''
log '2. 运行性能基准测试:'
log '   ./showcases/nginx/3_run_performance_collection.sh'
log ''
log '3. (完成后) 停止 Nginx 服务器:'
log '   ./showcases/nginx/stop_nginx_server.sh'
log "-------------------------------------------"
