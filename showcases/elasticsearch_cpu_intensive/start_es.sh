#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Elasticsearch - 启动脚本
# 职责: 1. 后台启动3节点集群; 2. 应用CPU亲和性; 3. 打印PID列表。
# =================================================================

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh" # 加载所有配置变量

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - START - $1"
}

# --- 前置检查 ---
if pgrep -f "java.*elasticsearch" > /dev/null; then
    log "❌ 错误: Elasticsearch 进程似乎已在运行。请先运行 stop_es.sh。"
    exit 1
fi

if [ ! -d "$ES_INSTALL_DIR/$ES_NODE_1_NAME" ]; then
    log "❌ 错误: Elasticsearch 节点目录未找到。请先运行 setup.sh。"
    exit 1
fi

# --- 启动节点 ---
log "--- 启动 Elasticsearch 3 节点集群 ---"

# --- 增加 JVM 版本日志记录 ---
log "检查并记录 Java 版本..."
if [ -x "$ES_INSTALL_DIR/$ES_NODE_1_NAME/jdk/bin/java" ]; then
    JAVA_CMD="$ES_INSTALL_DIR/$ES_NODE_1_NAME/jdk/bin/java"
    log "使用的 Java 版本: $($JAVA_CMD -version 2>&1 | head -n 1)"
else
    log "警告: 未找到 Elasticsearch 内置 JDK，将依赖系统 Java。"
fi

NODES=("$ES_NODE_1_NAME" "$ES_NODE_2_NAME" "$ES_NODE_3_NAME")
AFFINITIES=("$ES_NODE_1_CPU_AFFINITY" "$ES_NODE_2_CPU_AFFINITY" "$ES_NODE_3_CPU_AFFINITY")

for i in "${!NODES[@]}"; do
    NODE_NAME=${NODES[$i]}
    NODE_DIR="$ES_INSTALL_DIR/$NODE_NAME"
    AFFINITY=${AFFINITIES[$i]}

    log "启动节点 ${NODE_NAME} (CPU 亲和性: ${AFFINITY})..."
    # 使用 taskset 绑定 CPU，并在后台启动
    LOG_FILE="$NODE_DIR/logs/startup.log"
    mkdir -p "$(dirname "$LOG_FILE")"
    taskset -c "$AFFINITY" "$NODE_DIR/bin/elasticsearch" > "$LOG_FILE" 2>&1 &
done

# --- 等待并验证 ---
log "等待集群启动 (最多 60 秒)..."
retries=30
cluster_ready=false
while [ $retries -gt 0 ]; do
    # 检查 9200 端口是否返回了有效的 JSON
    if curl -s "http://127.0.0.1:9200" | grep -q "cluster_name"; then
        cluster_ready=true
        break
    fi
    sleep 2
    ((retries--))
done

if ! $cluster_ready; then
    log "❌ 错误: 集群在 60 秒内未能成功启动。请检查日志: ${ES_INSTALL_DIR}/*/logs/"
    exit 1
fi

log "✅ 集群已成功启动并响应。"

# --- 核心: 查找并打印所有 PID ---
ES_PIDS=$(pgrep -f "java.*elasticsearch" | tr '\n' ',' | sed 's/,$//')

if [ -z "$ES_PIDS" ]; then
    log "❌ 错误: 未能找到任何正在运行的 Elasticsearch Java 进程。"
    exit 1
fi

log "✅ 所有 Elasticsearch 节点已在运行，PID 列表: ${ES_PIDS}"
echo ""
echo "PIDs for pipa: ${ES_PIDS}" # 纯净的输出，方便脚本捕获
