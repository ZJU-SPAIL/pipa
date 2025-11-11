# PIPA Showcase 迁移指南：从 0 到 1 构建你自己的性能分析场景

## 迁移四步曲

整个迁移过程，可以被清晰地分解为以下四个步骤。

### 第一步：环境与控制脚本 (`env.sh`, `start_*.sh`, `stop_*.sh`)

这是所有工作的基础。你需要创建一套脚本，来**标准化地控制**你的应用进程的生命周期。

1.  **`env.sh` (环境变量)**:

    - **目的**: 集中管理所有可变的环境配置。
    - **操作**: 创建 `env.sh`，定义你的应用所需的所有环境变量（如 `NGINX_CONF_PATH`, `ES_JAVA_OPTS` 等）。这使得其他人可以轻松地在不同环境中复现你的场景。
    - **参考**: `showcases/mysql/env.sh`

2.  **`start_YOUR_APP.sh` (启动脚本)**:

    - **目的**: 以**后台模式**启动你的应用，并**清晰地打印出主进程的 PID**。
    - **关键实现**:
      - 使用 `&` 将应用放到后台运行。
      - 使用 `pgrep`, `cat /path/to/pidfile` 或 `$!` 等方法，**可靠地**获取到主进程的 PID。
      - 用 `echo "✅ YOUR_APP 已在运行，PID: ${PID}"` 这样的格式，将 PID 打印到标准输出。这是后续所有自动化脚本的基础。
    - **参考**: `showcases/mysql/start_mysql.sh`

3.  **`stop_YOUR_APP.sh` (停止脚本)**:
    - **目的**: 可靠、干净地停止你的应用。
    - **操作**: 编写一个脚本，通过 `pkill`, `kill` 或应用自带的停止命令，来终止进程，并清理所有临时文件。
    - **参考**: `showcases/mysql/stop_mysql.sh`

### 第二步：负载生成脚本 (`run_load.sh`)

`pipa` 在一个空闲的进程上，是看不到太多东西的。你需要一个能够**模拟真实负载**的脚本。

1.  **选择负载工具**:

    - **Nginx**: 可以使用 `wrk`, `ab (Apache Bench)` 或 `vegeta` 等 HTTP 压测工具。
    - **Elasticsearch**: 可以使用官方的 `rally`，或者一个简单的、循环发送查询请求的 Python/Shell 脚本。

2.  **`run_YOUR_LOAD.sh` (负载脚本)**:
    - **目的**: 启动负载工具，对你的应用施加压力。
    - **关键实现**:
      - 脚本应该接受**参数**来控制负载强度（如并发数、请求速率等），例如 `./run_wrk.sh 128`。
      - 同样地，建议将其设计为可以在后台运行 (`&`)。
    - **参考**: `showcases/mysql/run_sysbench.sh`

### 第三步：`pipa` 集成与自动化 (`ultimate_test.sh`)

现在，是时候让 `pipa` 登场了。我们强烈建议你创建一个自动化的端到端测试脚本，将所有步骤串联起来。

1.  **`ultimate_test.sh` (自动化测试脚本)**:
    - **目的**: 模拟一次完整的“健康检查 -> 施加负载 -> 性能采样 -> 生成报告”的工作流。
    - **操作**: 复制并修改我们项目根目录下的 `ultimate_mysql_test.sh`。
    - **关键修改点**:
      - 将 `start_mysql.sh` 替换为 `start_YOUR_APP.sh`。
      - 将 `run_sysbench.sh` 替换为 `run_YOUR_LOAD.sh`。
      - 调整 `pipa sample` 的参数，比如采样时长。
      - 确保脚本最后能成功生成 `analyze` 报告和 `flamegraph`。

### 第四步：文档 (`README.md`)

最后，为你自己和你的同事，编写一份清晰的说明文档。

1.  **`README.md`**:
    - **目的**: 解释这个 Showcase 的用途、如何设置环境、以及如何一步步手动执行性能分析。
    - **内容模板**:
      - **简介**: 简要说明这个 Showcase 的目标。
      - **前置依赖**: 列出需要安装的工具（如 `wrk`, `rally`）。
      - **快速开始**: 提供一个“一键式”的命令，直接调用你的 `ultimate_test.sh`。
      - **手动分析步骤**:
        1.  `source ./env.sh`
        2.  `./start_YOUR_APP.sh`
        3.  `./run_YOUR_LOAD.sh` (在另一个终端)
        4.  `pipa healthcheck`
        5.  `pipa sample ...` (提供完整的示例命令)
        6.  `pipa analyze ...`
        7.  `pipa flamegraph ...`
      - **结果解读**: (可选) 对生成的报告中可能出现的典型现象，进行简要的分析和说明。
    - **参考**: `showcases/mysql/README.md`
