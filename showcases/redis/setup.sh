#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Redis - 环境准备脚本
# 职责: 自动化下载、编译和安装 Redis。
# =================================================================

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - SETUP - $1"
}

# --- 幂等性检查 ---
SUCCESS_FLAG="$BASE_DIR/.setup_success"
if [ -f "$SUCCESS_FLAG" ]; then
    log "✅ 检测到成功标志，环境已准备就绪。跳过所有步骤。"
    exit 0
fi

# --- 步骤 1: 安装编译依赖 ---
log "--- 步骤 1/5: 安装编译依赖 (gcc, make) ---"
sudo yum install -y gcc make

# --- 步骤 2: 创建目录结构 ---
log "--- 步骤 2/5: 创建目录结构 ---"
SRC_DIR="$BASE_DIR/src"
mkdir -p "$SRC_DIR" "$REDIS_INSTALL_DIR"

# --- 步骤 3: 下载并解压 Redis ---
log "--- 步骤 3/5: 下载并解压 Redis ${REDIS_VERSION} ---"
cd "$SRC_DIR"
REDIS_TARBALL="redis-${REDIS_VERSION}.tar.gz"
REDIS_SRC_DIR="redis-${REDIS_VERSION}"

if [ ! -f "$REDIS_TARBALL" ]; then
    wget -q --show-progress "$REDIS_DOWNLOAD_URL" -O "$REDIS_TARBALL"
fi
if [ ! -d "$REDIS_SRC_DIR" ]; then
    tar -zxf "$REDIS_TARBALL"
fi

# --- 步骤 4: 编译和安装 Redis ---
log "--- 步骤 4/5: 编译和安装 Redis ---"
cd "$REDIS_SRC_DIR"
log "正在编译 Redis (使用 $(nproc) 个核心)..."
make -j"$(nproc)"
log "正在安装 Redis 到 ${REDIS_INSTALL_DIR}..."
make PREFIX="$REDIS_INSTALL_DIR" install

# --- 步骤 5: 从模板生成 redis.conf ---
log "--- 步骤 5/5: 从模板生成 redis.conf ---"
REDIS_CONF_TEMPLATE="$SHOWCASE_DIR/config/redis.conf.template"
if [ ! -f "$REDIS_CONF_TEMPLATE" ]; then
    log "❌ 错误: 模板文件未找到: $REDIS_CONF_TEMPLATE" >&2
    exit 1
fi
# 使用 envsubst 动态替换模板中的变量
envsubst < "$REDIS_CONF_TEMPLATE" > "$REDIS_CONF_PATH"

# --- 完成 ---
touch "$SUCCESS_FLAG"
log "✅ Redis Showcase 环境准备完成！"
