#!/bin/bash
set -e

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - STOP - $1"
}

log "--- 正在执行终极清理程序 ---"

# --- 阶段 1: 猎杀 esrally 进程蜂群 ---
log "阶段 1: 终止 esrally 进程..."
if pgrep -f "esrally race" > /dev/null; then
    # 使用我们验证过的、最高效的地毯式轰炸
    pkill -f "esrally race" || true
    sleep 1
    pkill -9 -f "esrally race" || true
    log "   -> 所有 'esrally race' 进程已被强制终止。"
else
    log "   -> 未检测到 'esrally race' 进程。"
fi

# --- 阶段 2: 优雅地停止 Elasticsearch 集群 ---
log "阶段 2: 终止 Elasticsearch 进程..."
if pgrep -f "java.*elasticsearch" > /dev/null; then
    # 尝试优雅关闭
    pkill -f "java.*elasticsearch"

    # 等待最多 30 秒
    retries=15
    while [ $retries -gt 0 ] && pgrep -f "java.*elasticsearch" > /dev/null; do
        echo -n "."
        sleep 2
        ((retries--))
    done
    echo "" # 换行

    # 如果仍在运行，则强制终止
    if pgrep -f "java.*elasticsearch" > /dev/null; then
        log "   -> ES 进程未能优雅关闭，强制终止..."
        pkill -9 -f "java.*elasticsearch"
    fi
    log "   -> 所有 Elasticsearch 进程已停止。"
else
    log "   -> 未检测到 Elasticsearch 进程。"
fi

# --- 阶段 3: 清理 esrally 日志 ---
RALLY_LOG_FILE="$HOME/.rally/logs/rally.log"
if [ -f "$RALLY_LOG_FILE" ]; then
    > "$RALLY_LOG_FILE"
    log "阶段 3: 已清空 esrally 日志文件。"
fi

log "✅ 终极清理完成。"
