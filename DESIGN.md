# pipa - Design & Architecture Document

# pipa - 设计与架构文档

This document outlines the core design philosophy and architectural principles behind the pipa framework, updated for the v0.4.0 "Physics-Aware" release.
本文档概述了 pipa 框架背后的核心设计哲学和架构原则，已为 v0.4.0 “物理感知”版本更新。

---

## 1. Core Philosophy / 核心哲学

- **Observer, Not an Actor:** Pipa **observes** running systems; it never starts, stops, or manages any process's lifecycle. Its sole purpose is to be a pure, non-intrusive data collector.

  - **观察者，而非执行者:** Pipa **观察**正在运行的系统；它从不启动、停止或管理任何进程的生命周期。它的唯一目标是成为一个纯粹的、非侵入式的数据采集器。

- **User in Control:** The user is responsible for managing the workload. Pipa's job is to provide a high-quality "CT scan" of the system's performance at the exact moment the user needs it.

  - **用户掌控一切:** 用户对工作负载负责。Pipa 的职责是在用户需要的确切时刻，为系统性能提供一次高质量的“CT 扫描”。

- **Physics-Aware, Not Average-Blind:** Pipa is designed to understand the physical realities of modern hardware. It moves beyond simple averages to detect micro-level phenomena, such as single-core bottlenecks on a 128-core system, or throughput saturation on a low-latency SSD.
  - **物理感知，而非平均值盲视:** Pipa 的设计旨在理解现代硬件的物理现实。它超越了简单的平均值，以检测微观层面的现象，例如 128 核系统上的单核瓶颈，或低延迟 SSD 上的吞吐量饱和。

---

## 2. Core Workflow: `healthcheck` -> `sample` -> `analyze`

## 2. 核心工作流: `healthcheck` -> `sample` -> `analyze`

The user journey is a simple, three-stage process:
用户旅程是一个简单的三阶段过程：

### 2.1 Stage 1: `healthcheck` - The System Interrogator

### 2.1 第一阶段：`healthcheck` - 系统审问器

- **Mechanism:** Collects static, one-time system information (CPU topology, NUMA nodes, disk models, OS version).
  - **机制：** 采集静态的、一次性的系统信息（CPU 拓扑、NUMA 节点、磁盘型号、OS 版本）。
- **Purpose:** Provides essential context for the `analyze` phase, enabling physics-aware diagnostics.
  - **目的：** 为 `analyze` 阶段提供必要的上下文，以实现物理感知诊断。

### 2.2 Stage 2: `sample` - The Snapshot Engine

### 2.2 第二阶段：`sample` - 快照引擎

- **Mechanism:** Attaches to user-specified PIDs or runs system-wide, orchestrating a suite of standard Linux tools (`perf`, `sar`) to run concurrently.
  - **机制：** 依附于用户指定的 PID 或以系统模式运行，编排一套标准的 Linux 工具（`perf`, `sar`）并发执行。
- **Output:** A single, self-contained **`.pipa` archive**, containing all raw data files for offline analysis.
  - **产出物：** 一个独立的、自包含的 **`.pipa` 归档文件**，包含所有用于离线分析的原始数据。

### 2.3 Stage 3: `analyze` - The Three-Tier Insight Engine

### 2.3 第三阶段：`analyze` - 三层洞察引擎

This is the intelligent core of PIPA. It processes the `.pipa` archive through a three-tier analysis pipeline:
这是 PIPA 的智能核心。它通过一个三层分析管道处理 `.pipa` 归档：

- **Tier 1: Configuration Audit Engine**
  - **Purpose:** The pre-check layer. Validates if the runtime environment matches the user's expectation.
  - **Input:** `--expected-cpus` parameter.
  - **Output:** Detects `Leakage` (unexpected busy cores) or `Absent` (underutilized reserved cores).
- **Tier 2: System-Level Diagnosis Engine**
  - **Purpose:** The macro-level diagnosis layer. Identifies system-wide bottlenecks like I/O, memory, or CPU imbalances.
  - **Core Component:** The YAML-based **Decision Tree** (`decision_tree.yaml`).
  - **Output:** Generates `Diagnostic Findings` based on the physics-aware rule set.
- **Tier 3: Code-Level Profiling Engine**
  - **Purpose:** The micro-level drill-down layer. Pinpoints which specific functions are consuming CPU.
  - **Core Component:** The **Hotspot Extractor** (`hotspots.py`), which automates `perf report`.
  - **Output:** The interactive "Top CPU Hotspots" table, with support for offline symbol resolution (`--symfs`).

---

## 3. High-Level Architecture / 高层架构

The data flow within the `analyze` command follows a clear pipeline:
`analyze` 命令内部的数据流遵循一个清晰的管道：

```
[ .pipa Archive ]
       |
       v
[ Parsers (`parsers/`) ] -> (Raw DataFrames)
       |
       v
[ Context Builder (`context_builder.py`) ] -> (Derived Metrics & Features)
       |
       v
[ Three-Tier Analysis Engine ]
       |
       +--- [ Tier 1: Audit (`--expected-cpus`) ]
       |
       +--- [ Tier 2: Decision Tree (`decision_tree.yaml`) ]
       |
       +--- [ Tier 3: Hotspots (`hotspots.py`) ]
       |
       v
[ HTML Generator (`html_generator.py`) ] -> (Interactive Report)
```
