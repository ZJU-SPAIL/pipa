#!/bin/bash

# =================================================================
# Pipa Showcase: Redis - 环境配置文件
# 这是本案例的“单一事实来源”(Single Source of Truth)。
# =================================================================

# --- 核心路径定义 ---
export SHOWCASE_DIR
SHOWCASE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

export BASE_DIR="$SHOWCASE_DIR/build"
export REDIS_INSTALL_DIR="$BASE_DIR/redis"

# --- Redis 配置 ---
export REDIS_VERSION="7.2.4"
export REDIS_DOWNLOAD_URL="http://download.redis.io/releases/redis-${REDIS_VERSION}.tar.gz"
export REDIS_PORT=6379
export REDIS_CONF_PATH="$REDIS_INSTALL_DIR/redis.conf" # 新增
export REDIS_PID_PATH="$BASE_DIR/redis.pid"           # 新增

# --- CPU 亲和性配置 (核心场景) ---
export REDIS_CPU_AFFINITY="0"
export BENCHMARK_CPU_AFFINITY="1-7"

# --- 压测工具 (redis-benchmark) 配置 ---
export BENCHMARK_CLIENTS=1
# 提高请求 QP在30w - 50w 之间波动
export BENCHMARK_REQUESTS=100000000
export BENCHMARK_PIPELINE=16
export BENCHMARK_DATA_SIZE=1024

# --- Pipa 采样配置 ---
export DURATION_STAT=60
export DURATION_RECORD=60
