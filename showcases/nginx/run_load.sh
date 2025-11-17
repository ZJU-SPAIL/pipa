#!/usr/bin/env bash

set -e
set -o pipefail

# =================================================================
# Pipa Showcase: Nginx - 负载生成脚本 (v2 - 自动化兼容版)
# 职责: 调用 wrk 对 Nginx 施加持续的压力。
# =================================================================

# --- 脚本初始化 ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

# --- 前置检查 ---
if [ ! -f "$WRK_INSTALL_DIR/bin/wrk" ]; then
    echo "❌ 错误: WRK 未安装。请先运行 setup.sh" >&2
    exit 1
fi

# 检查 Nginx 是否正在运行
if ! pgrep -f "nginx: master process" > /dev/null; then
    echo "❌ 错误: Nginx 服务器未在运行。请先运行 start_nginx.sh" >&2
    exit 1
fi

# --- 核心执行逻辑 ---
# 在自动化脚本 (ultimate_nginx_test.sh) 中，这个脚本将在后台运行。
# 它会持续施加压力，直到被 ultimate 脚本的 cleanup 机制或手动停止。
# 我们将标准输出重定向到 /dev/null，以避免污染 Pipa 的日志。
taskset -c "$WRK_CPU_AFFINITY" "$WRK_INSTALL_DIR/bin/wrk" \
    -t"$WRK_THREADS" -c"$WRK_CONNECTIONS" -d"$WRK_DURATION" \
    -H "Connection: keep-alive" "$WRK_TARGET_URL" > /dev/null
