#!/bin/bash
set -e

# =================================================================
# Pipa Showcase: Redis - 停止与清理脚本
# =================================================================

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - STOP - $1"
}

log "--- 正在执行 Redis 终极清理程序 ---"

# --- 阶段 1: 终止 redis-benchmark ---
log "阶段 1: 终止 redis-benchmark 进程..."
pkill -f "redis-benchmark" || true
log "   -> 'redis-benchmark' 进程清理完毕。"

# --- 阶段 2: 终止 Redis 服务器 ---
log "阶段 2: 终止 Redis 进程..."
if [ -f "$REDIS_PID_PATH" ] && ps -p "$(cat "$REDIS_PID_PATH")" > /dev/null 2>&1; then
    log "   -> 通过 redis-cli shutdown 命令优雅关闭..."
    "$REDIS_INSTALL_DIR/bin/redis-cli" -p "$REDIS_PORT" shutdown nosave || true

    retries=5
    while [ $retries -gt 0 ] && [ -f "$REDIS_PID_PATH" ]; do
        echo -n "."
        sleep 1
        ((retries--))
    done
    echo ""
else
    log "   -> PID 文件不存在或进程已停止。"
fi

# --- 兜底清理 ---
if pgrep -f "redis-server.*:${REDIS_PORT}" > /dev/null; then
    log "   -> Redis 未能优雅关闭，强制终止..."
    pkill -9 -f "redis-server.*:${REDIS_PORT}" || true
fi

# 清理 PID 文件
rm -f "$REDIS_PID_PATH"

log "✅ Redis 清理完成。"
