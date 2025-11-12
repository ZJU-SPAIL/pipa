# **PIPA 权威使用手册 (v1.0)**

## **目录**

1.  [**核心哲学：性能分析的“CT 扫描仪”**](#1-核心哲学)
2.  [**安装与环境准备**](#2-安装与环境准备)
3.  [**黄金工作流：十分钟定位性能问题**](#3-黄金工作流)
4.  [**命令参考大全**](#4-命令参考大全)
    - [4.1 `pipa healthcheck`](#41-pipa-healthcheck)
    - [4.2 `pipa sample`](#42-pipa-sample)
    - [4.3 `pipa analyze`](#43-pipa-analyze)
    - [4.4 `pipa compare`](#44-pipa-compare)
    - [4.5 `pipa flamegraph`](#45-pipa-flamegraph)
5.  [**解读分析报告**](#5-解读分析报告)
6.  [**高级用法与最佳实践**](#6-高级用法与最佳实践)
7.  [**常见问题 (FAQ) 与故障排查**](#7-常见问题-faq-与故障排查)

---

### **1. 核心哲学：性能分析的“CT 扫描仪”** <a name="1-核心哲学"></a>

`pipa` 的设计理念是成为一个**纯粹的观察者**。它不对你的系统或应用做任何修改、启停或管理。

它的唯一职责，是在你指定的时刻，为你的系统或进程进行一次**全面、深度、标准化的“CT 扫描”**，并将扫描结果（即性能数据）打包成一份可移植、可分析的快照。

后续的 `analyze`, `compare` 等命令，则是这份“CT 影像”的**智能阅片和诊断系统**。

---

### **2. 安装与环境准备** <a name="2-安装与环境准备"></a>

#### **2.1 系统依赖**

在安装 `pipa` 之前，请确保你的 Linux 系统已安装以下核心工具：

- **`perf`**: Linux 内核性能分析工具 (通常在 `linux-tools-common` 包中)。
- **`sysstat`**: 提供 `sar` 命令 (通常在 `sysstat` 包中)。
- **`python`**: Python 3.9 或更高版本。

```bash
# 在基于 YUM/DNF 的系统 (如 openEuler, CentOS)
sudo yum install -y sysstat perf python3.9

# 在基于 APT 的系统 (如 Ubuntu, Debian)
sudo apt-get update
sudo apt-get install -y sysstat linux-tools-common python3.9
```

#### **2.2 安装 PIPA**

我们提供了一个自动化的 `setup.sh` 脚本来处理所有环境配置。

```bash
# 1. 克隆仓库
cd pipa

# 2. 运行安装脚本
# 这个脚本会自动检测 Python 环境，创建虚拟环境，并安装所有依赖。
./setup.sh

# 3. 激活环境
# 每次使用 pipa 前，都需要激活此环境
source .venv/bin/activate
```

---

### **3. 黄金工作流：十分钟定位性能问题** <a name="3-黄金工作流"></a>

这是使用 `pipa` 定位性能问题的最常用、最高效的路径。

#### **场景**: 你的应用（进程 PID 为 `25188`）在运行时出现性能下降，你想找出原因。

#### **第 1 步: 系统健康检查 (可选但推荐)**

在目标机器上，首先运行 `healthcheck`。这会收集系统的静态信息，让后续的采样更精确。此步骤只需在环境不变的情况下执行一次。

```bash
pipa healthcheck
# ✅ Static information successfully saved to: pipa_static_info.yaml
```

#### **第 2 步: 执行性能快照 (`sample`)**

这是核心的数据采集步骤。我们附着到目标进程 `25188`，进行一次为期 120 秒的快照。

- **Phase 1 (宏观扫描)**: 前 60 秒，`pipa` 会采集 `perf stat` 和 `sar` 数据，用于系统级和微架构层面的分析。
- **Phase 2 (微观剖析)**: 后 60 秒，`pipa` 会采集 `perf record` 数据，用于生成火焰图。

```bash
pipa sample --attach-to-pid 25188 --duration-stat 60 --duration-record 60 --output my_app_snapshot.pipa
# ✅ Sampling complete (120s). Snapshot saved to: my_app_snapshot.pipa
```

#### **第 3 步: 智能分析与生成报告 (`analyze`)**

将上一步生成的 `.pipa` 快照文件交给 `analyze` 命令.

```bash
pipa analyze --input my_app_snapshot.pipa --output report.html
# ✅ Analysis complete. Report saved to: report.html
```

现在，在浏览器中打开 `report.html`。你将看到一份包含**自动诊断结论、交互式图表、原始数据**的完整报告。

#### **第 4 步: (如果需要) 深度代码剖析 (`flamegraph`)**

如果在报告中发现瓶颈是 **ON-CPU**，你可以使用 `flamegraph` 命令进一步定位到具体的函数热点。

```bash
pipa flamegraph --input my_app_snapshot.pipa --output flame.svg
# ✅ Flame Graph successfully saved to: flame.svg
```

在浏览器中打开 `flame.svg`，查看火焰图。

---

### **4. 命令参考大全** <a name="4-命令参考大全"></a>

#### **4.1 `pipa healthcheck`** <a name="41-pipa-healthcheck"></a>

**用途**: 收集目标系统一次性的静态信息（CPU 型号、核心数、内存、磁盘、OS 版本等）。

**为什么需要**: `sample` 命令会利用这些信息进行更精确的分析（例如，基于核心数计算负载率）。预先收集可以避免每次采样都重复执行，并确保数据的一致性。

```bash
pipa healthcheck [--output <file_path>]
```

- `--output`: (可选) 指定输出的 YAML 文件路径。默认为 `pipa_static_info.yaml`。

---

#### **4.2 `pipa sample`** <a name="42-pipa-sample"></a>

**用途**: 执行性能快照的核心命令。

**核心选项 (必须选择其一):**

- `--attach-to-pid <pid>`: **进程模式**。附着到一个或多个（用逗号分隔）已在运行的进程 ID。
- `--system-wide`: **系统模式**。采集整个系统的性能数据，不针对特定进程。

**阶段与时长选项:**

- `--duration-stat <sec>`: Phase 1 (宏观扫描) 的持续时间（秒）。默认 `60`。
- `--duration-record <sec>`: Phase 2 (微观剖析) 的持续时间（秒）。默认 `60`。
- `--no-stat`: 完全跳过 Phase 1。
- `--no-record`: 完全跳过 Phase 2 (不会生成 `perf.data`，无法制作火焰图)。

**专家调优选项:**

- `--perf-stat-interval <ms>`: `perf stat` 的采样间隔（毫秒）。
- `--sar-interval <sec>`: `sar` 的采样间隔（秒）。
- `--perf-record-freq <hz>`: `perf record` 的采样频率（赫兹）。
- `--perf-events <events>`: **(高级)** 覆盖内置的 `perf stat` 事件集。事件用逗号分隔，如 `"cycles,instructions"`。

**静态信息选项:**

- `--static-info-file <path>`: 指定一个由 `healthcheck` 生成的静态信息文件。
- `--no-static-info`: 强制不使用任何静态信息文件。

**输出选项:**

- `--output <file_path>`: **(必需)** 指定输出的 `.pipa` 快照文件路径。

**示例:**

```bash
# 示例1: 对 PID 12345 进行一个快速的 15 秒宏观扫描
pipa sample --attach-to-pid 12345 --duration-stat 15 --no-record --output quick_scan.pipa

# 示例2: 对整个系统进行一次完整的、各 60 秒的双阶段快照
pipa sample --system-wide --duration-stat 60 --duration-record 60 --output system_snapshot.pipa
```

---

#### **4.3 `pipa analyze`** <a name="43-pipa-analyze"></a>

**用途**: 解析 `.pipa` 快照文件，生成一份人类可读的 HTML 报告。

```bash
pipa analyze --input <snapshot.pipa> [--output <report.html>]
```

- `--input`: **(必需)** 输入的 `.pipa` 文件。
- `--output`: (可选) 输出的 HTML 报告路径。默认为 `report.html`。

---

#### **4.4 `pipa compare`** <a name="44-pipa-compare"></a>

**用途**: 对比两个 `.pipa` 快照，量化性能差异，常用于 A/B 测试或版本回归测试。

```bash
pipa compare --input-a <baseline.pipa> --input-b <target.pipa> [--output <compare_report.html>]
```

- `--input-a`: **(必需)** 作为基线的快照文件。
- `--input-b`: **(必需)** 作为对比目标的快照文件。
- `--output`: (可选) 输出的 HTML 对比报告。如果提供，会生成包含覆盖图表的网页报告。

---

#### **4.5 `pipa flamegraph`** <a name="45-pipa-flamegraph"></a>

**用途**: 从包含 `perf.data` 的 `.pipa` 快照中生成火焰图。

```bash
pipa flamegraph --input <snapshot.pipa> --output <flame.svg>
```

- `--input`: **(必需)** 包含 `perf.data` 的 `.pipa` 文件 (即 `sample` 时未加 `--no-record`)。
- `--output`: **(必需)** 输出的 SVG 火焰图文件。

---

### **5. 解读分析报告** <a name="5-解读分析报告"></a>

`pipa analyze` 生成的 HTML 报告是 `pipa` 的核心产出物，包含以下几个标签页：

- **Analysis & Insights**:

  - **决策树**: 直观展示了 `pipa` 内置专家系统的诊断路径。高亮的路径即为本次快照的诊断结论。
  - **诊断结论**: 基于决策树的最终文字总结，明确指出系统瓶颈类型和可能的根因。**这是你首先要看的部分**。

- **Metrics Explorer**:

  - **交互式图表**: 所有 `sar` 和 `perf stat` 的时序数据都在这里。
  - **文本筛选器**: 每个图表上方都有筛选框，你可以输入 CPU 核心号 (`0-3,5`)、网络接口名 (`eth0`) 或指标名 (`%user, %system`) 来过滤和聚焦。
  - **图例交互**: 点击图表下方的图例项，可以临时显示/隐藏对应的曲线。

- **Raw Data Tables**:

  - 所有解析后的数据以可搜索、可排序的表格形式呈现，方便进行精细的数据审查。

- **System Information**:
  - `healthcheck` 收集的所有静态信息，提供了分析时的必要上下文。

### **5.1 交互式筛选器：从数据中掘金**

`pipa` 报告的核心价值，在于其强大的交互式筛选能力。它允许你从上百条数据线中，精确地分离和聚焦你感兴趣的部分，从而发现隐藏在“平均值”之下的性能瓶颈。

以下是筛选器的使用语法和最佳实践：

#### **1. 基础筛选 (多选)**

- **语法**: 使用逗号 `,` 分隔多个选项。筛选器会显示**包含任何一个**选项的曲线 (OR 逻辑)。
- **示例**:
  - 在 `IFACE` 筛选框中输入 `eth0,docker0`，将只显示 `eth0` 和 `docker0` 两个网络接口的数据。
  - 在 `METRIC` 筛选框中输入 `%user,%system`，将只显示 CPU 的用户态和内核态利用率。

#### **2. 范围筛选 (数值型)**

- **语法**: 对于数值型维度（如 `CPU`），可以使用连字符 `-` 来指定一个连续的范围。可以与多选逗号结合使用。
- **示例**:
  - 在 `CPU` 筛选框中输入 `0-7`，将显示 CPU 核心 0 到 7 的所有数据。
  - 输入 `0-3,64-67`，将显示 NUMA 节点 0 和 NUMA 节点 2 的前 4 个核心，非常适合进行跨 NUMA 节点的性能对比。

#### **3. 高级筛选 (精确匹配)**

- **语法**: 在选项前加上 `^` 符号，可以强制进行**从头开始的精确匹配**。这对于区分 `tps` 和 `rtps` 这类包含关系的指标至关重要。
- **示例**:
  - 在 `Sar Io` 的 `METRIC` 框中输入 `tps`，会同时显示 `tps` 和 `rtps` 的曲线。
  - 输入 `^tps`，将**只显示 `tps`** 的曲线，`rtps` 会被过滤掉。

#### **4. 组合筛选 (终极用法)**

- 所有语法都可以自由组合，以实现外科手术式的精确数据钻取。
- **示例**:
  - 在 `Sar Io` 的 `METRIC` 框中输入 `^tps,rtps`，可以精确地同时显示 `tps` 和 `rtps` 两条曲线，而不会匹配到其他指标。
  - 在 `Sar CPU` 的 `CPU` 框中输入 `0-3,127`，同时在 `METRIC` 框中输入 `%user`，可以精确地对比核心 `0-3` 与核心 `127` 的用户态 CPU 利用率。

---

---

### **6. 高级用法与最佳实践** <a name="6-高级用法与最佳实践"></a>

- **自动化与 CI/CD**: 你可以将 `pipa` 命令集成到自动化测试脚本中。例如，在每次发布后，自动对新版本进行一次 `sample`，然后用 `compare` 与上一版本的基线快照进行对比，如果关键指标（如 IPC）下降超过阈值，则自动告警。
- **`.pipa` 归档文件**: `.pipa` 文件本质上是一个 `.tar.gz` 压缩包。你可以用 `tar -xvf my_snapshot.pipa` 解压它来查看内部的原始数据文件（如 `perf_stat.txt`, `sar_cpu.csv` 等）。
- **性能调优闭环**: 使用 `pipa` 形成 `采样 -> 分析 -> 优化 -> 再采样 -> 对比` 的性能调优闭环，让每一次优化的效果都能量化、可见。

---

### **7. 常见问题 (FAQ) 与故障排查** <a name="7-常见问题-faq-与故障排查"></a>

- **Q: `pipa sample` 失败，提示 `Perf permission denied` 或 `perf_event_paranoid` 错误。**

  - **A**: 这是因为系统内核的安全设置限制了 `perf` 的使用。你需要更高的权限。
    - **临时解决方案**: `echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid`
    - **永久解决方案**: 在 `/etc/sysctl.conf` 中添加 `kernel.perf_event_paranoid = -1`，然后执行 `sudo sysctl -p`。

- **Q: 运行 `pipa` 命令提示 `command not found`。**

  - **A**: 你很可能忘记激活 `pipa` 的 Python 虚拟环境。请执行 `source .venv/bin/activate`。

- **Q: `pipa flamegraph` 失败，提示 `perf.data not found`。**

  - **A**: 这意味着你用于 `sample` 的快照是在 `--no-record` 模式下采集的，它不包含生成火焰图所需的 `perf.data` 文件。请重新进行一次完整的双阶段采样。

- **Q: `pipa sample` 启动时就失败，提示 `Process with PID ... does not exist`。**
  - **A**: 你提供的 PID 在 `pipa` 启动检查时已经不存在了。请确认你的目标应用正在运行，并且 PID 是正确的。
