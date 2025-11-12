#!/usr/bin/env bash

set -e
set -o pipefail

# =================================================================
# Pipa Showcase: 启动 Nginx 服务器
# =================================================================

# 获取脚本自身所在的目录
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

# 检查 env.sh 是否存在
if [ ! -f "$SCRIPT_DIR/env.sh" ]; then
    echo "❌ 错误: 配置文件 env.sh 未找到！" >&2
    exit 1
fi

# 加载环境变量
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - $1"
}

log "启动 Nginx 服务器..."

# 检查 Nginx 是否已在运行
if [ -f "$NGINX_PID_PATH" ] && ps -p "$(cat "$NGINX_PID_PATH")" > /dev/null 2>&1; then
    log "⚠️  警告: Nginx 已在运行，PID 为 $(cat "$NGINX_PID_PATH")"
    exit 0
fi

# 检查 Nginx 是否已安装
if [ ! -f "$NGINX_INSTALL_DIR/sbin/nginx" ]; then
    log "❌ 错误: Nginx 未安装。请先运行 1_setup_nginx_env.sh"
    exit 1
fi

# 使用 CPU 亲和性启动 Nginx
taskset -c "$NGINX_CPU_AFFINITY" "$NGINX_INSTALL_DIR/sbin/nginx" -c "$NGINX_CONF_PATH"

log "✅ Nginx 启动成功。"
log "   PID 文件: $NGINX_PID_PATH"
log "   访问地址: http://localhost:8000/"
