# pipa - Design & Architecture Document

# pipa - 设计与架构文档

This document outlines the core design philosophy and architectural principles behind the pipa framework.
本文档概述了 pipa 框架背后的核心设计哲学和架构原则。

---

## 1. Core Philosophy: The Pure Performance Snapshot Tool

## 1. 核心哲学：纯粹的性能快照工具

- **Observer, Not an Actor:** Pipa **observes** running systems; it never starts, stops, or manages any process's lifecycle. Its sole purpose is to be a pure, non-intrusive data collector.

  - **观察者，而非执行者:** Pipa **观察**正在运行的系统；它从不启动、停止或管理任何进程的生命周期。它的唯一目标是成为一个纯粹的、非侵入式的数据采集器。

- **User in Control:** The user is responsible for managing the workload and its lifecycle. Pipa's job is to provide a high-quality "CT scan" of the system's performance at the exact moment the user needs it.

  - **用户掌控一切:** 用户对工作负载及其生命周期负责。Pipa 的职责是在用户需要的确切时刻，为系统性能提供一次高质量的“CT 扫描”。

- **Simplicity by Subtraction:** We achieve simplicity not by adding features, but by ruthlessly removing everything that is not essential to the core mission of performance snapshotting. The removal of workload management (`--workload`, `--intensity`) is a direct manifestation of this principle.
  - **少即是多:** 我们的简洁性并非通过增加功能实现，而是通过无情地移除一切与性能快照这一核心使命无关的东西。对工作负载管理功能（`--workload`, `--intensity`）的移除，正是这一原则的直接体现。

---

## 2. Core Workflow: `sample` -> `analyze`

## 2. 核心工作流: `sample` -> `analyze`

The user journey is a simple, two-stage process:
用户旅程是一个简单的两阶段过程：

### 2.1 Stage 1: `sample` - The Snapshot Engine

### 2.1 第一阶段：`sample` - 快照引擎

- **Mechanism:** Attaches to user-specified PIDs and orchestrates a suite of standard Linux performance tools (`perf`, `sar`, etc.) to run concurrently for a specified duration.
  - **机制：** 依附于用户指定的 PID，并编排一套标准的 Linux 性能工具（`perf`, `sar` 等），在指定时间内并发运行。
- **Configuration:** It uses a built-in, general-purpose set of collectors by default, ensuring it works out-of-the-box. Advanced users can provide a custom collector configuration via the `--collectors-config` option.
  - **配置：** 默认使用一套内置的、通用的采集器，确保开箱即用。高级用户可以通过 `--collectors-config` 选项提供自定义的采集器配置。
- **Output:** A single, self-contained **`.pipa` archive**, making the results portable and ready for analysis.
  - **产出物：** 一个独立的、自包含的 **`.pipa` 归档文件**，使得结果可移植并为分析做好准备。

### 2.2 Stage 2: `analyze` - The Insight Engine

### 2.2 第二阶段：`analyze` - 洞察引擎

- **Mechanism:** Unpacks the `.pipa` archive, parses all raw data files, aligns them on a common time axis, and runs a rule-based analysis.
  - **机制：** 解包 `.pipa` 归档，解析所有原始数据文件，将它们在共同的时间轴上对齐，并运行基于规则的分析。
- **Output:** A user-friendly, self-contained HTML report that presents findings, visualizations, and raw data in an explorable format.
  - **产出物：** 一份用户友好的、自包含的 HTML 报告，以可探索的格式呈现分析结论、可视化图表和原始数据。
