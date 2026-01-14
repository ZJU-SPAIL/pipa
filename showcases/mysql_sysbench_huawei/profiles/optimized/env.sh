#!/bin/bash
# profiles/optimized/env.sh - 针对鲲鹏 920 & 高并发锁竞争优化的配置

export DESCRIPTION="Optimized for High Concurrency & Kunpeng 920 (Reduced Lock Contention)"

# 1. 核心并发调优：将 Buffer Pool 切分为 64 个实例，大幅减少实例级的 Mutex 竞争
export INNODB_BP_INSTANCES=64

# 2. 减法优化：禁用自适应哈希索引 (AHI)。在 ARM 多核下，AHI 的全局锁往往是万恶之源。
export INNODB_AHI=OFF

# 3. 架构适配：增加旋转锁延迟。减少 ARM 核间缓存一致性风暴。
export INNODB_SPIN_WAIT_DELAY=24

# 4. 辅助调优：减少 LRU 扫描深度，降低背景线程对 CPU 的占用。
export INNODB_LRU_SCAN_DEPTH=256

# 5. 为了让线看起来更短，稍微降低一点线程并发到 32 (与之前对比)，或维持 32 以观察调优后的“线条缩短效果”。
export SYSBENCH_THREADS=32
