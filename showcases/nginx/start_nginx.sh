#!/usr/bin/env bash

set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Nginx - 启动脚本 (v2 - 协议兼容版)
# 职责: 1. 后台启动 Nginx; 2. 验证启动成功; 3. 按协议输出 Worker PIDs。
# =================================================================

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - START - $1"
}

log "启动 Nginx 服务器..."

# --- 前置检查 ---
if [ -f "$NGINX_PID_PATH" ] && ps -p "$(cat "$NGINX_PID_PATH")" > /dev/null 2>&1; then
    log "⚠️  警告: Nginx 已在运行，PID 为 $(cat "$NGINX_PID_PATH")"
else
    if [ ! -f "$NGINX_INSTALL_DIR/sbin/nginx" ]; then
        log "❌ 错误: Nginx 未安装。请先运行 setup.sh"
        exit 1
    fi
    # 使用 CPU 亲和性启动 Nginx
    taskset -c "$NGINX_CPU_AFFINITY" "$NGINX_INSTALL_DIR/sbin/nginx" -c "$NGINX_CONF_PATH"
fi

# --- 验证与 PID 捕获 ---
log "等待 Nginx 启动并稳定 (最多 10 秒)..."
retries=5
pids_found=false
while [ $retries -gt 0 ]; do
    # 核心逻辑: 查找所有 worker 进程
    NGINX_WORKER_PIDS=$(pgrep -f "nginx: worker process" | tr '\n' ',' | sed 's/,$//')
    if [ -n "$NGINX_WORKER_PIDS" ]; then
        pids_found=true
        break
    fi
    sleep 2
    ((retries--))
done

if ! $pids_found; then
    log "❌ 错误: 在 10 秒内未能找到任何 Nginx worker 进程。"
    exit 1
fi

log "✅ Nginx 已成功启动。"
log "   -> Master PID: $(cat "$NGINX_PID_PATH")"
log "   -> Worker PIDs: ${NGINX_WORKER_PIDS}"

# --- 协议输出 ---
# 这是为自动化脚本 (如 ultimate_nginx_test.sh) 提供的、纯净的、可捕获的输出
echo ""
echo "PIDs for pipa: ${NGINX_WORKER_PIDS}"
