#!/usr/bin/env bash

set -e
set -o pipefail

# =================================================================
# Pipa Showcase: 停止 Nginx 服务器
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

log "停止 Nginx 服务器..."

# 检查 PID 文件是否存在
if [ ! -f "$NGINX_PID_PATH" ]; then
    log "⚠️  警告: PID 文件不存在。尝试使用 pkill 强制杀死所有 nginx 进程..."
    pkill -f nginx || true
    exit 0
fi

# 获取 PID
NGINX_PID=$(cat "$NGINX_PID_PATH")

# 检查进程是否运行
if ! ps -p "$NGINX_PID" > /dev/null 2>&1; then
    log "⚠️  警告: PID $NGINX_PID 对应的进程不存在。清理 PID 文件..."
    rm -f "$NGINX_PID_PATH"
    exit 0
fi

# 发送停止信号
"$NGINX_INSTALL_DIR/sbin/nginx" -s stop

log "✅ 停止信号已发送，Nginx 已关闭。"
