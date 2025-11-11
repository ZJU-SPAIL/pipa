#!/bin/bash
set -e

# =================================================================
# Pipa Showcase: Elasticsearch - 停止脚本
# 职责: 可靠、干净地停止所有 Elasticsearch Java 进程。
# =================================================================

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh" # 加载配置以备将来扩展

log() {
    echo "[$(date +'%Y-%-m-%d %H:%M:%S')] - STOP - $1"
}

log "--- 正在停止所有 Elasticsearch 进程 ---"

if pgrep -f "java.*elasticsearch" > /dev/null; then
    # 使用 pkill 发送 SIGTERM 信号，允许进程优雅关闭
    pkill -f "java.*elasticsearch"

    # 等待进程退出
    retries=15
    while [ $retries -gt 0 ] && pgrep -f "java.*elasticsearch" > /dev/null; do
        log "等待进程关闭... ($retries retries left)"
        sleep 2
        ((retries--))
    done

    if pgrep -f "java.*elasticsearch" > /dev/null; then
        log "警告: 进程未能优雅关闭，强制终止..."
        pkill -9 -f "java.*elasticsearch"
    fi

    log "✅ 所有 Elasticsearch 进程已停止。"
else
    log "没有检测到正在运行的 Elasticsearch 进程。"
fi
