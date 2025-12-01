# PIPA (Performance Insight & Profiling Agent)

**v0.4.0 - Physics-Aware Edition / 物理感知版**

**Pipa is a non-intrusive, physics-aware performance diagnostic tool for modern Linux systems. It captures comprehensive snapshots (`perf`, `sar`) and uses an expert system to diagnose bottlenecks from the hardware layer up to the code level.**

**Pipa 是一款针对现代 Linux 系统的非侵入式、物理感知型性能诊断工具。它捕获全面的性能快照（`perf`, `sar`），并利用内置专家系统，从硬件层到代码层进行全栈瓶颈诊断。**

---

## ✨ Key Features / 核心特性

### 1. 🧠 Physics-Aware Diagnostics (物理感知诊断)

Unlike traditional tools that rely on global averages, Pipa understands the physical reality of hardware:
与依赖全局平均值的传统工具不同，Pipa 理解硬件的物理现实：

- **Storage:** Distinguishes between **Throughput Saturation** (SSD queue buildup) and **Latency Bottlenecks** (HDD seek time). / 区分吞吐量饱和（SSD 队列积压）与延迟瓶颈（HDD 寻道时间）。
- **CPU:** Detects single-core saturation even on 128-core systems using **P95 statistical features**, avoiding "average load" blindness. / 利用 P95 统计特征检测 128 核系统上的单核饱和，避免“平均负载”盲区。

### 2. 🔥 Code-Level Profiling (代码级热点)

- **Automated Extraction:** Automatically parses `perf` data to identify top CPU-consuming functions. / 自动解析 `perf` 数据以识别 CPU 消耗最高的函数。
- **JIT Support:** Full visibility into Java/JVM JIT compiled symbols (e.g., Elasticsearch, Spark). / 完全透视 Java/JVM JIT 编译符号。
- **Offline Analysis:** Supports `--symfs` for analyzing production snapshots on a developer machine with debug symbols. / 支持 `--symfs`，可在带有调试符号的开发机上分析生产环境快照。

### 3. 🛡️ Configuration Audit (配置合规审计)

- **Pre-flight Check:** Validates if your deployment strategy (e.g., CPU pinning/affinity) is actually effective using `--expected-cpus`. / 使用 `--expected-cpus` 验证部署策略（如 CPU 绑核）是否实际生效。
- **Leakage Detection:** Identifies noisy neighbors or IRQ misrouting. / 识别嘈杂邻居或中断错误路由。

---

## 🚀 Quick Start / 快速入门

### 1. Installation / 安装

```bash
./setup.sh
source .venv/bin/activate
```

### 2. Golden Workflow / 黄金工作流

**Scenario:** Diagnose a slow MySQL instance (PID 12345). / **场景:** 诊断缓慢的 MySQL 实例 (PID 12345)。

```bash
# Step 1: Collect static system info (Once per machine)
pipa healthcheck

# Step 2: Take a snapshot (60s macro-scan + 60s micro-profiling)
pipa sample --attach-to-pid 12345 --output mysql.pipa

# Step 3: Analyze and generate report (with config audit)
# "Verify if MySQL is correctly pinned to cores 0-7"
pipa analyze --input mysql.pipa --output report.html --expected-cpus "0-7"
```

---

## 📚 Documentation / 文档索引

- **[Manual.md](./Manual.md):** The definitive user guide and command reference. / 权威使用手册与命令参考。
- **[DESIGN.md](./DESIGN.md):** Architecture and design philosophy. / 架构与设计哲学。
