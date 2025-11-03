# PIPA (An Adaptive Performance Experimentation Platform)

# PIPA (一个自适应性能实验平台)

**pipa is an adaptive, command-line performance experimentation platform designed for complex systems. It bridges the gap between raw metric collection and actionable insights by automating the entire performance analysis workflow, from environment calibration to final reporting.**

**pipa 是一个为复杂系统设计的自适应、命令行的性能实验平台。它通过自动化从环境校准到最终报告的完整性能分析工作流，弥合了原始指标收集与可行动洞察之间的鸿沟。**

---

## ✨ Core Features / 核心特性

- **🚀 Adaptive Calibration (`calibrate`):** Automatically discovers the optimal load parameters (e.g., threads, connections) for your specific hardware to achieve target system states (e.g., 20% CPU, 80% CPU). Say goodbye to guesswork.
  - **🚀 自适应校准 (`calibrate`):** 针对您的特定硬件，自动发现最优的负载参数（如线程数、连接数），以达到目标系统状态（如 20% CPU, 80% CPU）。告别猜测。
- **🤖 Fully Automated Sampling (`sample`):** Executes a reproducible, multi-stage data collection process based on a calibrated plan. It captures both high-level system metrics (`sar`, `perf stat`) and deep, function-level profiles (`perf record`).
  - **🤖 全自动采样 (`sample`):** 基于校准过的计划，执行一个可复现的、多阶段的数据采集流程。它能同时捕获高阶系统指标（`sar`, `perf stat`）和深度的函数级画像（`perf record`）。
- **📊 Insightful Analysis (`analyze`):** Transforms raw data into a rich HTML report, featuring a rule-based decision tree for macro-bottleneck identification and **differential flame graphs** to pinpoint micro-level hotspots that emerge under pressure.
  - **📊 富有洞察的分析 (`analyze`):** 将原始数据转换为内容丰富的 HTML 报告，其特色在于：使用基于规则的决策树进行宏观瓶颈识别，并利用**差分火焰图**来精确定位在压力下出现的微观层面热点。
- **🔧 Universal & Extensible:** Built on a **"Load Driver"** architecture. Supporting new workloads (like Redis or PostgreSQL) requires only adding a simple YAML configuration file, with zero changes to the core engine.
  - **🔧 通用与可扩展:** 构建于**“负载驱动程序”**架构之上。支持新的工作负载（如 Redis 或 PostgreSQL）仅需添加一个简单的 YAML 配置文件，核心引擎代码无需任何更改。
- **⚙️ Configuration as Code:** The entire experimental process is defined in human-readable YAML files, making your performance tests versionable, repeatable, and easy to share.
  - **⚙️ 配置即代码:** 整个实验流程被定义在人类可读的 YAML 文件中，使您的性能测试可版本化、可重复且易于分享。

## 🚀 Quick Start / 快速入门

> **Note:** pipa is currently in early development. The following is a target workflow.
> **注意:** pipa 目前处于早期开发阶段。以下为目标工作流。

### 1. Prerequisites / 先决条件

- A Linux system (ARM or x86) / 一个 Linux 系统 (ARM 或 x86)
- Python 3.10+
- Core performance tools installed (`perf`, `sysstat` for `sar`) / 核心性能工具已安装 (`perf`, `sysstat` for `sar`)

### 2. Installation (Target) / 安装 (目标)

```bash
cd pipapi
pip install -r requirements.txt
```

### 3. The Three-Stage Workflow / 三阶段工作流

**Stage 1: Calibrate your environment for a specific workload.**
**第一阶段：为特定工作负载校准您的环境。**
This step probes your system to find the right benchmark intensity for "low," "medium," and "high" loads.
此步骤探测您的系统，以找到对应“低”、“中”、“高”负载的正确基准测试强度。

```bash
python pipa.py calibrate --workload mysql --output-config mysql_calibrated.yaml
```

**Stage 2: Run the automated sampling process.**
**第二阶段：运行自动化采样流程。**
This executes the full, multi-hour test run automatically based on the calibrated plan.
此步骤基于校准计划，自动执行完整的多小时测试运行。

```bash
python pipa.py sample --config mysql_calibrated.yaml --output results.pipa
```

**Stage 3: Analyze the results and generate a report.**
**第三阶段：分析结果并生成报告。**
This takes the `.pipa` data archive and produces a `report.html`.
此步骤接收 `.pipa` 数据归档文件，并产出 `report.html`。

```bash
python pipa.py analyze --input results.pipa --output report.html
```

## 📚 Deeper Dive / 深度探索

For a complete understanding of pipa's architecture, principles, and future plans, please refer to our detailed documentation:
为了全面理解 pipa 的架构、原则和未来计划，请参考我们的详细文档：

- **[DESIGN.md](./DESIGN.md):** The soul and blueprint of pipa. Understand the "why" behind its architecture.
  - **[DESIGN.md](./DESIGN.md):** pipa 的灵魂与蓝图。理解其架构背后的“为什么”。
- **[CONTRIBUTING.md](./CONTRIBUTING.md):** The laws and rules of our kingdom. Learn how to contribute, our code styles, and our Git workflow.
  - **[CONTRIBUTING.md](./CONTRIBUTING.md):** 我们王国的“法律”与“规则”。学习如何贡献、我们的代码风格和 Git 工作流。
- **[ROADMAP.md](./ROADMAP.md):** The future and ambition of pipa. See where we are heading.
  - **[ROADMAP.md](./ROADMAP.md):** pipa 的未来与雄心。了解我们的前进方向。

---

_This project is currently in a private, pre-alpha stage._
_本项目目前处于私有的 Alpha 前阶段。_
