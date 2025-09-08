# PIPA性能数据采集脚本生成指南

本文将详细介绍如何使用PIPA生成性能数据采集脚本，包括可用的模式选择、参数配置和采集时长设置方法。

## 安装

首先，确保已安装PIPA包：

```shell
pip install pypipa
```

## PIPA Generate概述

PIPA提供了灵活的性能数据采集脚本生成功能，通过`pipa generate`命令可以启动交互式配置界面，根据用户需求生成定制化的数据采集脚本。

## 数据采集模式

PIPA提供了以下几种数据采集模式：

### 1. PIPA启动工作负载模式 (run_by_pipa)

这种模式下，PIPA会生成一个集成脚本，自动启动工作负载并同时进行性能数据采集。适合于可重现的基准测试场景。

**特点：**
- 生成单个`pipa-run.sh`脚本文件
- 工作负载由PIPA直接启动和管理
- 自动收集`perf record`和`perf stat`数据
- 自动导出系统配置信息

### 2. 用户控制工作负载模式 (run_by_user)

这种模式下，PIPA生成两个脚本：一个用于数据采集，一个用于数据分析。用户需要自行控制工作负载的启动和停止。

**特点：**
- 生成`pipa-collect.sh`和`pipa-parse.sh`两个脚本
- 用户需确保在运行采集脚本时工作负载正在运行
- 支持设置采集时长
- 适合于无法由PIPA直接启动的复杂工作负载

### 3. 基于配置文件生成

用户可以先生成配置模板，编辑后再基于该配置生成脚本，适合需要重复使用相同配置的场景。

## 使用方法详解

### 基本使用流程

运行以下命令启动PIPA generate交互式界面：

```shell
pipa generate
```

系统会显示模式选择菜单：

```
? Please select the way of workload you want to run.
  Build scripts that collect global performance data.
  Build a script that collects performance data and start the workload by perf.
  Generate a configuration template configuration of PIPA-SHU.
  Build scripts based on the configuration file of PIPA-SHU.
  Generate a configuration template configuration of pipa-upload.
  Exit.
```

### 模式1：PIPA启动工作负载

选择`Build a script that collects performance data and start the workload by perf.`选项后，按照提示回答以下问题：

```sh
? Where do you want to store your data? (Default: ./) ./data
? What's the frequency of perf-record? (Default: 999) 999
? What's the event of perf-record? (Default: {cycles,instructions}:S) {cycles,instructions}:S
? Whether to use perf-annotate? No
? Do you want to use perf-stat or emon? perf-stat
? What's count deltas of perf-stat? (Default: 1000 milliseconds) 1000
? What's the event of perf-stat? cycles,instructions,branch-misses,L1-dcache-load-misses,L1-icache-load-misses
? Whether to use taskset? Yes
? Which cores do you want to use? (Default: 0-47) 0-47
? What's the command of workload? perf bench futex hash
```

完成配置后，脚本将生成在指定目录（如`./data/pipa-run.sh`）。

### 模式2：用户控制工作负载

选择`Build scripts that collect global performance data.`选项后，除了基本配置外，还可以设置采集时长：

```sh
? Where do you want to store your data? (Default: ./) ./data
? What's the frequency of perf-record? (Default: 999) 999
? What's the event of perf-record? (Default: {cycles,instructions}:S) {cycles,instructions}:S
? Whether to use perf-annotate? No
? Do you want to use perf-stat or emon? perf-stat
? What's count deltas of perf-stat? (Default: 1000 milliseconds) 1000
? What's the event of perf-stat? cycles,instructions,branch-misses,L1-dcache-load-misses,L1-icache-load-misses
? Whether to set the duration of the perf-record run?
  Yes
  No, I'll control it by myself. (Exit by Ctrl+C)
? How long do you want to run perf-record? (Default: 120s) 180
? Whether to set the duration of the perf-stat run?
  Yes
  No, I'll control it by myself. (Exit by Ctrl+C)
? How long do you want to run perf-stat? (Default: 120s) 180
```

完成配置后，将生成两个脚本：
- `./data/pipa-collect.sh`：用于启动数据采集
- `./data/pipa-parse.sh`：用于处理采集的数据

### 模式3：基于配置文件生成

1. 首先生成配置模板：
   ```shell
   pipa generate
   ```
   选择`Generate a configuration template configuration of PIPA-SHU.`选项。

2. 编辑生成的`config-pipa-shu.yaml`文件，配置所需参数。

3. 基于配置文件生成脚本：
   ```shell
   pipa generate --config_path=./config-pipa-shu.yaml
   ```

## 设置采集时长

PIPA提供了灵活的采集时长设置方式，主要在"用户控制工作负载"模式下可用：

### perf-record时长设置

在交互式配置中，当回答`Whether to set the duration of the perf-record run?`问题时选择`Yes`，然后输入所需的时长（秒）。默认时长为120秒。

```sh
? Whether to set the duration of the perf-record run? Yes
? How long do you want to run perf-record? (Default: 120s) 300
```

### perf-stat时长设置

同样，在交互式配置中，当回答`Whether to set the duration of the perf-stat run?`问题时选择`Yes`，然后输入所需的时长（秒）。默认时长为120秒。

```sh
? Whether to set the duration of the perf-stat run? Yes
? How long do you want to run perf-stat? (Default: 120s) 300
```

### 在配置文件中设置时长

如果使用配置文件方式，可以在YAML文件中添加时长配置：

```yaml
# 设置采集时长（秒）
duration_record: 300
# 设置统计时长（秒）
duration_stat: 300
```

## 运行生成的脚本

### 模式1：PIPA启动工作负载

```shell
bash ./data/pipa-run.sh > ./data/pipa-run.log
```

### 模式2：用户控制工作负载

1. 首先启动您的工作负载

2. 然后运行采集脚本：
   ```shell
bash ./data/pipa-collect.sh > ./data/pipa-collect.log
   ```

3. 当工作负载完成后，运行解析脚本：
   ```shell
bash ./data/pipa-parse.sh > ./data/pipa-parse.log
   ```

## 注意事项

1. 确保系统已安装`perf`和`sar`工具
2. 对于大型工作负载，建议增加采集时长以获得更全面的数据
3. 生成的脚本中包含了系统配置信息的导出，可能需要root权限
4. 脚本默认使用的核心列表是根据运行脚本的机器自动生成的
5. 对于用户控制工作负载模式，确保工作负载的运行时间足够长（建议超过10分钟）

## 数据输出

成功运行脚本后，您将在指定的数据目录中获得以下文件：

- `perf.data`：原始性能数据
- `perf.script`：解析后的性能数据
- `perf-stat.csv`：性能统计数据
- `sar.txt`：系统活动报告
- `config/`：系统配置信息目录

这些数据可以用于后续的性能分析和可视化。"},"result":{"status":"success","error_message":"","data":{"summary":"# PIPA性能数据采集脚本生成指南

本文将详细介绍如何使用PIPA生成性能数据采集脚本，包括可用的模式选择、参数配置和采集时长设置方法。

## 安装

首先，确保已安装PIPA包：

```shell
pip install pypipa
```

## PIPA Generate概述

PIPA提供了灵活的性能数据采集脚本生成功能，通过`pipa generate`命令可以启动交互式配置界面，根据用户需求生成定制化的数据采集脚本。

## 数据采集模式

PIPA提供了以下几种数据采集模式：

### 1. PIPA启动工作负载模式 (run_by_pipa)

这种模式下，PIPA会生成一个集成脚本，自动启动工作负载并同时进行性能数据采集。适合于可重现的基准测试场景。

**特点：**
- 生成单个`pipa-run.sh`脚本文件
- 工作负载由PIPA直接启动和管理
- 自动收集`perf record`和`perf stat`数据
- 自动导出系统配置信息

### 2. 用户控制工作负载模式 (run_by_user)

这种模式下，PIPA生成两个脚本：一个用于数据采集，一个用于数据分析。用户需要自行控制工作负载的启动和停止。

**特点：**
- 生成`pipa-collect.sh`和`pipa-parse.sh`两个脚本
- 用户需确保在运行采集脚本时工作负载正在运行
- 支持设置采集时长
- 适合于无法由PIPA直接启动的复杂工作负载

### 3. 基于配置文件生成

用户可以先生成配置模板，编辑后再基于该配置生成脚本，适合需要重复使用相同配置的场景。

## 使用方法详解

### 基本使用流程

运行以下命令启动PIPA generate交互式界面：

```shell
pipa generate
```

系统会显示模式选择菜单：

```
? Please select the way of workload you want to run.
  Build scripts that collect global performance data.
  Build a script that collects performance data and start the workload by perf.
  Generate a configuration template configuration of PIPA-SHU.
  Build scripts based on the configuration file of PIPA-SHU.
  Generate a configuration template configuration of pipa-upload.
  Exit.
```

### 模式1：PIPA启动工作负载

选择`Build a script that collects performance data and start the workload by perf.`选项后，按照提示回答以下问题：

```sh
? Where do you want to store your data? (Default: ./) ./data
? What's the frequency of perf-record? (Default: 999) 999
? What's the event of perf-record? (Default: {cycles,instructions}:S) {cycles,instructions}:S
? Whether to use perf-annotate? No
? Do you want to use perf-stat or emon? perf-stat
? What's count deltas of perf-stat? (Default: 1000 milliseconds) 1000
? What's the event of perf-stat? cycles,instructions,branch-misses,L1-dcache-load-misses,L1-icache-load-misses
? Whether to use taskset? Yes
? Which cores do you want to use? (Default: 0-47) 0-47
? What's the command of workload? perf bench futex hash
```

完成配置后，脚本将生成在指定目录（如`./data/pipa-run.sh`）。

### 模式2：用户控制工作负载

选择`Build scripts that collect global performance data.`选项后，除了基本配置外，还可以设置采集时长：

```sh
? Where do you want to store your data? (Default: ./) ./data
? What's the frequency of perf-record? (Default: 999) 999
? What's the event of perf-record? (Default: {cycles,instructions}:S) {cycles,instructions}:S
? Whether to use perf-annotate? No
? Do you want to use perf-stat or emon? perf-stat
? What's count deltas of perf-stat? (Default: 1000 milliseconds) 1000
? What's the event of perf-stat? cycles,instructions,branch-misses,L1-dcache-load-misses,L1-icache-load-misses
? Whether to set the duration of the perf-record run?
  Yes
  No, I'll control it by myself. (Exit by Ctrl+C)
? How long do you want to run perf-record? (Default: 120s) 180
? Whether to set the duration of the perf-stat run?
  Yes
  No, I'll control it by myself. (Exit by Ctrl+C)
? How long do you want to run perf-stat? (Default: 120s) 180
```

完成配置后，将生成两个脚本：
- `./data/pipa-collect.sh`：用于启动数据采集
- `./data/pipa-parse.sh`：用于处理采集的数据

### 模式3：基于配置文件生成

1. 首先生成配置模板：
   ```shell
   pipa generate
   ```
   选择`Generate a configuration template configuration of PIPA-SHU.`选项。

2. 编辑生成的`config-pipa-shu.yaml`文件，配置所需参数。

3. 基于配置文件生成脚本：
   ```shell
   pipa generate --config_path=./config-pipa-shu.yaml
   ```

## 设置采集时长

PIPA提供了灵活的采集时长设置方式，主要在"用户控制工作负载"模式下可用：

### perf-record时长设置

在交互式配置中，当回答`Whether to set the duration of the perf-record run?`问题时选择`Yes`，然后输入所需的时长（秒）。默认时长为120秒。

```sh
? Whether to set the duration of the perf-record run? Yes
? How long do you want to run perf-record? (Default: 120s) 300
```

### perf-stat时长设置

同样，在交互式配置中，当回答`Whether to set the duration of the perf-stat run?`问题时选择`Yes`，然后输入所需的时长（秒）。默认时长为120秒。

```sh
? Whether to set the duration of the perf-stat run? Yes
? How long do you want to run perf-stat? (Default: 120s) 300
```

### 在配置文件中设置时长

如果使用配置文件方式，可以在YAML文件中添加时长配置：

```yaml
# 设置采集时长（秒）
duration_record: 300
# 设置统计时长（秒）
duration_stat: 300
```

## 运行生成的脚本

### 模式1：PIPA启动工作负载

```shell
bash ./data/pipa-run.sh > ./data/pipa-run.log
```

### 模式2：用户控制工作负载

1. 首先启动您的工作负载

2. 然后运行采集脚本：
   ```shell
bash ./data/pipa-collect.sh > ./data/pipa-collect.log
   ```

3. 当工作负载完成后，运行解析脚本：
   ```shell
bash ./data/pipa-parse.sh > ./data/pipa-parse.log
   ```

## 注意事项

1. 确保系统已安装`perf`和`sar`工具
2. 对于大型工作负载，建议增加采集时长以获得更全面的数据
3. 生成的脚本中包含了系统配置信息的导出，可能需要root权限
4. 脚本默认使用的核心列表是根据运行脚本的机器自动生成的
5. 对于用户控制工作负载模式，确保工作负载的运行时间足够长（建议超过10分钟）

## 数据输出

成功运行脚本后，您将在指定的数据目录中获得以下文件：

- `perf.data`：原始性能数据
- `perf.script`：解析后的性能数据
- `perf-stat.csv`：性能统计数据
- `sar.txt`：系统活动报告
- `config/`：系统配置信息目录

这些数据可以用于后续的性能分析和可视化。