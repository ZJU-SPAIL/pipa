#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: IO Intensive - 数据准备脚本
# 职责: 在目标磁盘上生成测试文件 (100GB+)。
# 特性: 阻塞运行，直到文件生成完毕。
# =================================================================

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - PREPARE - $1"
}

SYSBENCH_BIN="$SYSBENCH_INSTALL_DIR/bin/sysbench"

if [ ! -x "$SYSBENCH_BIN" ]; then
    log "❌ 错误: Sysbench 未找到。请先运行 './setup.sh'。"
    exit 1
fi

# 确保目录存在
mkdir -p "$BASE_DIR"
cd "$BASE_DIR"

# 解析目标大小 (100G -> 100, 100M -> 0.1 等，简化处理只支持 G)
TARGET_SIZE_GB=$(echo $IO_FILE_TOTAL_SIZE | sed 's/G//')
TARGET_SIZE_KB=$((TARGET_SIZE_GB * 1024 * 1024))

log "--- 开始生成测试数据 ($IO_FILE_TOTAL_SIZE) ---"
log "目标目录: $(pwd)"

# --- 启动进度监控 (后台) ---
(
    while true; do
        # 计算当前目录下 test_file.* 的总大小 (KB)
        CURRENT_SIZE_KB=$(du -sk . | cut -f1)

        # 简单的百分比计算
        if [ "$TARGET_SIZE_KB" -gt 0 ]; then
            PERCENT=$((CURRENT_SIZE_KB * 100 / TARGET_SIZE_KB))
        else
            PERCENT=0
        fi

        # 限制最大显示为 99% (防止 du 计算偏差导致超过 100)
        if [ "$PERCENT" -gt 99 ]; then PERCENT=99; fi

        # 打印进度条
        # \r 回车不换行，实现在同一行刷新
        # printf "[%-50s] %d%%" 定义一个 50 字符宽的进度条
        HASHES=$((PERCENT / 2))
        printf "\rProgress: [%-50s] %d%% (%d GB / %d GB)" \
            $(printf "#%.0s" $(seq 1 $HASHES)) \
            "$PERCENT" \
            $((CURRENT_SIZE_KB / 1024 / 1024)) \
            "$TARGET_SIZE_GB"

        sleep 2
    done
) &
MONITOR_PID=$!

# --- 执行 Sysbench (阻塞) ---
"$SYSBENCH_BIN" fileio \
    --file-total-size=$IO_FILE_TOTAL_SIZE \
    --file-num=128 \
    prepare > /dev/null 2>&1

# --- 结束监控 ---
kill $MONITOR_PID 2>/dev/null
wait $MONITOR_PID 2>/dev/null || true

# 打印最终 100%
printf "\rProgress: [%-50s] 100%% (%d GB / %d GB)\n" \
    $(printf "#%.0s" $(seq 1 50)) \
    "$TARGET_SIZE_GB" "$TARGET_SIZE_GB"

log "✅ 数据准备完成。"
