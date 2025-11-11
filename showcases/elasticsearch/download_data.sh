#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Elasticsearch - 数据下载脚本
# 职责: 联网下载 esrally 所需的 track 数据集。
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

log "--- 开始下载 track: ${ES_RALLY_TRACK} ---"
log "此过程可能需要很长时间，具体取决于您的网络速度和数据集大小。"
log "数据集将被下载到 ~/.rally/benchmarks/data/"

# 调用 esrally download 命令
"$PYTHON_VENV_PATH/bin/esrally" download --track="$ES_RALLY_TRACK"

log "✅ 数据集下载完成。"
log "现在您可以在离线环境中使用 run_load.sh --offline 进行压测了。"
