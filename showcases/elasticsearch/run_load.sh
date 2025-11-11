#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Elasticsearch - 负载生成脚本
# 职责: 调用 esrally 对集群施加压力。
# =================================================================

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh" # 加载所有配置变量

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - LOAD - $1"
}

# --- 前置检查 ---
if ! pgrep -f "java.*elasticsearch" > /dev/null; then
    log "❌ 错误: Elasticsearch 集群未在运行。请先运行 start_es.sh。"
    exit 1
fi

if [ ! -x "$PYTHON_VENV_PATH/bin/esrally" ]; then
    log "❌ 错误: esrally 未找到或不可执行。请先运行 setup.sh。"
    exit 1
fi

# --- 运行负载 ---
log "--- 启动 esrally 负载 (Track: ${ES_RALLY_TRACK}, Challenge: ${ES_RALLY_CHALLENGE}) ---"
log "负载将施加在 CPU 核心: ${ES_BENCHMARK_CPU_AFFINITY}"

# 使用 taskset 绑定 esrally 进程到指定的 CPU 核心
# --kill-running-processes 确保每次都是一个干净的运行
taskset -c "$ES_BENCHMARK_CPU_AFFINITY" stdbuf -oL "$PYTHON_VENV_PATH/bin/esrally" race \
    --offline \
    --pipeline=benchmark-only \
    --target-hosts=127.0.0.1:9200,127.0.0.1:9201,127.0.0.1:9202 \
    --track="$ES_RALLY_TRACK" \
    --challenge="$ES_RALLY_CHALLENGE" \
    --kill-running-processes

log "✅ esrally 负载测试完成。"
