#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Elasticsearch - 数据下载脚本
# 职责: 联网触发 esrally 下载指定 track 的数据集。
#       此脚本应在可以访问外网的环境中运行一次。
# =================================================================

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh" # 加载配置变量

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - DOWNLOAD - $1"
}

# --- 前置检查 ---
if [ ! -x "$PYTHON_VENV_PATH/bin/esrally" ]; then
    log "❌ 错误: esrally 未安装。请先运行 setup.sh 来创建虚拟环境。"
    exit 1
fi

RALLY_DATA_DIR="$HOME/.rally/benchmarks/data"
# 检查数据是否已经存在，如果存在则跳过，实现幂等性
if [ -d "$RALLY_DATA_DIR/$ES_RALLY_TRACK" ]; then
    log "✅ 检测到 track [${ES_RALLY_TRACK}] 的数据已存在于 ${RALLY_DATA_DIR}。跳过下载。"
    exit 0
fi


log "--- 开始准备 track: ${ES_RALLY_TRACK} 的数据 ---"
log "esrally 将会自动下载所需的数据集。此过程可能需要很长时间。"
log "数据集将被下载到 ${RALLY_DATA_DIR}/"

# 运行一个 race 命令是触发数据下载的标准方式。
# 我们使用 --track-params 来限制只跑一个文档，并指定 --test-mode
# 这样做的目的是最小化 benchmark 本身的开销，只关注数据准备。
# 注意：即使在 test-mode 下，它仍然会下载完整的数据集。
"$PYTHON_VENV_PATH/bin/esrally" race \
    --track="$ES_RALLY_TRACK" \
    --test-mode \
    --pipeline=benchmark-only \
    --target-hosts=127.0.0.1:9200

log "✅ 数据集准备完成。"
log "现在您可以在离线环境中使用 run_load.sh --offline 进行压测了。"
