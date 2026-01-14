# Pipa Showcase: MySQL 性能分析场景 (Huawei Kunpeng 920)

本案例是 PIPA 在 **华为鲲鹏 920 (ARM64)** 架构下的深度性能调优与分析实战演示。它严格遵循《鲲鹏 BoostKit 数据库使能套件指南》，通过对比不同调优阶段的性能表现，展示 PIPA 如何精准定位性能瓶颈。

---

## 🛠️ 核心工作流

为了复现高性能场景下的细微差异，本案例采用严格的 **Profile（场景配置）** 驱动模式：

1.  **OS 调优**：应用中断绑核、透明大页禁用等底层优化。
2.  **数据准备**：生成标准的 Sysbench 测试数据集。
3.  **场景运行**：选择特定的 Profile（如 `baseline` vs `optimized`）执行自动化测试。
4.  **对比分析**：使用 PIPA 生成的报告对比不同配置下的吞吐量与资源消耗。

---

## 🚀 快速开始

### 1. 操作系统基线调优 (Root 权限)

**⚠️ 关键步骤**：在鲲鹏服务器上，默认的 OS 配置无法发挥硬件性能。请务必运行此脚本进行中断绑核和内核参数优化。

```bash
# 需要 sudo 权限
sudo ./showcases/mysql_sysbench_huawei/initialize.sh
```

### 2. 环境初始化与数据准备

编译 MySQL 8.0 和 Sysbench，并生成测试数据（默认 64 张表，1000 万数据量，视 `env.sh` 配置而定）。

```bash
# 1. 编译安装 (首次运行)
./showcases/mysql_sysbench_huawei/setup.sh

# 2. (可选) 强制重置数据集
# 如果你需要一个干净的测试环境，或者修改了表数量配置，请执行：
./showcases/mysql_sysbench_huawei/force_rebuild.sh
```

### 3. 执行自动化测试场景 (Profile)

本案例预置了多个典型场景，你可以通过传递 Profile 名称来运行测试。

**用法：**
```bash
./showcases/mysql_sysbench_huawei/run_with_profile.sh <PROFILE_NAME>
```

**可用 Profile 列表：**

| Profile 名称 | 描述 | 预期效果 |
| :--- | :--- | :--- |
| `baseline` | **默认基线**。未进行深度调优的配置。 | 吞吐量较低，存在明显的锁竞争或资源瓶颈。 |
| `optimized` | **通用调优**。应用了常规的 MySQL 参数优化。 | 吞吐量提升，延迟降低。 |
| `boostkit` | **鲲鹏极速模式**。针对 ARM64 指令集和 NUMA 架构的深度优化。 | 极限吞吐量，CPU 利用率最优。 |
| `contention_64_threads` | **高并发锁竞争**。特意制造的热点冲突场景。 | 用于观察 PIPA 如何分析 Mutex 锁争用。 |

**示例：运行优化后的场景**
```bash
./showcases/mysql_sysbench_huawei/run_with_profile.sh optimized
```

测试完成后，结果将保存在 `evidence/<时间戳>_<profile>/` 目录下。

---

## 📊 结果产出与分析

每个测试运行结束后，你将获得：

1.  **`report.html`**: PIPA 生成的交互式性能分析报告。
2.  **`snapshot.pipa`**: 原始采样数据，可用于后续重新分析或对比。
3.  **`sysbench.log`**: 具体的 TPS/QPS 压测数据。
4.  **`actual_my.cnf` & `profile_env.sh`**: 记录当时的实际配置，确保实验可回溯。

---

## 🔬 手动调试指南 (高级)

如果你需要手动介入（例如调试某个特定参数），请遵循以下步骤以确保环境一致性：

1.  **加载基础环境与 Profile 配置**：
    ```bash
    source showcases/mysql_sysbench_huawei/env.sh
    # 加载你想要调试的 Profile (例如 optimized)
    source showcases/mysql_sysbench_huawei/profiles/optimized/env.sh
    ```

2.  **生成配置文件并启动 MySQL**：
    ```bash
    envsubst < showcases/mysql_sysbench_huawei/config/my.cnf.template > $MYSQL_INSTALL_DIR/etc/my.cnf
    ./showcases/mysql_sysbench_huawei/start_mysql.sh
    ```

3.  **运行 Sysbench (注意绑核)**：
    为了避免客户端压力干扰服务端，**必须**使用 `taskset` 将 Sysbench 绑定到特定的 CPU 核（脚本变量 `$SYSBENCH_CPU_AFFINITY`）。
    ```bash
    # 使用脚本中预定义的绑核策略运行
    ./showcases/mysql_sysbench_huawei/run_sysbench.sh 128
    ```

4.  **执行 PIPA 采样**：
    ```bash
    MYSQL_PID=$(pgrep -x mysqld)
    pipa sample --attach-to-pid $MYSQL_PID --duration 60 --output manual_test.pipa
    ```

5.  **停止服务**：
    ```bash
    ./showcases/mysql_sysbench_huawei/stop_mysql.sh
    ```
