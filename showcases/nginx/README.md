# Pipa Showcase: Nginx 高并发性能分析

本案例演示了针对 Web 服务器场景的性能诊断。我们将模拟 **Gzip 高压缩** 场景，制造高 CPU 负载，以验证 PIPA 的物理感知诊断能力。

---

## 📋 前置要求

执行环境准备脚本，编译安装 Nginx 和 wrk 压测工具。

```bash
# 首次运行需执行
./showcases/nginx/setup.sh
```

## 🚀 一键式终极测试 (推荐)

自动化脚本将启动 Nginx（配置为 32 Worker），并使用 wrk 进行饱和式压测，最后生成全套分析报告。

```bash
./showcases/nginx/ultimate_nginx_test.sh
```

**产出物：**

- `nginx_snapshot.pipa`: 原始数据快照包 使用`tar -xzf .\nginx_snapshot.pipa`
- `nginx_report.html`: 交互式分析报告（包含 TMA 微架构分析）
- `nginx_flamegraph.svg`: 性能火焰图

---

## 🔬 手动分步操作指南

### 1. 启动 Nginx 服务

```bash
source ./showcases/nginx/env.sh
./showcases/nginx/start_nginx.sh
```

_注意：Nginx 将绑定到 CPU 0-31 核心运行。_

### 2. 施加压力 (wrk)

在另一个终端窗口中运行：

```bash
# 启动 wrk 进行持续的高并发请求
./showcases/nginx/run_load.sh &
```

### 3. 执行 PIPA 采样

```bash
# 1. 自动捕获所有 Nginx Worker PIDs
NGINX_PIDS=$(pgrep -f "nginx: worker process" | tr '\n' ',' | sed 's/,$//')

# 2. 执行采样
pipa sample \
    --attach-to-pid "$NGINX_PIDS" \
    --duration-stat 60 \
    --duration-record 60 \
    --output nginx_manual.pipa
```

### 4. 生成分析报告与火焰图

```bash
pipa analyze --input nginx_manual.pipa --output report.html
pipa flamegraph --input nginx_manual.pipa --output flame.svg
```

### 5. 环境清理

```bash
./showcases/nginx/stop_nginx.sh
```
