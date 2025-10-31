# pipa - Design & Architecture Document
# pipa - 设计与架构文档

This document outlines the core design philosophy, architectural principles, and key technical decisions behind the pipa framework. It serves as the "why" behind our code.
本文档概述了 pipa 框架背后的核心设计哲学、架构原则和关键技术决策。它阐释了我们代码背后的“为什么”。

---

## 1. Core Philosophy: The Adaptive Performance Experimentation Platform
## 1. 核心哲学：自适应性能实验平台

Traditional performance tools operate on a static, pre-configured basis. They assume the user knows exactly what to measure and how to configure the load. This approach is brittle and not portable across different environments.
传统的性能工具基于静态、预配置的方式运行。它们假设用户确切地知道要测量什么以及如何配置负载。这种方法是脆弱的，并且在不同环境间不具备可移植性。

pipa is founded on a different philosophy: it is an **adaptive performance experimentation platform**.
pipa 建立在一种不同的哲学之上：它是一个**自适应的性能实验平台**。

*   **It does not assume; it discovers.** Instead of asking the user for low-level parameters, it asks for high-level goals (e.g., "find the bottleneck at 80% CPU utilization").
    *   **它从不假设，而是去发现。** 它不向用户索要低阶参数，而是询问高阶目标（例如，“找到 CPU 利用率在 80% 时的瓶颈”）。
*   **It automates the experiment, not just the collection.** Its core innovation is the ability to automatically calibrate the environment to find the correct parameters for a scientifically valid experiment.
    *   **它自动化实验，而不仅是采集。** 其核心创新在于能够自动校准环境，为一次科学有效的实验找到正确的参数。
*   **It is environment-agnostic.** A pipa test defined on an 8-core developer machine will intelligently adapt itself to run correctly on a 128-core production server.
    *   **它环境无关。** 一个在 8 核开发机上定义的 pipa 测试，将能智能地自我调整，以在一个 128 核的生产服务器上正确运行。

---

## 2. The Three-Stage Workflow: A Journey from Goal to Insight
## 2. 三阶段工作流：从目标到洞察的旅程

pipa's user journey is intentionally designed as a clear, three-stage process. This separation of concerns is a fundamental architectural choice.
pipa 的用户旅程被刻意设计为一个清晰的三阶段过程。这种关注点分离是一个根本性的架构选择。

### 2.1 Stage 1: `calibrate` - The "Pre-warm" Engine
### 2.1 第一阶段：`calibrate` - “预热”引擎

This stage is the heart of pipa's adaptive nature.
这个阶段是 pipa 自适应特性的核心。

*   **Problem Solved:** It answers the question, "What does 'high load' even mean on this specific machine for this specific workload?"
    *   **解决的问题：** 它回答了“对于这个特定的工作负载，在这台特定的机器上，‘高负载’到底意味着什么？”这个问题。
*   **Mechanism:** It employs a **feedback loop** (e.g., binary search) to actively probe the target system.
    *   **机制：** 它采用**反馈循环**（例如，二分查找）来主动探测目标系统。
*   **Output:** A `_calibrated.yaml` file. This file is a **machine-specific, reproducible "experiment card"** that locks in the parameters for the actual sampling run.
    *   **产出物：** 一个 `_calibrated.yaml` 文件。这个文件是一张**特定于机器的、可复现的“实验卡片”**，它锁定了用于实际采样运行的参数。

### 2.2 Stage 2: `sample` - The "Hermetic" Collection Engine
### 2.2 第二阶段：`sample` - “密封的”采集引擎

This stage executes the experiment with scientific rigor.
这个阶段以科学的严谨性来执行实验。

*   **Problem Solved:** It ensures that data collection is performed in a fully automated, repeatable, and non-interactive manner.
    *   **解决的问题：** 它确保了数据采集以一种全自动、可重复且非交互的方式进行。
*   **Mechanism:** It implements the classic **"Two-Minute Macro-to-Micro"** profiling strategy for each calibrated load level.
    *   **机制：** 它为每个校准过的负载等级，执行经典的**“两分钟宏观到微观”**画像策略。
*   **Output:** A single, self-contained **`.pipa` archive**. This makes the experimental results portable, easy to share, and ready for offline analysis.
    *   **产出物：** 一个独立的、自包含的 **`.pipa` 归档文件**。这使得实验结果可移植、易于分享，并为离线分析做好了准备。

### 2.3 Stage 3: `analyze` - The "Insight" Engine
### 2.3 第三阶段：`analyze` - “洞察”引擎

This stage turns data into answers.
这个阶段将数据转化为答案。

*   **Problem Solved:** It automates the tedious and error-prone process of parsing log files and correlating different data sources.
    *   **解决的问题：** 它自动化了那个繁琐且易错的解析日志文件和关联不同数据源的过程。
*   **Mechanism:**
    *   **Macro Analysis (The "Decision Tree"):** A simple, Python-based rules engine applies configurable `if-then` heuristics to generate high-level conclusions.
        *   **宏观分析（“决策树”）：** 一个简单的、基于 Python 的规则引擎，应用可配置的 `if-then` 启发式规则来生成高阶结论。
    *   **Micro Analysis (Differential Flame Graphs):** It compares profiles from different load levels to identify functions whose CPU consumption **grows non-linearly**, flagging them as hotspot bottlenecks.
        *   **微观分析（差分火焰图）：** 它对比来自不同负载等级的画像，以识别那些 CPU 消耗**非线性增长**的函数，并将它们标记为热点瓶颈。
*   **Architectural Benefit:** It produces a final, user-friendly HTML report that presents a clear, evidence-based story.
    *   **架构优势：** 它产出一份最终的、用户友好的 HTML 报告，呈现一个清晰的、基于证据的故事。

---

## 3. The "Load Driver" Abstraction: The Key to Extensibility
## 3. “负载驱动程序”抽象：可扩展性的关键

A core design goal of pipa is to be workload-agnostic. The main engine should not have any hardcoded knowledge of "MySQL" or "Nginx". This is achieved through the **Load Driver** architectural pattern.
pipa 的一个核心设计目标是工作负载无关。主引擎不应包含任何关于 “MySQL” 或 “Nginx” 的硬编码知识。这一点通过**负载驱动程序**架构模式得以实现。

*   **The Interface:** The core engine (`pipa.py`) only knows how to interact with a generic "Load Driver" interface.
    *   **接口：** 核心引擎 (`pipa.py`) 只知道如何与一个通用的“负载驱动程序”接口进行交互。
*   **The Implementation:** This interface is implemented via a `workload.yaml` configuration file for each specific workload.
    *   **实现：** 这个接口通过为每个特定工作负载配置一个 `workload.yaml` 文件来实现。
*   **The Contract:** Each `workload.yaml` must define how to start/stop the service and how to control the benchmark's intensity.
    *   **契约：** 每个 `workload.yaml` 必须定义如何启动/停止服务，以及如何控制基准测试的强度。

This powerful abstraction means that supporting a completely new workload requires **zero changes to pipa's core Python code**. The user simply provides a new YAML file that teaches pipa how to "drive" the new workload. This makes the framework infinitely extensible.
这种强大的抽象意味着，支持一个全新的工作负载**无需对 pipa 的核心 Python 代码做任何更改**。用户只需提供一个新的 YAML 文件，教会 pipa 如何“驱动”这个新的工作负载。这使得框架拥有了无限的可扩展性。
