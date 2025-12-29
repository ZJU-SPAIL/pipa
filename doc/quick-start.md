# Quick Start

本文聚焦 `pipa-tree` 采集器，帮助你在几分钟内完成性能数据抓取。典型流程：**安装 pipa-tree → 执行 `collect` → 获得标准压缩包 → （可选）交给 `pipa analyze` 生成报告**。

## 1. 环境准备

### 1.1 获取源码

```bash
git clone https://github.com/ZJU-SPAIL/pipa.git
cd pipa
```

### 1.2 安装 `pipa-tree`

官方安装脚本位于 `script/pipa-tree/install.sh`，等价于 [INSTALL.md](../script/pipa-tree/INSTALL.md) 中的步骤：

```bash
cd script/pipa-tree
sudo ./install.sh              # 安装到 /usr/local/bin
sudo ./install.sh --all-users  # 可选：为所有用户配置 perf sudo 权限
```

| 组件       | 安装路径                                       | 说明                           |
| ---------- | ---------------------------------------------- | ------------------------------ |
| 可执行文件 | `/usr/local/bin/pipa-tree`                     | 主入口脚本                     |
| 依赖库     | `/usr/local/lib/pipa-tree`                     | `common.sh/perf.sh/sar.sh/...` |
| sudo 配置  | `/etc/sudoers.d/pipa-tree`（仅 `--all-users`） | 限定 perf 权限                 |

> **开发/临时模式**：不想全局安装时，可直接在 `script/pipa-tree` 目录执行 `./pipa-tree collect ...`，脚本会自动引用本地 `./lib`。

## 2. 使用 `pipa-tree collect`

### 2.1 命令结构

- `pipa-tree collect [options]` 是唯一且默认的子命令；输入仅包含参数（如 `pipa-tree --duration-stat 120`）时会自动执行 `collect`。
- 采集包含两个阶段：
  1. **Counting**：`perf stat -I` + `sar`，快速获取整体指标。
  2. **Profiling**：`perf record -g`，可获取函数级详细信息。

### 2.2 常用参数速查

| 参数                        | 说明                            | 默认值                                 |
| --------------------------- | ------------------------------- | -------------------------------------- |
| `--output PATH`             | 结果压缩包（`.tar.gz`）输出位置 | `./pipa-collection-<timestamp>.tar.gz` |
| `--duration-stat SEC`       | Counting 阶段时长               | 60 秒                                  |
| `--duration-record SEC`     | Profiling 阶段时长              | 60 秒                                  |
| `--no-stat` / `--no-record` | 关闭对应阶段                    | 均开启                                 |
| `--perf-stat-interval MS`   | `perf stat -I` 间隔             | 1000 ms                                |
| `--sar-interval SEC`        | `sar` 采样间隔                  | 1 秒                                   |
| `--perf-record-freq HZ`     | `perf record -F` 频率           | 97 Hz                                  |
| `--perf-events LIST`        | 覆盖默认事件组（逗号分隔）      | 随架构自动选择                         |
| `--no-spec-info`            | 跳过硬件规格导出                | 否                                     |
| `--spec-info-file PATH`     | 使用自定义规格文件              | 无                                     |

### 2.3 快速操作流程

1. **确认依赖**：
   ```bash
   which pipa-tree perf sar sadf
   ```
2. **执行采集**：
   ```bash
   sudo pipa-tree collect
   # stdout 示例如下（未指定 --output 时会给出默认路径）
   # [INFO] No --output specified. Using default path: /home/xyjiang/project/pipa/pipa-collection-20251229_124228.tar.gz
   # [INFO] Working directory: /tmp/pipa_sample_Zdhy
   # [INFO] Starting counting phase (perf stat + sar) for 60s
   ```
3. **等待完成**：命令结束会提示 `Archive created at ...`。
4. **查看结果**：压缩包包含 `spec_info.yaml` 与 `attach_session/`，后者持有：
   - `pipa-tree.log` / `pipa-collection-info.txt` / `collection_id.txt`
   - `perf_stat.txt`、`perf.data`
   - `sar_all.bin`、`sar.log`、`sar_cpu.csv`、`sar_io.csv` 等 CSV

### 2.4 典型调用示例

```bash
sudo pipa-tree --duration-stat 90 --duration-record 30 \
  --perf-record-freq 199 \
  --perf-events "cycles,instructions" \
  --output ./pipa-collection-demo.tar.gz
```

- Counting 90 秒、Profiling 30 秒。
- 仅关注 `cycles`/`instructions` 事件，便于定位 IPC 问题。
- 输出 `pipa-collection-demo.tar.gz`，可直接交给分析工具。

### 2.5 常见使用场景

- **紧急现场排障**：无需额外参数，默认配置即可输出 perf/sar 基线。
- **持续压测或回归**：借助 `cron`/CI 定期运行 `pipa-tree collect --output /data/<tag>.tar.gz`，统一归档。
- **硬件对比/容量规划**：在不同服务器使用相同参数采集，通过 `collection_id.txt` 和 `pipa-collection-info.txt` 核对机器信息，再用 `pipa analyze --expected-cpus ...` 对齐拓扑。

## 3. 下一步（可选）

### 3.1 使用 `pipa analyze` 生成报告

采集完成后，可在同一仓库中调用：

```bash
make # 编译安装 pipa cli
pipa analyze ./pipa-collection-demo.tar.gz \
  --expected-cpus 0-7 \
  --symfs /path/to/symbols \
  --kallsyms /proc/kallsyms
```

该命令会在当前目录输出 `report.html`，包含 CPU 聚类、NUMA 负载、磁盘容量告警、热点符号等可视化信息：

- `--expected-cpus`：可选，告诉决策树“业务核心”范围，便于亲和性与利用率对齐。
- `--symfs`/`--kallsyms`：可选，若提供符号目录与 `kallsyms`，可让 `perf.data` 热点解析出精准函数名。
- 所有图表/规则模板均位于 `src/templates/`，可按需自定义主题。

### 3.2 通过自动化测试验证分析能力

仓库内提供了覆盖 CLI、规则引擎与解析能力的测试集，可在采集主机上直接运行：

```bash
pytest test/test_command_analyze.py::test_analyze_archive_end_to_end
pytest test/test_command_rules.py
pytest test/test_pipa_parsers.py
```

- 端到端用例会构造一个最小化的 `pipa-tree` 压缩包，真实调用 `pipa analyze` 并生成 HTML，以确保报告链路可用。
- 决策树与 `perf stat` 解析用例保证规则逻辑、TMA 指标与 CSV 解析在升级后依旧工作，便于回归验证。
