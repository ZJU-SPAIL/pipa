# Pipa Showcase: MySQL 性能分析场景

本案例演示了如何使用 PIPA 对一个**高负载 MySQL 数据库**进行“无侵入式”性能快照与诊断。

---

## 📋 前置要求

在开始之前，请确保已执行环境准备脚本。该脚本会自动编译 MySQL 8.0 和 Sysbench，并初始化测试数据。

```bash
# 首次运行需执行（耗时较长，请耐心等待）
./showcases/mysql/setup.sh
```

## 🚀 一键式终极测试 (推荐)

我们提供了一个自动化脚本，能够自动完成“启动服务 -> 施加极限负载 -> 执行 PIPA 采样 -> 生成报告 -> 清理环境”的全流程。

```bash
./showcases/mysql/ultimate_mysql_test.sh
```

**产出物：**

- `mysql_snapshot.pipa`: 原始数据快照包
- `mysql_report.html`: 交互式分析报告
- `mysql_flamegraph.svg`: 性能火焰图

---

## 🔬 手动分步操作指南

如果您希望手动控制分析流程，请参考以下步骤：

### 1. 启动 MySQL 服务

```bash
source ./showcases/mysql/env.sh
./showcases/mysql/start_mysql.sh
```

_脚本会输出 MySQL 进程的 PID，请留意。_

### 2. 施加压力 (Sysbench)

在另一个终端窗口中运行：

```bash
# 启动 32 线程的高并发读写测试
./showcases/mysql/run_sysbench.sh 32 &
```

### 3. 执行 PIPA 采样

```bash
# 1. 获取 MySQL PID
MYSQL_PID=$(pgrep -x mysqld)

# 2. 执行双阶段快照 (60秒宏观统计 + 60秒微观剖析)
pipa sample \
    --attach-to-pid "$MYSQL_PID" \
    --duration-stat 60 \
    --duration-record 60 \
    --output mysql_manual.pipa
```

### 4. 生成分析报告

```bash
pipa analyze --input mysql_manual.pipa --output report.html
```

### 5. 环境清理

测试完成后，请务必清理环境：

```bash
./showcases/mysql/stop_mysql.sh
pkill sysbench
```
