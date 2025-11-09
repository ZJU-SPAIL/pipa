# Pipa Showcase: 手动分析 MySQL 性能

这是一个展示如何使用 Pipa 对一个**外部管理的** MySQL 数据库进行性能快照的教程。它完美地演示了 Pipa 作为纯粹“观察者”的核心哲学。

## 🚀 快速开始

### 1️⃣ 准备环境 (仅需一次)

1.  **配置密码**: 打开 `env.sh` 并设置你的 `MYSQL_ROOT_PASSWORD`。
2.  **运行安装脚本**:
    ```bash
    ./showcases/mysql/setup.sh
    # 这将花费 30-60 分钟编译并初始化 MySQL 和 Sysbench。
    ```

### 2️⃣ 核心分析工作流 (可重复)

这是一个典型的、手动的性能分析场景：

**第 1 步: 加载环境**
_每次打开新终端时，都需要执行此操作以加载所有路径。_

```bash
source showcases/mysql/env.sh
```

**第 2 步: 启动 MySQL 服务**

```bash
./showcases/mysql/start_mysql.sh
# 输出: ✅ MySQL 服务器已在运行，PID: 12345
```

**第 3 步: 施加负载**
_在后台启动 Sysbench 压测，模拟生产负载。_

```bash
# 使用 32 个线程进行压测
./showcases/mysql/run_sysbench.sh 32 &
```

**第 4 步: 使用 Pipa 进行快照！**
_这是核心步骤。我们告诉 Pipa 去观察正在运行的 `mysqld` 进程。_

```bash
# 找到 mysqld 的 PID
MYSQL_PID=$(pgrep -x mysqld)

# 运行 pipa sample！
pipa sample \
    --attach-to-pid "${MYSQL_PID}" \
    --duration 60 \
    --collectors-config showcases/mysql/mysql_collectors.yaml \
    --output mysql_snapshot_32threads.pipa
```

**第 5 步: 分析结果**

```bash
pipa analyze --input mysql_snapshot_32threads.pipa --output report_32threads.html
```

_在浏览器中打开 `report_32threads.html` 查看分析报告。_

**第 6 步: 清理**
_停止压测（如果仍在运行）和 MySQL 服务。_

```bash
# 停止 sysbench (如果需要)
pkill sysbench

# 停止 MySQL
./showcases/mysql/stop_mysql.sh
```

---

这个工作流完美地体现了 Pipa 的设计理念：**你管理应用，Pipa 负责观察。**
