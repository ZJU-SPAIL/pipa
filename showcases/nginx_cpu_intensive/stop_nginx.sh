#!/usr/bin/env bash

set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Nginx - 停止脚本 (v2 - 终极清理版)
# 职责: 无论 Nginx 处于何种状态，都能可靠地终止所有相关进程。
# =================================================================

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - STOP - $1"
}

log "--- 正在执行 Nginx 终极清理程序 ---"

# --- 阶段 1: 终止 WRK 负载进程 ---
log "阶段 1: 终止 wrk 进程..."
if pgrep -f "wrk" > /dev/null; then
    pkill -f "wrk" || true
    sleep 1
    pkill -9 -f "wrk" || true
    log "   -> 所有 'wrk' 进程已被强制终止。"
else
    log "   -> 未检测到 'wrk' 进程。"
fi

# --- 阶段 2: 终止 Nginx 进程 ---
log "阶段 2: 终止 Nginx 进程..."
if pgrep -f "nginx: master process" > /dev/null; then
    # 尝试优雅关闭
    if [ -f "$NGINX_INSTALL_DIR/sbin/nginx" ]; then
        "$NGINX_INSTALL_DIR/sbin/nginx" -s stop > /dev/null 2>&1 || true
        log "   -> 已发送优雅停止信号。"
    else
        log "   -> Nginx 可执行文件未找到，将使用 pkill。"
        pkill -f "nginx: master process" || true
    fi

    # 等待最多 10 秒
    retries=5
    while [ $retries -gt 0 ] && pgrep -f "nginx" > /dev/null; do
        echo -n "."
        sleep 2
        ((retries--))
    done
    echo "" # 换行

    # 如果仍在运行，则强制终止
    if pgrep -f "nginx" > /dev/null; then
        log "   -> Nginx 进程未能优雅关闭，强制终止..."
        pkill -9 -f "nginx" || true
    fi
    log "   -> 所有 Nginx 进程已停止。"
else
    log "   -> 未检测到 Nginx 进程。"
fi

# --- 清理 PID 文件 ---
if [ -f "$NGINX_PID_PATH" ]; then
    rm -f "$NGINX_PID_PATH"
    log "   -> 已清理 PID 文件。"
fi

log "✅ Nginx 终极清理完成。"
