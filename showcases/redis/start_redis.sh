#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Redis - 启动脚本
# 职责: 1. 后台启动 Redis; 2. 验证启动成功; 3. 按协议输出 PID。
# =================================================================

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - START - $1"
}

# --- 前置检查 ---
if [ -f "$REDIS_PID_PATH" ] && ps -p "$(cat "$REDIS_PID_PATH")" > /dev/null 2>&1; then
    log "❌ 错误: Redis 进程似乎已在运行。请先运行 stop_redis.sh。"
    exit 1
fi

REDIS_SERVER_BIN="$REDIS_INSTALL_DIR/bin/redis-server"
if [ ! -x "$REDIS_SERVER_BIN" ]; then
    log "❌ 错误: Redis 未安装。请先运行 setup.sh。"
    exit 1
fi

# --- 启动 Redis ---
log "启动 Redis 服务器 (配置文件: ${REDIS_CONF_PATH}, CPU 亲和性: ${REDIS_CPU_AFFINITY})..."
taskset -c "$REDIS_CPU_AFFINITY" "$REDIS_SERVER_BIN" "$REDIS_CONF_PATH"

# --- 验证与 PID 捕获 ---
log "等待 Redis 启动并响应 (最多 10 秒)..."
retries=5
server_ready=false
while [ $retries -gt 0 ]; do
    if [ -f "$REDIS_PID_PATH" ] && "$REDIS_INSTALL_DIR/bin/redis-cli" -p "$REDIS_PORT" ping | grep -q "PONG"; then
        server_ready=true
        break
    fi
    sleep 1
    ((retries--))
done

if ! $server_ready; then
    log "❌ 错误: 在 10 秒内 Redis 未能成功启动。"
    exit 1
fi

# --- 核心: 从 PID 文件读取 PID ---
REDIS_PID=$(cat "$REDIS_PID_PATH")
if [ -z "$REDIS_PID" ]; then
    log "❌ 错误: 未能从 PID 文件中读取到 Redis 进程 ID。"
    exit 1
fi

log "✅ Redis 已成功启动，PID: ${REDIS_PID}"

# --- 协议输出 ---
echo ""
echo "PIDs for pipa: ${REDIS_PID}"
