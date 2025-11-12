# Nginx 性能分析 Showcase

这个 showcase 展示了如何使用 Pipa 对 Nginx Web 服务器进行性能分析。

## 文件结构

```
showcases/nginx/
├── env.sh                           # 环境配置 (单一事实来源)
├── config/
│   └── nginx.conf.template         # Nginx 配置模板
├── setup_nginx_env.sh            # 编译和安装 Nginx 和 WRK
├── start_nginx_server.sh         # 启动 Nginx 服务器
├── run_performance_collection.sh # 运行基准测试和数据收集
├── run_single_benchmark.sh         # 运行单次 WRK 基准测试
├── stop_nginx_server.sh            # 停止 Nginx 服务器
└── README.md                        # 本文件
```

## 性能分析工作流

### 典型的使用流程：

```bash
# 1. 准备环境（仅需一次）
./setup_nginx_env.sh

# 2. 启动 Nginx
./start_nginx_server.sh

# 3. 运行性能数据收集
./run_performance_collection.sh

```

### 4. 使用 Pipa 对 Nginx 进程进行性能采样和分析(在另一个终端执行)

```sh

NGINX_PID=$(pgrep -x nginx | head -1)

# 先healthcheck在进行采样
pipa healthcheck

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
