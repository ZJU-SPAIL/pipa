#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Redis - 负载生成脚本
# 职责: 调用 redis-benchmark 对 Redis 施加压力。
# =================================================================

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - LOAD - $1"
}

REDIS_BENCHMARK_BIN="$REDIS_INSTALL_DIR/bin/redis-benchmark"
if [ ! -x "$REDIS_BENCHMARK_BIN" ]; then
    log "❌ 错误: redis-benchmark 未找到。请先运行 setup.sh。"
    exit 1
fi

log "--- 启动 redis-benchmark 负载 ---"
log "CPU 亲和性: ${BENCHMARK_CPU_AFFINITY}, 客户端: ${BENCHMARK_CLIENTS}, 请求数: ${BENCHMARK_REQUESTS}"

# -t set,get: 同时测试写和读
# -d: 数据大小
# -P: Pipelining
taskset -c "$BENCHMARK_CPU_AFFINITY" "$REDIS_BENCHMARK_BIN" \
    -p "$REDIS_PORT" \
    -c "$BENCHMARK_CLIENTS" \
    -n "$BENCHMARK_REQUESTS" \
    -P "$BENCHMARK_PIPELINE" \
    -d "$BENCHMARK_DATA_SIZE" \
    -t set,get

log "✅ redis-benchmark 负载测试完成。"
