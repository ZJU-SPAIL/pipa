# pipa - Project Roadmap

# pipa - 项目路线图

This document outlines the planned development milestones for the pipa project, reflecting its new focus as a pure performance snapshot tool.
本文档概述了 pipa 项目规划的开发里程碑，反映了其作为纯粹性能快照工具的新焦点。

---

## ✅ Version 0.2.0: The Great Refactoring

## ✅ 版本 0.2.0：伟大的重构

- **Status:** ✔️ Completed
- **状态:** ✔️ 已完成
- **Goal:** To pivot the project from a complex workload management platform to a simple, robust, user-centric performance snapshot tool.
- **目标：** 将项目从一个复杂的工作负载管理平台，转型为一个简单、健壮、以用户为中心的性能快照工具。
- **Key Achievements / 关键成就:**
  - [x] **Removed `calibrate` command** and all adaptive logic. / **移除了 `calibrate` 命令**及所有自适应逻辑。
  - [x] **Removed workload management**: The tool no longer starts, stops, or drives any application. / **移除了工作负载管理**：工具不再启动、停止或驱动任何应用。
  - [x] **Simplified `sample` command** to a pure attach-only (`--attach-to-pid`) workflow. / **简化了 `sample` 命令**，使其成为一个纯粹的、仅支持依附（`--attach-to-pid`）的工作流。
  - [x] **Modernized data pipeline**: Replaced fragile text parsing with robust binary collection (`sar -o`) and reliable conversion (`sadf`). / **现代化了数据管道**：用健壮的二进制采集（`sar -o`）和可靠的转换（`sadf`）取代了脆弱的文本解析。
  - [x] **Implemented per-core data collection** for `perf stat` (`-A`) to enable finer-grained analysis. / **实现了 `perf stat` 的 per-core 数据采集**（`-A`），以支持更精细的分析。

## 🚀 Version 0.3.0: Deep Analysis & Physics-Aware Engine (Released)

- **Status:** ✔️ Released
- **Goal:** 引入物理感知诊断引擎，实现从宏观到微观的全链路可视化。
- **Key Features / 关键特性:**
  - [x] **Physics-Aware Clustering**: 基于 DBSCAN 的物理感知核心聚类，破除平均值掩盖效应。
  - [x] **NUMA Diagnostics**: 跨节点负载失衡检测与架构风险告警。
  - [x] **Storage Visualization**: 交互式磁盘旭日图 + 分区级容量预警。
  - [x] **TMA Integration**: 微架构瓶颈分析 (Frontend/Backend Bound) 与决策树集成。
  - [ ] **Compare Command**: (Planned for v0.3.1) 差分对比分析。
