# pipa - Project Roadmap

# pipa - 项目路线图

This document outlines the planned development milestones for the pipa project. It serves as a high-level guide to our priorities and future ambitions. The roadmap is a living document and may evolve over time.

本文档概述了 pipa 项目规划的开发里程碑。它作为我们优先级和未来雄心的高阶指南。该路线图是一份动态文档，可能会随时间演进。

---

## मील Milestone-Based Plan / 基于里程碑的计划

### 🚀 Version 0.1.0: The Foundation (MVP)

### 🚀 版本 0.1.0：奠定基础 (最小可行产品)

- **Status:** 🚧 In Progress
- **状态:** 🚧 进行中
- **Goal:** Deliver a functional, end-to-end command-line tool that proves the core "Calibrate -> Sample -> Analyze" workflow.
- **目标：** 交付一个功能性的、端到端的命令行工具，以验证核心的“校准 -> 采样 -> 分析”工作流。
- **Key Features / 关键特性:**
  - [x] Establish core project structure and documentation. / 建立核心项目结构和文档。
  - [ ] Implement the `calibrate` command with adaptive CPU utilization targeting. / 实现带有自适应 CPU 利用率目标的 `calibrate` 命令。
  - [ ] Implement the `sample` command for automated, three-level data collection. / 实现 `sample` 命令，用于自动化的三级数据采集。
  - [ ] Implement the `analyze` command with a basic Python-based decision tree. / 实现 `analyze` 命令，使用基础的、基于 Python 的决策树。
  - [ ] Initial support for **MySQL** workload via the Load Driver abstraction. / 通过负载驱动程序抽象，初步支持 **MySQL** 工作负载。
  - [ ] Basic unit tests for `processor` and `analyzer` modules. / 为 `processor` 和 `analyzer` 模块编写基础单元测试。

### ✈️ Version 0.2.0: Broadening Horizons

### ✈️ 版本 0.2.0：拓宽视野

- **Status:** 📋 Planned
- **状态:** 📋 计划中
- **Goal:** Expand workload support and enhance the analysis capabilities.
- **目标：** 扩展工作负载支持，并增强分析能力。
- **Key Features / 关键特性:**
  - [ ] Add Load Driver support for **Nginx**. / 增加对 **Nginx** 的负载驱动程序支持。
  - [ ] Add Load Driver support for **Elasticsearch**. / 增加对 **Elasticsearch** 的负载驱动程序支持。
  - [ ] Implement initial **Differential Flame Graph** generation in the `analyze` report. / 在 `analyze` 报告中，实现初步的**差分火焰图**生成。
  - [ ] Refine the command-line interface for better user experience. / 优化命令行界面以提升用户体验。

### 🛰️ Version 1.0.0: The Polished Release

### 🛰️ 版本 1.0.0：精炼发布

- **Status:** 📋 Planned
- **状态:** 📋 计划中
- **Goal:** A stable, feature-rich release suitable for wider use.
- **目标：** 一个稳定、功能丰富的版本，适合更广泛的使用。
- **Key Features / 关键特性:**
  - [ ] Interactive HTML report with filterable data and visualizations. / 带有可筛选数据和交互式可视化的 HTML 报告。
  - [ ] Full CI/CD pipeline for automated testing and release packaging. / 完整的 CI/CD 流水线，用于自动化测试和发布打包。
  - [ ] Comprehensive user documentation. / 详尽的用户文档。
  - [ ] Pluggable analysis rule engine, allowing users to provide their own rule sets. / 可插拔的分析规则引擎，允许用户提供自己的规则集。

### 🌌 Future: The Rust Frontier (pipa-rs)

### 🌌 未来：Rust 前沿 (pipa-rs)

- **Status:** 🔭 Research
- **状态:** 🔭 探索中
- **Goal:** Explore rewriting the performance-critical collection engine in Rust for maximum efficiency and reliability.
- **目标：** 探索用 Rust 重写性能关键的采集引擎，以获得最高的效率和可靠性。
- **Key Ideas / 核心思想:**
  - Continue to use Python as the high-level workflow orchestrator. / 继续使用 Python 作为高阶工作流的编排器。
  - Replace the `subprocess` calls to `perf` with a Rust binary that interacts **directly with the `perf_event_open` syscall**. / 将对 `perf` 的 `subprocess` 调用，替换为一个**直接与 `perf_event_open` 系统调用交互**的 Rust 二进制程序。
  - This would eliminate the dependency on the system's `perf` tool and remove the overhead of parsing text output. / 这将消除对系统 `perf` 工具的依赖，并移除解析文本输出的开销。
