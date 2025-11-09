# MySQL Showcase for Pipa

这是一个展示如何使用 Pipa 对 MySQL 数据库进行性能分析和校准的完整示例。

## 🏗️ 架构特点

本 Showcase 采用**关注点分离**的设计原则：

- **`env.sh`**: 单一事实来源（Single Source of Truth）- 所有配置变量的定义
- **`setup.sh`**: 环境准备逻辑 - 编译、安装、初始化
- **`workload.yaml`**: Pipa 工作负载配置 - 使用环境变量引用路径和参数
- **`config/my.cnf.template`**: MySQL 配置模板

## 📋 前置条件

- CentOS/RHEL 系统
- 足够的磁盘空间（约 5GB）
- 编译工具链（setup.sh 会自动安装）
- 多核 CPU（建议至少 128 核用于 taskset 绑核）

## 🚀 快速开始

### 1️⃣ 配置密码 (仅需一次)

打开 `showcases/mysql/env.sh` 并设置你的 `MYSQL_ROOT_PASSWORD`。

### 2️⃣ 一键准备环境 (仅需一次)

```bash
./showcases/mysql/setup.sh
```

> 该脚本会自动加载 `env.sh`。编译过程可能需要 30-60 分钟。

### 3️⃣ 运行 Pipa 实验 (任意多次)

**重要**: `pipa` 命令本身是一个独立的 Python 进程，它需要从你当前的 shell 环境中继承变量。因此，在运行 `pipa` 之前，你**仍然需要 `source` 一次**。

```bash
# 1. 加载环境变量 (每次新终端)
source showcases/mysql/env.sh

# 2. 运行 Pipa
pipa -vv calibrate --workload showcases/mysql/workload.yaml --output-config showcases/mysql/mysql_calibrated.yaml
```

## 📂 目录结构

```
showcases/mysql/
├── env.sh                    # 环境变量配置（单一事实来源）
├── setup.sh                  # 环境准备脚本
├── workload.yaml             # Pipa 工作负载配置
├── README.md                 # 本文件
├── config/
│   └── my.cnf.template       # MySQL 配置模板
└── build/                    # 构建产物目录（由 setup.sh 创建）
    ├── mysql/                # MySQL 安装目录
    ├── sysbench/             # Sysbench 安装目录
    ├── data/                 # MySQL 数据目录
    └── logs/                 # MySQL 日志目录
```

## 🔧 工作流说明

### 典型的日常使用流程

```bash
# 1. 加载环境（每次新终端）
source showcases/mysql/env.sh

# 2. 运行 Pipa（可重复多次）
pipa calibrate --workload showcases/mysql/workload.yaml -vv
```

### 清理和重置

如果需要重新开始：

```bash
rm -rf showcases/mysql/build/
./showcases/mysql/setup.sh
```

## 📝 配置说明

### 环境变量（env.sh）

| 变量名                | 说明            | 默认值                 |
| --------------------- | --------------- | ---------------------- |
| `MYSQL_ROOT_PASSWORD` | MySQL root 密码 | `your_secure_password` |
| `MYSQL_INSTALL_DIR`   | MySQL 安装目录  | `$BASE_DIR/mysql`      |
| `MYSQL_DATA_DIR`      | MySQL 数据目录  | `$BASE_DIR/data`       |
| `SYSBENCH_TABLES`     | Sysbench 表数量 | `8`                    |
| `SYSBENCH_TABLE_SIZE` | 每表行数        | `10000`                |

### 工作负载参数（workload.yaml）

- **intensity_variable**: Sysbench 线程数，范围 8-256
- **target_load_levels**: 低负载（15-25% CPU）和高负载（90-100% CPU）
- **collectors**: 使用 perf_stat 和 sar_cpu 进行性能数据采集

## 🎯 设计理念

### DRY 原则（Don't Repeat Yourself）

所有配置参数只在 `env.sh` 中定义一次，其他文件通过环境变量引用，避免重复和不一致。

### 单一职责原则

- `env.sh`: 只负责定义配置
- `setup.sh`: 只负责执行安装逻辑
- `workload.yaml`: 只负责描述工作负载

### 可维护性

修改密码或路径？只需编辑 `env.sh` 一个文件！

## 🐛 故障排查

### 问题：pipa 找不到 mysqld 进程

**原因**: 未加载环境变量

**解决**: 确保执行了 `source showcases/mysql/env.sh`

### 问题：setup.sh 失败

**原因**: 可能缺少依赖或磁盘空间不足

**解决**:

1. 检查磁盘空间：`df -h`
2. 查看详细日志
3. 删除 `build/` 目录重试

### 问题：MySQL 启动失败

**原因**: 端口被占用或权限问题

**解决**:

1. 检查是否有其他 MySQL 实例在运行
2. 确保当前用户有 `build/` 目录的写权限

## 📖 扩展阅读

- [Pipa 官方文档](../../README.md)
- [MySQL Performance Tuning](https://dev.mysql.com/doc/refman/8.0/en/optimization.html)
- [Sysbench 使用指南](https://github.com/akopytov/sysbench)

---

**提示**: 这个 Showcase 展示了专业级的配置管理实践，是生产环境部署的良好参考。
