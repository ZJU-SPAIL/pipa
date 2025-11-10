# PIPA (A Pure Performance Snapshot Tool)

# PIPA (一款纯粹的性能快照工具)

**Pipa is a command-line performance snapshot tool for running systems. It attaches to existing processes and captures a comprehensive, multi-source performance snapshot (`perf`, `sar`, etc.) without disturbing the target application. Its sole purpose is to make complex performance data collection simple, reliable, and repeatable.**

**Pipa 是一款为正在运行的系统设计的、命令行的性能快照工具。它依附于现有进程，在不干扰目标应用的前提下，捕获一个全面的、多来源的性能快照（`perf`, `sar` 等）。其唯一的目标，就是让复杂的性能数据采集变得简单、可靠、可复现。**

---

## ✨ Core Philosophy / 核心哲学

- **Observer, Not an Actor:** Pipa **observes** running systems; it never starts, stops, or manages any process's lifecycle. It is a pure data collector.
  - **观察者，而非执行者:** Pipa **观察**正在运行的系统；它从不启动、停止或管理任何进程的生命周期。它是一个纯粹的数据采集器。
- **User in Control:** The user is responsible for the workload. Pipa's job is to provide a high-quality "CT scan" of the system's performance at the exact moment the user needs it.
  - **用户掌控一切:** 用户对工作负载负责。Pipa 的职责是在用户需要的确切时刻，为系统性能提供一次高质量的“CT 扫描”。
- **Simplicity by Subtraction:** We achieve simplicity not by adding features, but by ruthlessly removing everything that is not essential to the core mission of performance snapshotting.
  - **少即是多:** 我们的简洁性并非通过增加功能实现，而是通过无情地移除一切与性能快照这一核心使命无关的东西。

---

## 🚀 Quick Start / 快速入门

### 1. Prerequisites / 先决条件

- A Linux system (ARM or x86)
- Python 3.9+
- Core performance tools installed (`perf`, `sysstat` for `sar`)

### 2. Installation / 安装

```bash
# Clone the repository and install dependencies
git clone <repository_url>
cd pipa
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. Core Usage / 核心用法

_**Goal:** My application (PID 12345) is running slow. I want to take a 60-second performance snapshot to investigate._
_**目标:** 我的应用（PID 12345）运行缓慢。我想进行一次 60 秒的性能快照以供调查。_

```bash
# 1. Attach pipa to the PID and monitor for 60 seconds
#    Pipa will use a built-in, general-purpose set of collectors.
pipa sample --attach-to-pid 12345 --duration 60 --output my_snapshot.pipa

# 2. (Optional) For advanced users with custom collector needs:
#    pipa sample --attach-to-pid 12345 --duration 60 \
#    --collectors-config my_custom_collectors.yaml \
#    --output my_advanced_snapshot.pipa

# 3. Analyze the snapshot and generate the report
pipa analyze --input my_snapshot.pipa --output report.html
```

---

## 📚 Deeper Dive / 深度探索

- **[DESIGN.md](./DESIGN.md):** The soul and blueprint of pipa. / pipa 的灵魂与蓝图。
- **[CONTRIBUTING.md](./CONTRIBUTING.md):** Development guide and engineering standards. / 开发指南与工程标准。
- **[ROADMAP.md](./ROADMAP.md):** Future plans and milestones. / 未来计划与里程碑。
