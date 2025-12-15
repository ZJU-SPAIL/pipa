#!/usr/bin/env bash

set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Nginx - 启动脚本 (V3 - 稳健PID捕获版)
# 职责: 1. 后台启动 Nginx; 2. 验证启动成功; 3. 按协议输出 Worker PIDs。
# =================================================================

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - START - $1"
}

log "启动 Nginx 服务器..."

# --- 0. 清理旧 PID 文件 (防止误读) ---
if [ -f "$NGINX_PID_PATH" ]; then
    rm -f "$NGINX_PID_PATH"
fi

# --- 1. 启动逻辑 ---
if pgrep -f "nginx: master process" > /dev/null 2>&1; then
    log "⚠️  警告: Nginx 似乎已在运行，尝试复用..."
else
    if [ ! -f "$NGINX_INSTALL_DIR/sbin/nginx" ]; then
        log "❌ 错误: Nginx 未安装。请先运行 setup.sh"
        exit 1
    fi
    # 使用 CPU 亲和性启动 Nginx
    taskset -c "$NGINX_CPU_AFFINITY" "$NGINX_INSTALL_DIR/sbin/nginx" -c "$NGINX_CONF_PATH"
fi

# --- 2. [核心修复] 稳健等待 PID 文件生成 ---
log "等待 Nginx PID 文件生成 (最多 5 秒)..."
retries=50 # 50 * 0.1s = 5s
while [ ! -f "$NGINX_PID_PATH" ] && [ $retries -gt 0 ]; do
    sleep 0.1
    ((retries--))
done

if [ ! -f "$NGINX_PID_PATH" ]; then
    log "⚠️  警告: PID 文件未生成 (可能 Nginx 启动失败或配置错误)。尝试通过 pgrep 获取 Master PID..."
    MASTER_PID=$(pgrep -f "nginx: master process" | head -1)
else
    MASTER_PID=$(cat "$NGINX_PID_PATH")
fi

if [ -z "$MASTER_PID" ]; then
    log "❌ 错误: Nginx 启动失败，未找到 Master 进程。"
    tail -n 20 "$NGINX_LOGS_DIR/error.log" 2>/dev/null
    exit 1
fi

log "✅ Nginx 已成功启动。Master PID: $MASTER_PID"

# --- 3. 验证 Worker 进程并捕获 PIDs ---
log "等待 Worker 进程就绪..."
retries=50
pids_found=false
while [ $retries -gt 0 ]; do
    # 核心逻辑: 查找所有 worker 进程
    NGINX_WORKER_PIDS=$(pgrep -f "nginx: worker process" | tr '\n' ',' | sed 's/,$//')
    if [ -n "$NGINX_WORKER_PIDS" ]; then
        pids_found=true
        break
    fi
    sleep 0.2
    ((retries--))
done

# 4. 获取 Worker PIDs
NGINX_WORKER_PIDS=$(pgrep -f "nginx: worker process" | tr '\n' ',' | sed 's/,$//')

if [ -z "$NGINX_WORKER_PIDS" ]; then
    log "⚠️  警告: 未找到 Worker 进程 (可能配置为单进程模式?)"
    NGINX_WORKER_PIDS=$MASTER_PID
fi

# =========================================================
# [修复] 恢复原本的日志格式，把 Master PID 加回来！
# =========================================================
log "✅ Nginx 已成功启动。"
log "   -> Master PID: $MASTER_PID"  # <--- 这里！不用 cat 文件，直接用变量
log "   -> Worker PIDs: $NGINX_WORKER_PIDS"

# 5. 协议输出 (给脚本抓取用的)
echo ""
echo "PIDs for pipa: ${NGINX_WORKER_PIDS}"
