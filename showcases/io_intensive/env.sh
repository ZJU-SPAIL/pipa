#!/bin/bash

# =================================================================
# Pipa Showcase: IO Intensive - 环境配置文件
# =================================================================

# --- 核心路径 ---
export SHOWCASE_DIR
SHOWCASE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

# --- 压测目标配置 ---
# 默认在当前 showcase 的 build 目录下生成
# 用户可以通过修改此变量，指向特定的挂载点 (例如 /mnt/hdd_data/fio_test_file)
export IO_TARGET_DIR="$SHOWCASE_DIR/build"
export IO_FILENAME="fio_test_file"

# --- 压测参数 (FIO HDD Killer) ---
# 引擎: libaio (Linux 异步 IO 标准)
export IO_ENGINE="libaio"
# 模式: randwrite (随机写，HDD 杀手)
export IO_MODE="randwrite"
# 块大小: 4k (小块 IO，拉高 IOPS)
export IO_BLOCK_SIZE="4k"
# Direct IO: 1 (绕过 Page Cache，直击物理盘)
export IO_DIRECT="1"
# 深度: 64 (单 Job 深度)
export IO_DEPTH="64"
# 并发: 8 (Job 数量 -> 总深度 512)
export IO_NUMJOBS="8"
# 文件大小: 10G (总写入量 = 10G * 8 = 80G)
export IO_SIZE_PER_JOB="10G"
# 时长: 300s
export IO_DURATION="300"
