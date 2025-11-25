# Pipa Showcase: Elasticsearch 集群性能分析

本案例构建了一个 **3 节点 Elasticsearch 集群**，并使用官方基准测试工具 **esrally** 在离线模式下模拟真实业务负载，用于展示 PIPA 在分布式 Java 应用下的诊断能力。

---

## 📋 前置要求

该脚本会自动下载并配置 ES 7.12.1 集群及 geonames 数据集。

```bash
# 首次运行需执行（会自动配置 JDK 和 Python 虚拟环境）
./showcases/elasticsearch/setup.sh
```

## 🚀 一键式终极测试 (推荐)

这是最简单的运行方式。脚本会自动处理复杂的 ES 集群引导、数据注入和 esrally 负载同步。

```bash
./showcases/elasticsearch/ultimate_es_test.sh
```

**产出物：**

- `elasticsearch_snapshot.pipa`: 包含所有节点性能数据的快照
- `elasticsearch_report.html`: 详细的集群性能分析报告
- `elasticsearch_flamegraph.svg`: Java 混合模式火焰图

---

## 🔬 手动分步操作指南

### 1. 启动 ES 集群

```bash
source ./showcases/elasticsearch/env.sh
./showcases/elasticsearch/start_es.sh
```

_脚本会启动 3 个节点，并分别绑定到不同的 CPU 核心组上。_

### 2. 施加压力 (esrally)

```bash
# 启动 esrally 进行 race 测试（离线模式）
./showcases/elasticsearch/run_load.sh &
```

### 3. 执行 PIPA 采样

```bash
# 1. 获取所有 ES 节点的 PID
ES_PIDS=$(pgrep -f "java.*elasticsearch" | tr '\n' ',' | sed 's/,$//')

# 2. 执行采样 (建议开启静态信息采集以辅助 NUMA 分析)
pipa sample \
    --attach-to-pid "$ES_PIDS" \
    --duration-stat 60 \
    --duration-record 60 \
    --output es_manual.pipa
```

### 4. 生成报告

```bash
pipa analyze --input es_manual.pipa --output report.html
```

### 5. 环境清理

**重要：** 测试结束后请运行清理脚本，以确保所有 Java 进程和后台 esrally 进程被正确终止。

```bash
./showcases/elasticsearch/stop_es.sh
```
