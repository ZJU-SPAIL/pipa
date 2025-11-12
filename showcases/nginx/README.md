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

pipa -vv sample \
    --attach-to-pid ${NGINX_PID} \
    --duration-stat 60 \
    --duration-record 60 \
    --output my_app_snapshot.pipa

# 5. 分析快照并生成报告
pipa analyze \
    --input nginx_snapshot.pipa \
    --output nginx_report.html

# 6. 停止 Nginx
./stop_nginx_server.sh
```
