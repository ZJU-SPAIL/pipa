# Pipa Showcase: 磁盘 I/O 极限压力测试 (FIO 版)

本案例使用业界标准工具 **FIO (Flexible I/O Tester)** 模拟高并发随机写场景，用于验证 PIPA 在 **Disk Saturation** 和 **High Latency** 下的诊断能力。

---

## 📋 前置要求

- **FIO**: 系统必须已安装 `fio` 工具 (`yum install fio` 或 `apt install fio`)。
- **磁盘空间**: 默认配置需要约 80GB (10G \* 8 Jobs) 可用空间。

## ⚙️ 配置目标磁盘 (关键!)

默认情况下，测试文件会生成在 `showcases/io_intensive/build` 目录下。
如果您的项目位于系统盘（通常是 SSD），测试可能无法触发高延迟告警。

**为了测试机械硬盘 (HDD) 的性能瓶颈，请修改 `env.sh`：**

1.  打开 `showcases/io_intensive/env.sh`。
2.  修改 `IO_TARGET_DIR` 变量，指向您的 HDD 挂载点。

```bash
# 示例：指向挂载在 /mnt/hdd_data 的机械硬盘
export IO_TARGET_DIR="/mnt/hdd_data/fio_test"
```
