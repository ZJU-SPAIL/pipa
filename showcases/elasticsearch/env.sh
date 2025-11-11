#!/bin/bash

# =================================================================
# Pipa Showcase: Elasticsearch - 环境配置文件
# 这是本案例的“单一事实来源”(Single Source of Truth)。
# 在运行任何脚本之前，请先 source 此文件。
# =================================================================

# --- 核心路径定义 ---
# 获取此脚本所在的目录，作为 showcase 的根目录
export SHOWCASE_DIR
SHOWCASE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

# 所有构建产物和数据都将存放在 showcase 目录下的 build/ 子目录中
export BASE_DIR="$SHOWCASE_DIR/build"

# --- Elasticsearch 配置 ---
export ES_VERSION="7.12.1"
export ES_DOWNLOAD_URL="https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-${ES_VERSION}-linux-aarch64.tar.gz"
export ES_INSTALL_DIR="$BASE_DIR/elasticsearch"
export ES_DATA_DIR="$BASE_DIR/es_data"
# Python 虚拟环境将用于安装 esrally
export PYTHON_VENV_PATH="$BASE_DIR/venv_esrally"

# --- 集群与节点配置 ---
export ES_CLUSTER_NAME="pipa-es-cluster"
export ES_NODE_1_NAME="node-1"
export ES_NODE_2_NAME="node-2"
export ES_NODE_3_NAME="node-3"
export ES_NODE_1_CPU_AFFINITY="0-31"
export ES_NODE_2_CPU_AFFINITY="32-63"
export ES_NODE_3_CPU_AFFINITY="64-95"

# --- JVM 配置 ---
# 为每个 Elasticsearch 节点配置 16GB 的堆内存，以确保在高负载下稳定运行
export ES_JVM_HEAP="16g"

# --- 负载生成 (esrally) 配置 ---
export ES_BENCHMARK_CPU_AFFINITY="96-127"
export ES_RALLY_TRACK="geonames"
export ES_RALLY_CHALLENGE="append-no-conflicts"

# --- 信号配置 ---
# 这是 esrally 在后台日志中，标志着核心压测开始的真实信号
export ES_RALLY_WORKLOAD_SIGNAL="executing tasks: ['default']"
