# Pipa Showcase: Nginx 性能分析 (v2 - 重构版)

这是一个经过重构的 showcase，旨在演示如何使用 Pipa 对 Nginx Web 服务器进行**自动化、可重复的**性能分析。它遵循 Pipa 项目的最佳实践，强调自动化和配置驱动。

---

## 🚀 一键式分析: 终极测试

这是运行一次完整 Nginx 性能分析实验的**推荐方法**。它会自动处理所有步骤，从启动服务到生成最终报告。

#### **第 1 步: 环境准备 (仅需一次)**

```bash
# 这将编译并安装 Nginx 和负载测试工具 WRK
./showcases/nginx/setup.sh
```

#### **第 2 步: 运行终极测试脚本！**

```bash
# 这个脚本将完成所有工作：
# 1. 启动 Nginx
# 2. 施加后台负载
# 3. 运行 pipa healthcheck, sample, analyze, flamegraph
# 4. 自动清理所有进程
./showcases/nginx/ultimate_nginx_test.sh
```

实验结束后，你将在 `showcases/nginx/` 目录下找到两个核心产出物：

- `nginx_ultimate_report.html`: 完整的 HTML 分析报告。
- `nginx_ultimate_flamegraph.svg`: 可交互的火焰图。

---

## 🔬 手动分步分析

如果你想深入了解每个步骤或进行自定义分析，可以按照以下流程手动操作。

#### **1. 准备环境**

```bash
# 加载所有环境变量
source ./showcases/nginx/env.sh

# 运行一次性安装 (如果还没做)
./showcases/nginx/setup.sh
```

#### **2. 启动服务**

```bash
# 启动 Nginx，脚本会自动打印出 worker 进程的 PID 列表
./showcases/nginx/start_nginx.sh
```

#### **3. 施加负载 (在另一个终端)**

```bash
# 在后台启动一个持续的 wrk 压测
./showcases/nginx/run_load.sh &
```

#### **4. 运行 Pipa**

```bash
# a. 运行健康检查 (推荐)
pipa healthcheck

# b. 捕获 Nginx Worker PIDs
NGINX_PIDS=$(pgrep -f "nginx: worker process" | tr '\n' ',' | sed 's/,$//')
echo "Target PIDs: ${NGINX_PIDS}"

# c. 执行性能快照
pipa sample \
    --attach-to-pid "${NGINX_PIDS}" \
    --duration-stat 60 \
    --duration-record 60 \
    --output nginx_manual_snapshot.pipa
```

#### **5. 分析与生成报告**

```bash
# a. 生成 HTML 报告
pipa analyze \
    --input nginx_manual_snapshot.pipa \
    --output nginx_manual_report.html

# b. 生成火焰图
pipa flamegraph \
    --input nginx_manual_snapshot.pipa \
    --output nginx_manual_flamegraph.svg
```

#### **6. 清理**

```bash
# 停止所有相关进程 (Nginx 和 wrk)
./showcases/nginx/stop_nginx.sh
```

---

## ⚙️ 配置

所有可配置项（如 Nginx 版本、worker 数量、CPU 亲和性、WRK 参数等）都集中在 **`env.sh`** 文件中。这是此 showcase 的“单一事实来源”。

## 📂 文件结构

- **`setup.sh`**: (新) 一次性环境准备。
- **`start_nginx.sh`**: (新) 启动服务并按协议输出 PIDs。
- **`stop_nginx.sh`**: (新) 健壮地停止所有相关进程。
- **`run_load.sh`**: (新) 施加 `wrk` 负载。
- **`ultimate_nginx_test.sh`**: (新) 核心的自动化测试脚本。
- **`env.sh`**: 所有配置。
- **`config/nginx.conf.template`**: Nginx 配置模板。
