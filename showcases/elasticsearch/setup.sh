#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Elasticsearch 环境准备脚本 (v4 - 终极版)
# 职责: 自动化完成一个完全离线、高性能的测试环境所需的一切。
# =================================================================

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - SETUP - $1"
}

# --- 幂等性检查 ---
SUCCESS_FLAG="$BASE_DIR/.setup_success"
if [ -f "$SUCCESS_FLAG" ]; then
    log "✅ 检测到成功标志，环境已准备就绪。跳过所有步骤。"
    exit 0
fi

# --- 步骤 1: 安装系统依赖 (新增 pbzip2) ---
log "--- 步骤 1/7: 安装系统依赖 ---"
sudo yum install -y wget tar python3-devel python3-venv pbzip2

# --- 步骤 2 & 3: 创建目录 & 下载 ES (无变化) ---
log "--- 步骤 2/7: 创建目录结构 ---"
SRC_DIR="$BASE_DIR/src"
mkdir -p "$SRC_DIR" "$ES_INSTALL_DIR" "$ES_DATA_DIR"

log "--- 步骤 3/7: 下载并解压 Elasticsearch ${ES_VERSION} ---"
cd "$SRC_DIR"
ES_TARBALL="elasticsearch-${ES_VERSION}-linux-aarch64.tar.gz"
ES_SRC_DIR_NAME="elasticsearch-${ES_VERSION}"
if [ ! -f "$ES_TARBALL" ]; then
    wget -q --show-progress "$ES_DOWNLOAD_URL" -O "$ES_TARBALL"
fi
if [ ! -d "$ES_SRC_DIR_NAME" ]; then
    tar -zxf "$ES_TARBALL"
fi

# --- 步骤 4: 配置 3 节点集群 (使用新环境变量) ---
log "--- 步骤 4/7: 配置 3 节点集群 (堆内存: ${ES_JVM_HEAP}) ---"
NODES=("$ES_NODE_1_NAME" "$ES_NODE_2_NAME" "$ES_NODE_3_NAME")
# ... (for 循环保持不变)
for i in "${!NODES[@]}"; do
    NODE_NAME=${NODES[$i]}
    NODE_DIR="$ES_INSTALL_DIR/$NODE_NAME"
    log "配置节点: ${NODE_NAME}..."
    rm -rf "$NODE_DIR"
    cp -R "$SRC_DIR/$ES_SRC_DIR_NAME" "$NODE_DIR"
    # ... (envsubst 保持不变)
    export NODE_NAME HTTP_PORT=$((9200 + i)) TRANSPORT_PORT=$((9300 + i)) ES_CLUSTER_NAME
    if [ "$i" -eq 0 ]; then export INITIAL_MASTER_NODE_CONFIG="cluster.initial_master_nodes: [\"${NODE_NAME}\"]"; else export INITIAL_MASTER_NODE_CONFIG=""; fi
    envsubst < "$SHOWCASE_DIR/config/elasticsearch.yml.template" > "$NODE_DIR/config/elasticsearch.yml"

    # 添加 perf map 支持
    JVM_OPTIONS_FILE="$NODE_DIR/config/jvm.options"
    if ! grep -q "DumpPerfMapAtExit" "$JVM_OPTIONS_FILE"; then echo -e "\n-XX:+UnlockDiagnosticVMOptions\n-XX:+DumpPerfMapAtExit" >> "$JVM_OPTIONS_FILE"; fi

    # 核心修复: 配置堆内存
    JVM_HEAP_CONFIG_FILE="$NODE_DIR/config/jvm.options.d/heap.options"
    mkdir -p "$(dirname "$JVM_HEAP_CONFIG_FILE")"
    echo "-Xms${ES_JVM_HEAP}" > "$JVM_HEAP_CONFIG_FILE"
    echo "-Xmx${ES_JVM_HEAP}" >> "$JVM_HEAP_CONFIG_FILE"
    log "   -> 已为节点 ${NODE_NAME} 配置 ${ES_JVM_HEAP} JVM 堆内存。"
done

# --- 步骤 5: 配置 esrally (无变化) ---
log "--- 步骤 5/7: 配置 Python 虚拟环境和 esrally ---"
if [ ! -d "$PYTHON_VENV_PATH" ]; then
    python3 -m venv "$PYTHON_VENV_PATH"
fi
source "$PYTHON_VENV_PATH/bin/activate"
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install esrally -i https://pypi.tuna.tsinghua.edu.cn/simple
deactivate

# --- 步骤 6 & 7: 自动化数据准备 ---
log "--- 步骤 6/7: 准备 esrally 数据集 ---"
RALLY_DATA_DIR="$HOME/.rally/benchmarks/data"
GEONAMES_DIR="$RALLY_DATA_DIR/geonames"
DECOMPRESSED_FILE="$GEONAMES_DIR/documents-2.json"

if [ -f "$DECOMPRESSED_FILE" ]; then
    log "✅ 检测到已解压的数据文件，跳过数据准备。"
else
    log "开始数据准备流程..."
    mkdir -p "$GEONAMES_DIR"

    COMPRESSED_FILE_URL="https://rally-tracks.elastic.co/geonames/documents-2.json.bz2"
    COMPRESSED_FILE_TARGET="$GEONAMES_DIR/documents-2.json.bz2"

    if [ ! -f "$COMPRESSED_FILE_TARGET" ]; then
        log "下载 geonames 数据集 (约 253MB)..."
        wget -q --show-progress "$COMPRESSED_FILE_URL" -O "$COMPRESSED_FILE_TARGET"
    else
        log "检测到已下载的压缩文件。"
    fi

    log "--- 步骤 7/7: 预解压数据集 (约 3.3GB)... ---"
    log "使用 pbzip2 进行并行解压，这将花费几分钟..."
    pbzip2 -d -k "$COMPRESSED_FILE_TARGET"

    if [ -f "$DECOMPRESSED_FILE" ]; then
        log "✅ 数据集预解压完成！"
    else
        log "❌ 错误: 解压失败，未找到 ${DECOMPRESSED_FILE}。"
        exit 1
    fi
fi

# --- 完成 ---
touch "$SUCCESS_FLAG"
log "✅ Elasticsearch Showcase 终极环境准备完成！"
