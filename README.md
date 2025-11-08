# PIPA (An Adaptive Performance Experimentation Platform)

# PIPA (一个自适应性能实验平台)

**pipa is an adaptive, command-line performance experimentation platform designed for complex systems. It bridges the gap between raw metric collection and actionable insights by automating the entire performance analysis workflow, from environment calibration to final reporting.**

**pipa 是一个为复杂系统设计的自适应、命令行的性能实验平台。它通过自动化从环境校准到最终报告的完整性能分析工作流，弥合了原始指标收集与可行动洞察之间的鸿沟。**

---

## ✨ Core Features / 核心特性

- **🚀 Adaptive Calibration (`calibrate`):** Automatically discovers the optimal load parameters (e.g., threads, connections) for your specific hardware to achieve target system states (e.g., 20% CPU, 80% CPU). Say goodbye to guesswork.
  - **🚀 自适应校准 (`calibrate`):** 针对您的特定硬件，自动发现最优的负载参数（如线程数、连接数），以达到目标系统状态（如 20% CPU, 80% CPU）。告别猜测。
- **🤖 Robust Sampling Engine (`sample`):** A powerful, configuration-driven engine that orchestrates concurrent data collection (`perf stat`, etc.) with precise process lifecycle management. It supports multiple operating modes:
  - **Standard Mode:** Follows a calibrated plan.
  - **Direct Mode:** Executes with specific intensity levels, skipping calibration.
  - **Attach Mode:** Passively monitors existing processes without launching new loads.
  - **🤖 健壮的采样引擎 (`sample`):** 一个强大的、配置驱动的引擎，负责编排并发的数据采集（如 `perf stat` 等），并具备精确的进程生命周期管理。它支持多种运行模式：
    - **标准模式:** 遵循校准过的计划执行。
    - **直接模式:** 跳过校准，直接以指定的强度等级运行。
    - **依附模式:** 被动监控已存在的进程，不启动新的负载。
- **📊 Insightful Analysis (`analyze`):** Transforms raw data into a rich HTML report, featuring a rule-based decision tree for macro-bottleneck identification and **differential flame graphs** to pinpoint micro-level hotspots.
  - **📊 富有洞察的分析 (`analyze`):** 将原始数据转换为内容丰富的 HTML 报告，其特色在于：使用基于规则的决策树进行宏观瓶颈识别，并利用**差分火焰图**来精确定位微观层面的热点。
- **🔧 Universal & Extensible:** Built on a **"Load Driver"** architecture. Supporting new workloads (like Redis or PostgreSQL) requires only adding a simple YAML configuration file, with zero changes to the core engine.
  - **🔧 通用与可扩展:** 构建于 **“负载驱动程序”** 架构之上。支持新的工作负载（如 Redis 或 PostgreSQL）仅需添加一个简单的 YAML 配置文件，核心引擎代码无需任何更改。
- **⚙️ Configuration as Code:** The entire experimental process is defined in human-readable YAML files, making your performance tests versionable, repeatable, and easy to share.
  - **⚙️ 配置即代码:** 整个实验流程被定义在人类可读的 YAML 文件中，使您的性能测试可版本化、可重复且易于分享。

## 🚀 Quick Start / 快速入门

### 1. Prerequisites / 先决条件

- A Linux system (ARM or x86) / 一个 Linux 系统 (ARM 或 x86)
- Python 3.10+
- Core performance tools installed (`perf`, `sysstat` for `sar`) / 核心性能工具已安装 (`perf`, `sysstat` for `sar`)

### 2. Installation (Target) / 安装 (目标)

```bash
pip install -r requirements.txt
```

### 3. Usage Scenarios / 使用场景

#### Scenario 1: The Standard Three-Stage Workflow (标准三阶段工作流)

_Best for new workloads where optimal settings are unknown._
_适用于未知工作负载，自动发现最佳配置。_

```bash
# 1. Calibrate to find optimal parameters
pipa calibrate --workload mysql --output-config mysql_calibrated.yaml

# 2. Run automated sampling based on the calibrated plan
pipa sample --config mysql_calibrated.yaml --output results.pipa

# 3. Analyze the results and generate the final report
pipa analyze --input results.pipa --output report.html
```

#### Scenario 2: Direct Sampling Mode (直接采样模式)

_Best when you already know the exact load intensity you want to test._
_适用于已知确切压测强度的情况，跳过校准步骤。_

```bash
# Sample 'stress_cpu' workload at 8 and 16 threads directly
python pipa.py sample --workload stress_cpu --intensity 8,16 --output direct_run.pipa
```

#### Scenario 3: Passive Attach Mode (被动依附模式)

_Best for monitoring existing, running production services._
_适用于监控已经在运行的生产服务。_

```bash
# Find the PIDs of your target service
PID_LIST=$(pgrep mysqld | tr '\n' ',' | sed 's/,$//')

# Attach pipa to these PIDs and monitor for 60 seconds
python pipa.py sample --workload mysql --attach-to-pid "$PID_LIST" --duration 60 --output attach_run.pipa
```

## 📚 Deeper Dive / 深度探索

For a complete understanding of pipa's architecture, principles, and future plans, please refer to our detailed documentation:
为了全面理解 pipa 的架构、原则和未来计划，请参考我们的详细文档：

- **[DESIGN.md](./DESIGN.md):** The soul and blueprint of pipa. / pipa 的灵魂与蓝图。
- **[CONTRIBUTING.md](./CONTRIBUTING.md):** Development guide and engineering standards. / 开发指南与工程标准。
- **[ROADMAP.md](./ROADMAP.md):** Future plans and milestones. / 未来计划与里程碑。

---

_This project is currently in early development._
_本项目目前处于早期开发阶段。_

````

---

### **Commit Message 建议**

```text
docs(readme): 更新 README 以反映最新的 sample 功能和多种运行模式

- 更新核心特性列表，强调新的健壮采样引擎及其支持的三种模式（标准、直接、依附）。
- 重构“快速入门”部分，增加了“直接采样模式”和“被动依附模式”的具体使用场景和示例命令。
- 清晰地展示了 pipa 作为通用性能分析平台的灵活性。
````
