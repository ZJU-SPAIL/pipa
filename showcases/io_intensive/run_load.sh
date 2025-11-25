#!/bin/bash
set -e
set -o pipefail

# =================================================================
# Pipa Showcase: IO Intensive - FIO 负载生成器
# =================================================================

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - LOAD - $1"
}

# 前置检查
if ! command -v fio &>/dev/null; then
    log "❌ 错误: FIO 未安装。请运行 ./setup.sh 查看说明。"
    exit 1
fi

# 确保目录存在
if [ ! -d "$IO_TARGET_DIR" ]; then
    mkdir -p "$IO_TARGET_DIR"
fi

TARGET_FILE="$IO_TARGET_DIR/$IO_FILENAME"

log "--- 启动 FIO 极限压测 ---"
log "目标文件: $TARGET_FILE"
log "配置: $IO_MODE, BS=$IO_BLOCK_SIZE, Depth=$IO_DEPTH x $IO_NUMJOBS, Size=$IO_SIZE_PER_JOB"

# 启动 FIO
# group_reporting: 汇总所有 Job 的数据
# time_based: 即使文件写完了，也要跑满 runtime 时间
fio \
    --name=pipa_stress \
    --filename="$TARGET_FILE" \
    --ioengine="$IO_ENGINE" \
    --rw="$IO_MODE" \
    --bs="$IO_BLOCK_SIZE" \
    --direct="$IO_DIRECT" \
    --size="$IO_SIZE_PER_JOB" \
    --numjobs="$IO_NUMJOBS" \
    --iodepth="$IO_DEPTH" \
    --runtime="$IO_DURATION" \
    --time_based \
    --group_reporting

log "✅ 压测完成。"

# 清理 (可选，FIO 默认保留文件以便复用)
# rm -f "$TARGET_FILE"
