# Nginx 性能分析 Showcase

这个 showcase 展示了如何使用 Pipa 对 Nginx Web 服务器进行性能分析。

## 文件结构

```
showcases/nginx/
├── env.sh                           # 环境配置 (单一事实来源)
├── config/
│   └── nginx.conf.template         # Nginx 配置模板
├── 1_setup_nginx_env.sh            # 编译和安装 Nginx 和 WRK
├── 2_start_nginx_server.sh         # 启动 Nginx 服务器
├── 3_run_performance_collection.sh # 运行基准测试和数据收集
├── run_single_benchmark.sh         # 运行单次 WRK 基准测试
├── stop_nginx_server.sh            # 停止 Nginx 服务器
└── README.md                        # 本文件
```

## 快速开始

### 1. 准备环境

首先，设置 Nginx 和 WRK 的编译和安装：

```bash
cd showcases/nginx
./1_setup_nginx_env.sh
```

这个脚本会：
- 安装必要的编译依赖
- 从源代码编译 Nginx
- 从源代码编译 WRK（高性能 HTTP 基准测试工具）
- 从模板生成 `nginx.conf` 配置文件

**注意**: 第一次运行需要几分钟。之后的运行会跳过已完成的步骤（幂等性）。

### 2. 启动 Nginx 服务器

```bash
./2_start_nginx_server.sh
```

这会启动 Nginx 服务器，监听 `http://localhost:8000/`

### 3. 运行性能测试

选择以下两种方式之一：

#### 方式 A: 运行单次基准测试

```bash
./run_single_benchmark.sh
```

这会运行两个测试：
- 保活连接测试 (Keep-Alive)
- 关闭连接测试 (Close)

#### 方式 B: 运行完整性能数据收集（推荐）

```bash
./3_run_performance_collection.sh
```

这会运行 10 轮完整的性能测试，收集的指标包括：
- CPU 使用率（用户态、系统态）
- 中断处理时间 (IRQ, SoftIRQ)
- CPU 性能计数器（周期数、指令数、缓存性能等）
- 上下文切换次数
- WRK 基准测试结果（延迟、吞吐量）

结果会保存到 `build/output/nginx_performance_data.csv`

### 4. 停止 Nginx 服务器

```bash
./stop_nginx_server.sh
```

## 配置文件说明

### env.sh

这是环境配置文件，定义了所有需要的变量和路径。可以修改以下参数：

```bash
# Nginx 配置
NGINX_VERSION="1.24.0"           # Nginx 版本
NGINX_WORKER_PROCESSES=4         # Worker 进程数
NGINX_CPU_AFFINITY="0-3"         # CPU 亲和性绑定

# WRK 基准测试参数
WRK_THREADS=4                    # 测试线程数
WRK_CONNECTIONS=100              # 并发连接数
WRK_DURATION="30s"               # 测试持续时间
WRK_CPU_AFFINITY="4-7"          # CPU 亲和性绑定
WRK_TARGET_URL="http://localhost:8000/"  # 测试目标
```

## 性能分析工作流

典型的使用流程：

```bash
# 1. 准备环境（仅需一次）
./1_setup_nginx_env.sh

# 2. 启动 Nginx
./2_start_nginx_server.sh

# 3. 运行性能数据收集
./3_run_performance_collection.sh

# 4. 使用 Pipa 对 Nginx 进程进行性能采样和分析
# (在另一个终端执行)
NGINX_PID=$(pgrep -x nginx | head -1)
pipa sample \
    --attach-to-pid "${NGINX_PID}" \
    --duration 60 \
    --output nginx_snapshot.pipa

# 5. 分析快照并生成报告
pipa analyze \
    --input nginx_snapshot.pipa \
    --output nginx_report.html

# 6. 停止 Nginx
./stop_nginx_server.sh
```

## 故障排除

### 问题: "Permission denied" 或 "sudo password required"

某些步骤需要 root 权限来安装系统依赖。确保你的用户可以无密码执行 `sudo`，或在运行脚本前手动安装依赖。

### 问题: "Port 8000 already in use"

修改 `env.sh` 中的 `WRK_TARGET_URL` 以使用不同的端口，或者停止占用该端口的其他服务。

### 问题: "WRK executable not found"

确保已运行 `1_setup_nginx_env.sh` 来编译 WRK。

## 高级用法

### 使用不同的 CPU 亲和性

修改 `env.sh` 中的 `NGINX_CPU_AFFINITY` 和 `WRK_CPU_AFFINITY` 来指定不同的 CPU 核心。例如：

```bash
NGINX_CPU_AFFINITY="0-7"      # 使用核心 0-7
WRK_CPU_AFFINITY="8-15"       # 使用核心 8-15
```

### 修改基准测试参数

在 `env.sh` 中调整 WRK 参数以获得不同的测试场景：

```bash
WRK_THREADS=8              # 增加测试线程
WRK_CONNECTIONS=500        # 增加并发连接
WRK_DURATION="60s"         # 延长测试时间
```

### 清理构建产物

要重新开始，可以删除成功标志：

```bash
rm -f build/.setup_success
```

下次运行 `1_setup_nginx_env.sh` 时，它将重新编译。

## 许可证

这个 showcase 是 Pipa 项目的一部分。
