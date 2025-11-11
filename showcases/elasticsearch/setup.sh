#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Elasticsearch 环境准备脚本 (v2 - Pipa 范式)
# 职责: 编译、安装、初始化 Elasticsearch 和 esrally。
# 特性: 幂等性、配置模板化、清晰日志、依赖 env.sh。
# =================================================================

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh" # 加载所有配置变量

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - SETUP - $1"
}

# --- 幂等性检查 ---
SUCCESS_FLAG="$BASE_DIR/.setup_success"
if [ -f "$SUCCESS_FLAG" ]; then
    log "✅ 检测到成功标志，环境已准备就绪。跳过所有步骤。"
    log "如需强制重新准备，请先删除目录: rm -rf $BASE_DIR"
    exit 0
fi

# --- 步骤 1: 安装系统依赖 ---
log "--- 步骤 1/5: 安装系统依赖 ---"
sudo yum install -y wget tar python3-devel

# --- 步骤 2: 创建目录结构 ---
log "--- 步骤 2/5: 创建目录结构 ---"
SRC_DIR="$BASE_DIR/src"
mkdir -p "$SRC_DIR" "$ES_INSTALL_DIR" "$ES_DATA_DIR"

# --- 步骤 3: 下载并解压 Elasticsearch ---
log "--- 步骤 3/5: 下载并解压 Elasticsearch ${ES_VERSION} ---"
cd "$SRC_DIR"
ES_TARBALL="elasticsearch-${ES_VERSION}-linux-aarch64.tar.gz"
ES_SRC_DIR_NAME="elasticsearch-${ES_VERSION}"

if [ ! -f "$ES_TARBALL" ]; then
    log "下载 Elasticsearch from ${ES_DOWNLOAD_URL}..."
    wget -q --show-progress "$ES_DOWNLOAD_URL" -O "$ES_TARBALL"
fi

if [ ! -d "$ES_SRC_DIR_NAME" ]; then
    log "解压 Elasticsearch..."
    tar -zxf "$ES_TARBALL"
fi

# --- 步骤 4: 配置 3 节点集群 ---
log "--- 步骤 4/5: 配置 3 节点集群 ---"
NODES=("$ES_NODE_1_NAME" "$ES_NODE_2_NAME" "$ES_NODE_3_NAME")
HTTP_PORTS=(9200 9201 9202)
TRANSPORT_PORTS=(9300 9301 9302)
CONF_TEMPLATE="$SHOWCASE_DIR/config/elasticsearch.yml.template"

for i in "${!NODES[@]}"; do
    NODE_NAME=${NODES[$i]}
    NODE_DIR="$ES_INSTALL_DIR/$NODE_NAME"
    log "配置节点: ${NODE_NAME}..."

    rm -rf "$NODE_DIR"
    cp -R "$SRC_DIR/$ES_SRC_DIR_NAME" "$NODE_DIR"

    # 动态生成配置文件
    export NODE_NAME
    export HTTP_PORT=${HTTP_PORTS[$i]}
    export TRANSPORT_PORT=${TRANSPORT_PORTS[$i]}
    export ES_CLUSTER_NAME
    # 仅为第一个节点设置 initial_master_nodes
    if [ "$i" -eq 0 ]; then
        export INITIAL_MASTER_NODE_CONFIG="cluster.initial_master_nodes: [\"${NODE_NAME}\"]"
    else
        export INITIAL_MASTER_NODE_CONFIG=""
    fi
    envsubst < "$CONF_TEMPLATE" > "$NODE_DIR/config/elasticsearch.yml"

    # 为 perf 火焰图添加 JVM 选项 (幂等)
    JVM_OPTIONS_FILE="$NODE_DIR/config/jvm.options"
    if ! grep -q "DumpPerfMapAtExit" "$JVM_OPTIONS_FILE"; then
        echo -e "\n-XX:+UnlockDiagnosticVMOptions\n-XX:+DumpPerfMapAtExit" >> "$JVM_OPTIONS_FILE"
    fi
done

# --- 步骤 5: 配置 esrally ---
log "--- 步骤 5/5: 配置 Python 虚拟环境和 esrally ---"
if [ ! -d "$PYTHON_VENV_PATH" ]; then
    python3 -m venv "$PYTHON_VENV_PATH"
fi
source "$PYTHON_VENV_PATH/bin/activate"
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install esrally -i https://pypi.tuna.tsinghua.edu.cn/simple
deactivate

log "验证 esrally 安装..."
"$PYTHON_VENV_PATH/bin/esrally" list tracks

# --- 完成 ---
touch "$SUCCESS_FLAG"
log "✅ Elasticsearch Showcase 环境准备完成！"
log "下一步: 运行 ./showcases/elasticsearch/start_es.sh 来启动集群。"
