### **1. 核心哲学：性能分析的“CT 扫描仪”** <a name="1-核心哲学"></a>

`pipa` 的设计理念是成为一个**纯粹的观察者**。它不对你的系统或应用做任何修改、启停或管理。

它的唯一职责，是在你指定的时刻，为你的系统或进程进行一次**全面、深度、标准化的“CT 扫描”**，并将扫描结果（即性能数据）打包成一份可移植、可分析的快照。

后续的 `analyze` 和 `flamegraph` 命令，则是这份“CT 影像”的**智能阅片和诊断系统**。v0.4.0 版本引入了 **物理感知引擎 (Physics-Aware Engine)**，能够穿透平均值的迷雾，直击 128 核服务器和 NVMe SSD 的微观瓶颈。

---

### **2. 安装与环境准备** <a name="2-安装与环境准备"></a>

#### **2.1 系统依赖**

在安装 `pipa` 之前，请确保你的 Linux 系统已安装以下核心工具：

- **`perf`**: Linux 内核性能分析工具 (通常在 `linux-tools-common` 或 `perf` 包中)。
- **`sysstat`**: 提供 `sar` 命令 (通常在 `sysstat` 包中)。
- **`python`**: Python 3.9 或更高版本。

```bash
# 在基于 YUM/DNF 的系统 (如 openEuler, CentOS)
sudo yum install -y sysstat perf python3-devel python3-virtualenv
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

在目标机器上，首先运行 `healthcheck`。这会收集系统的静态信息，让后续的采样更精确。

```bash
pipa healthcheck
# ✅ Static information successfully saved to: pipa_static_info.yaml
```

#### **第 2 步: 执行性能快照 (`sample`)**

这是核心的数据采集步骤。我们附着到目标进程 `25188`，进行一次为期 120 秒的快照。

```bash
pipa sample --attach-to-pid 25188 --duration-stat 60 --duration-record 60 --output my_app_snapshot.pipa
# ✅ Sampling complete (120s). Snapshot saved to: my_app_snapshot.pipa
```

#### **第 3 步: 智能分析与生成报告 (`analyze`)**

将上一步生成的 `.pipa` 快照文件交给 `analyze` 命令。
_(v0.4.0 新特性：你可以传入 `--expected-cpus` 来验证绑核策略)_

```bash
pipa analyze --input my_app_snapshot.pipa --output report.html --expected-cpus "0-7"
# ✅ Analysis complete. Report saved to: report.html
```

#### **第 4 步: 查看报告与深度剖析**

打开 `report.html`：

1.  查看 **Configuration Audit**：确认绑核是否生效。
2.  查看 **Diagnostic Findings**：PIPA 会自动告诉你是否存在“I/O 吞吐饱和”、“TMA 前端瓶颈”等问题。
3.  点击 **Top CPU Hotspots**：查看具体是哪个函数在消耗 CPU。

---

### **4. 命令参考大全** <a name="4-命令参考大全"></a>

#### **4.1 `pipa healthcheck`** <a name="41-pipa-healthcheck"></a>

**用途**: 收集目标系统一次性的静态信息（CPU 型号、核心数、内存、磁盘、OS 版本等）。

```bash
pipa healthcheck [--output <file_path>]
```

---

#### **4.2 `pipa sample`** <a name="42-pipa-sample"></a>

**用途**: 执行性能快照的核心命令。支持双阶段采集：

1.  **Macro-Scan**: `perf stat` + `sar` (宏观指标)。
2.  **Micro-Profiling**: `perf record` (微观热点)。

**核心选项:**

- `--attach-to-pid <pid>`: **进程模式**。附着到一个或多个 PID。
- `--system-wide`: **系统模式**。采集全系统数据。
- `--duration-stat <sec>`: 宏观扫描时长 (默认 60s)。
- `--duration-record <sec>`: 微观剖析时长 (默认 60s)。
- `--no-record`: 仅采集指标，不采集热点 (文件更小，但无法看 Hotspots Tab)。

---

#### **4.3 `pipa analyze`** <a name="43-pipa-analyze"></a>

**用途**: 解析 `.pipa` 快照文件，生成 HTML 报告。v0.4.0 增强了审计和离线分析能力。

```bash
pipa analyze --input <snapshot.pipa> [OPTIONS]
```

**核心选项:**

- `--input <path>`: **(必需)** 输入的 `.pipa` 文件。
- `--output <path>`: 输出 HTML 路径。

**[v0.4.0 新增] 审计与调试选项:**

- `--expected-cpus <list>`: **配置合规性审计**。
  - 输入预期繁忙的 CPU 列表 (如 `"0-7,16"` )。
  - 报告将自动检测是否存在 **干扰 (Leakage)** 或 **资源闲置 (Absent)**。
- `--symfs <dir>`: **离线符号解析**。
  - 如果采样环境（生产环境）没有安装 `debuginfo`，你可以在分析环境（开发机）准备好带符号的二进制文件结构，通过此参数指定根目录，PIPA 将自动还原函数名。
- `--kallsyms <file>`: 指定内核符号表路径（用于离线解析内核函数）。

---

#### **4.4 `pipa flamegraph`** <a name="44-pipa-flamegraph"></a>

**用途**: 从包含 `perf.data` 的 `.pipa` 快照中生成火焰图。

```bash
pipa flamegraph --input <snapshot.pipa> --output <flame.svg>
```

- `--input`: **(必需)** 包含 `perf.data` 的 `.pipa` 文件 (即 `sample` 时未加 `--no-record`)。
- `--output`: **(必需)** 输出的 SVG 火焰图文件。

---

### **5. 解读分析报告** <a name="5-解读分析报告"></a>

`pipa analyze` 生成的 HTML 报告包含以下核心模块：

#### **5.1 交互式筛选器：从数据中掘金**

所有时序图表（Metrics Explorer）均支持正则表达式筛选。

- **多选**: `eth0,docker0`
- **范围**: `0-7` (CPU 核心)
- **精确匹配**: `^tps` (只匹配 tps，不匹配 rtps)

#### **5.2 磁盘拓扑与容量分析**

左侧旭日图展示物理磁盘结构，右侧展示分区详情。

- **红色高亮**: 表示分区使用率超过 90%，需关注容量风险。

#### **5.3 配置合规性审计 (Configuration Audit)** <a name="53-配置合规性审计-new"></a>

_(v0.4.0 新增，仅在指定 `--expected-cpus` 时显示)_

这是报告的第一道关卡，用于验证部署策略是否生效。

- **Pass (通过)**: 实际繁忙的核心与预期完全一致。
- **Leakage (干扰)**: 发现了非预期的核心处于高负载状态（可能是中断漂移或未绑核进程干扰）。
- **Absent (闲置)**: 预留的核心未被充分利用。

#### **5.4 代码级热点分析 (Top CPU Hotspots)** <a name="54-代码级热点分析-new"></a>

_(v0.4.0 新增)_

展示消耗 CPU 最多的函数列表。包含进度条可视化。

- **符号解析说明**:
  - 如果看到 **函数名** (如 `deflate`, `do_sys_open`)，说明解析成功。
  - 如果看到 **十六进制** (如 `0x4011...`) 或 `[unknown]`，说明**当前分析机器**缺少对应的 `debuginfo` 包。
- **Java JIT 支持**:
  - 对于 Elasticsearch 等 Java 应用，PIPA 支持透视 JIT 编译后的符号 (如 `org.apache.lucene...`)。
  - 报告提供了一个 **"Show Raw JIT Symbols"** 开关，可切换“聚合视图”（清爽）和“底层视图”（显示 TID 和内存地址）。

**I/O 诊断逻辑更新 (v0.4.0):**
PIPA 现在采用 **“吞吐拥塞”** 与 **“延迟拖累”** 双轨判定：

- **吞吐量饱和**: 即使 SSD 响应很快 (3ms)，如果队列积压严重 (Queue > 80)，依然会被判定为瓶颈。
- **延迟瓶颈**: 针对 HDD，如果响应慢 (>20ms) 且导致单核 CPU 等待，则判定为介质瓶颈。

---

### **6. 高级用法与最佳实践** <a name="6-高级用法与最佳实践"></a>

- **生产环境最小化采集**:
  - 在生产环境运行 `pipa sample --no-record`，仅采集指标，对系统干扰极小。
  - 需要深挖时，再开启完整采集。
- **离线分析工作流**:
  - 在生产环境采集 (`sample`) -> 将 `.pipa` 包下载到本地开发机 -> 在本地安装 `debuginfo` -> 运行 `analyze --symfs ...`。既安全又精准。
- **性能调优闭环**: 使用 `pipa` 形成 `采样 -> 分析 -> 优化 -> 再采样 -> 对比` 的性能调优闭环，让每一次优化的效果都能量化、可见。

---

### **7. 常见问题 (FAQ) 与故障排查** <a name="7-常见问题-faq-与故障排查"></a>

- **Q: Hotspots Tab 显示 "No Profiling Data Available"。**

  - **A**: 可能是 `sample` 时使用了 `--no-record`，或者**当前分析机器**未安装 `perf` 工具。

- **Q: 为什么 Java 函数名看起来很长？**

  - **A**: 这是 JIT 编译的特性。PIPA 忠实反映了 JVM 在内存中生成的符号名。你可以关闭报告中的 "Show Raw JIT Symbols" 开关来获得更清爽的视图。

- **Q: `pipa sample` 提示 `Perf permission denied`。**
  - **A**: `echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid`。
