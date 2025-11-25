#!/bin/bash
set -e

# =================================================================
# Pipa Showcase: IO Intensive - 环境检查脚本
# 职责: 检查系统是否已安装 FIO。
# =================================================================

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - SETUP - $1"
}

log "检查 FIO 工具..."

if ! command -v fio &>/dev/null; then
    log "❌ 错误: 未找到 'fio' 命令。"
    log "   请使用系统包管理器安装: "
    log "   - Ubuntu/Debian: sudo apt-get install fio"
    log "   - CentOS/OpenEuler: sudo yum install fio"
    exit 1
fi

FIO_PATH=$(command -v fio)
FIO_VERSION=$(fio --version)
log "✅ FIO 已就绪: $FIO_PATH ($FIO_VERSION)"

# 准备目录
mkdir -p "$IO_TARGET_DIR"
log "✅ 测试目录已准备: $IO_TARGET_DIR"
