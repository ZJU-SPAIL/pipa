# 鲲鹏 BoostKit Nginx 官方基线调优实战 (Huawei Baseline)

本 Showcase 严格遵循华为官方发布的《Nginx 移植&调优指南》，构建了一套全自动化的性能基线测试环境。旨在确立项目在鲲鹏 920 平台上的性能调优标准，并为后续组件（如 MySQL, Redis）提供工程化参考。

> **📚 官方依据：** > [鲲鹏 BoostKit Web 场景 Nginx 移植&调优指南 12.pdf](https://www.hikunpeng.com/doc_center/source/zh/kunpengwebs/ecosystemEnable/Nginx/%E9%B2%B2%E9%B9%8FBoostKit%20Web%E5%9C%BA%E6%99%AF%20Nginx%20%E7%A7%BB%E6%A4%8D&%E8%B0%83%E4%BC%98%E6%8C%87%E5%8D%97%2012.pdf)

---

## 🏗️ 架构设计与资源隔离

为了在单台 128 核服务器上获得准确的基线数据，本方案采用了严格的 **NUMA 物理隔离策略**：

| 组件           | 角色     | 绑核范围 | NUMA 节点 | 说明                                      |
| :------------- | :------- | :------- | :-------- | :---------------------------------------- |
| **Nginx**      | 被测服务 | `0-31`   | Node 0    | 独占一个 NUMA 节点，避免跨片访问          |
| **中断 (IRQ)** | 系统底层 | `32-63`  | Node 1    | 网卡硬中断强制绑定至 Node 1，防止打断业务 |
| **压测工具**   | 负载生成 | `32-127` | Node 1-3  | 施压端与被测端物理隔离，杜绝“抢资源”现象  |

---

## 🛠️ 快速开始

### 1. 环境初始化 (仅需一次)

脚本将自动完成：编译 Nginx 1.19.0、编译压测工具 (wrk/httpress)、应用 OS 内核参数调优。

```bash
sudo ./initialize.sh  # 应用 sysctl 和 IRQ 绑核
./setup.sh            # 编译软件
```

### 2. 执行基线测试 (Profile 模式)

本项目支持 4 种华为官方定义的标准测试场景，通过 Profile 切换：

```bash
# 场景 A: WRK 长连接 (默认基线)
./run_with_profile.sh wrk_long

# 场景 B: WRK 短连接
./run_with_profile.sh wrk_short

# 场景 C: Httpress 长连接
./run_with_profile.sh httpress_long

# 场景 D: Httpress 短连接
./run_with_profile.sh httpress_short
```

---

## 📊 产出物说明 (Evidence)

每次运行结束后，结果会自动归档至 `../../evidence/{时间戳}_{场景名}` 目录：

1.  **`report.html`**: PIPA 智能分析报告（含散点图、决策树）。
2.  **`snapshot.pipa`**: 原始性能数据快照。
3.  **`flamegraph.svg`**: 性能火焰图。
4.  **`nginx_running.conf`**: 运行时生成的 Nginx 配置（含自动计算的 CPU 掩码）。
5.  **`load.log`**: 压测工具的原始输出 (RPS, Latency)。

---

## 💡 核心调优项 (已固化)

所有配置均源自华为官方指南：

- **BIOS/OS**: 关闭 irqbalance，开启 `numa_balancing` 优化。
- **Nginx**:
  - `worker_cpu_affinity`: 二进制掩码级绑定 (Guide P60)
  - `use epoll`, `multi_accept on` (Guide P62)
  - `keepalive_requests 20000` (Guide P61)
