# Pipa Showcase: Redis 性能分析

本案例演示了如何使用 PIPA 对 Redis 数据库进行性能快照与诊断，特别关注在高并发下 **Redis 单线程模型的 CPU 瓶颈** 特征。

---

## 📋 前置要求

在开始之前，请执行环境准备脚本

```bash
# 首次运行需执行
./showcases/redis/setup.sh
```

## 🚀 一键式测试

我们提供了一个自动化脚本，能够一键完成“启动服务 -> 施加高并发负载 -> 执行 PIPA 采样 -> 生成报告 -> 清理环境”的全流程。

```bash
./showcases/redis/ultimate_redis_test.sh
```

**产出物：**

- redis_snapshot.pipa: 包含性能数据的快照文件
- redis_report.html: 交互式分析报告
- redis_flamegraph.svg: 性能火焰图

---

## 🔬 手动分步操作指南

### 1. 启动 Redis 服务

```bash
source ./showcases/redis/env.sh
./showcases/redis/start_redis.sh
```

_注意: Redis Server 将被绑定到 CPU 核心 0。_

### 2. 施加压力 (redis-benchmark)

在**另一个终端窗口**中运行：

```bash
# 启动 redis-benchmark 进行高并发读写测试
./showcases/redis/run_load.sh &
```

### 3. 执行 PIPA 采样

```bash
# 1. 获取 Redis 的 PID
REDIS_PID=$(pgrep -f "redis-server.*:6379")

# 2. 执行双阶段快照
pipa sample \
    --attach-to-pid "$REDIS_PID" \
    --duration-stat 60 \
    --duration-record 60 \
    --output redis_manual.pipa
```

### 4. 生成分析报告

```bash
pipa analyze --input redis_manual.pipa --output report.html
pipa flamegraph --input redis_manual.pipa --output flame.svg
```

### 5. 环境清理

测试完成后，请务必运行清理脚本，以确保所有后台进程被正确终止。

```bash
./showcases/redis/stop_redis.sh
```
