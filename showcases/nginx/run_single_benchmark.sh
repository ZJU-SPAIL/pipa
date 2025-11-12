#!/usr/bin/env bash

set -e
set -o pipefail

# =================================================================
# Pipa Showcase: 运行单次 WRK 基准测试
# =================================================================

# 获取脚本自身所在的目录
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

# 检查 env.sh 是否存在
if [ ! -f "$SCRIPT_DIR/env.sh" ]; then
    echo "❌ 错误: 配置文件 env.sh 未找到！" >&2
    exit 1
fi

# 加载环境变量
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - $1"
}

log "运行 WRK 基准测试..."
log "重要: 请确保 Nginx 服务器正在运行。使用 ./2_start_nginx_server.sh 启动"

# 检查 WRK 是否已安装
if [ ! -f "$WRK_INSTALL_DIR/bin/wrk" ]; then
    log "❌ 错误: WRK 未安装。请先运行 1_setup_nginx_env.sh"
    exit 1
fi

log "--- 保活连接测试 (Keep-Alive) ---"
taskset -c "$WRK_CPU_AFFINITY" "$WRK_INSTALL_DIR/bin/wrk" \
    -t"$WRK_THREADS" -c"$WRK_CONNECTIONS" -d"$WRK_DURATION" \
    -H "Connection: keep-alive" "$WRK_TARGET_URL"

log ""
log "--- 关闭连接测试 (Close) ---"
taskset -c "$WRK_CPU_AFFINITY" "$WRK_INSTALL_DIR/bin/wrk" \
    -t"$WRK_THREADS" -c"$WRK_CONNECTIONS" -d"$WRK_DURATION" \
    -H "Connection: close" "$WRK_TARGET_URL"

log "✅ 基准测试完成。"
