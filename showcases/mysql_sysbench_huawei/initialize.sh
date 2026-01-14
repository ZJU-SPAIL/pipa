#!/bin/bash
set -e
# -----------------------------------------------------------------------------
# 操作系统基线调优脚本 - 数据库场景专用
# 引用依据: 《鲲鹏 BoostKit 数据库使能套件 数据库性能调优指南》 第 3 章
# -----------------------------------------------------------------------------

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

if [ "$(id -u)" -ne 0 ]; then
    log_err "OS 调优需要 root 权限，请使用 sudo 执行。"
    exit 1
fi

# 确保 ethtool 存在，用于获取 PCIe 总线号以进行精准中断绑定
if ! command -v ethtool &> /dev/null; then
    log_info "正在安装 ethtool 用于硬件探测..."
    yum install -y ethtool > /dev/null 2>&1
fi

log_info ">>> [Step 1] 开始应用鲲鹏 920 数据库性能基线 (OS Level) <<<"

# --- 1. 关闭防火墙和 SELinux (引用依据: 指南 3.1 节, P5) ---
log_info "[3.1] 关闭防火墙和 SELinux 以消除网络与权限干扰..."
if systemctl is-active --quiet firewalld; then
    systemctl stop firewalld.service || true
    systemctl disable firewalld.service || true
fi
setenforce 0 2>/dev/null || true
if [ -f /etc/selinux/config ]; then
    sed -i 's/^SELINUX=.*/SELINUX=disabled/' /etc/selinux/config
fi

# --- 2. 禁用 irqbalance (引用依据: 指南 3.4 节, P7) ---
log_info "[3.4] 停止并禁用 irqbalance 服务..."
if systemctl is-active --quiet irqbalance; then
    systemctl stop irqbalance.service || true
    systemctl disable irqbalance.service || true
else
    log_info "  -> irqbalance 未运行。"
fi

# --- 3. 网卡中断绑核 (引用依据: 指南 3.4 节, P7) ---
# 数据库场景下，将中断绑定至特定 NUMA 节点可显著降低 CPU 上下文切换开销
log_info "[3.4] 正在执行网卡中断多队列亲和性绑定..."

# 物理网卡探测逻辑
ROUTE_IF=$(ip route get 8.8.8.8 2>/dev/null | awk '{print $5}' | head -1)
if [[ -z "$ROUTE_IF" || "$ROUTE_IF" == "lo" || "$ROUTE_IF" == *"docker"* || "$ROUTE_IF" == *"virbr"* ]]; then
    INTERFACE=$(ls /sys/class/net | grep -E '^(en|eth)' | head -1)
else
    INTERFACE="$ROUTE_IF"
fi

if [ -n "$INTERFACE" ]; then
    log_info "  -> 锁定目标物理网卡: [ $INTERFACE ]"
    BUS_INFO=$(ethtool -i $INTERFACE 2>/dev/null | grep 'bus-info' | awk '{print $2}')

    if [ -n "$BUS_INFO" ]; then
        log_info "  -> 获取到 PCIe 总线 ID: [ $BUS_INFO ]"
        IRQS=$(grep "$BUS_INFO" /proc/interrupts | awk '{print $1}' | sed 's/://')
    else
        IRQS=$(grep "$INTERFACE" /proc/interrupts | awk '{print $1}' | sed 's/://')
    fi

    if [ -n "$IRQS" ]; then
        # 依据 env.sh 定义的 IRQ_BIND_CORES (通常为 Node 1)
        # 解析范围例如 "32-63" -> Start 32
        IRQ_START_CORE=$(echo $IRQ_BIND_CORES | awk -F'-' '{print $1}')
        IRQ_END_CORE=$(echo $IRQ_BIND_CORES | awk -F'-' '{print $2}')

        CORE_IDX=$IRQ_START_CORE
        BIND_COUNT=0

        for IRQ in $IRQS; do
            if [ $CORE_IDX -le $IRQ_END_CORE ]; then
                if [ -f "/proc/irq/$IRQ/smp_affinity_list" ]; then
                    echo $CORE_IDX > /proc/irq/$IRQ/smp_affinity_list
                    CORE_IDX=$((CORE_IDX + 1))
                    BIND_COUNT=$((BIND_COUNT + 1))
                fi
            else
                CORE_IDX=$IRQ_START_CORE # 循环绑定
            fi
        done
        log_info "  -> 中断绑定完成: 共处理 $BIND_COUNT 个队列 (绑定范围: $IRQ_BIND_CORES)。"
    fi
else
    log_err "⚠️ 警告: 未找到物理网卡，跳过中断绑定。"
fi

# --- 4. 网络与内存内核参数优化 (引用依据: 指南 3.5 节, P8-9) ---
log_info "[3.5] 正在配置 /etc/sysctl.d/99-kunpeng-mysql.conf..."
cat <<EOF > /etc/sysctl.d/99-kunpeng-mysql.conf
# 鲲鹏 MySQL 调优基线参数 (BoostKit Guide Chapter 3.5)
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 8192
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
vm.swappiness = 1
vm.dirty_ratio = 5
EOF
sysctl -p /etc/sysctl.d/99-kunpeng-mysql.conf > /dev/null
log_info "✅ 内核参数已加载。"

# --- 5. 关闭透明大页 (引用依据: 指南 3.7 节, P10) ---
# 数据库场景必须关闭 THP 以避免延迟抖动
log_info "[3.7] 禁用透明大页 (Transparent Huge Pages)..."
if [ -f /sys/kernel/mm/transparent_hugepage/enabled ]; then
    echo never > /sys/kernel/mm/transparent_hugepage/enabled
fi
if [ -f /sys/kernel/mm/transparent_hugepage/defrag ]; then
    echo never > /sys/kernel/mm/transparent_hugepage/defrag
fi
log_info "  -> THP 已禁用。"

# --- 6. IO 调度算法优化 (引用依据: 指南 3.9 节, P11) ---
# 数据库场景建议使用 deadline 或 noop
log_info "[3.9] 正在调整磁盘 IO 调度算法..."

# 动态探测存放 MySQL 数据的磁盘设备
# 逻辑: 获取 BASE_DIR 挂载点的设备名 -> 解析为块设备名 (如 sda)
TARGET_DEV=$(df -P "$BASE_DIR" | tail -1 | awk '{print $1}')
if [[ "$TARGET_DEV" == /dev/* ]]; then
    # 处理 /dev/sda1 -> sda 的情况，兼容 NVMe /dev/nvme0n1p1 -> nvme0n1
    BLK_DEV=$(lsblk -no pkname "$TARGET_DEV" | head -1)

    if [ -z "$BLK_DEV" ]; then
        # 如果 lsblk 没拿到，尝试直接去掉数字 (fallback)
        BLK_DEV=$(echo "$TARGET_DEV" | sed 's/[0-9]*$//' | awk -F/ '{print $NF}')
    fi

    SCHEDULER_PATH="/sys/block/$BLK_DEV/queue/scheduler"
    if [ -f "$SCHEDULER_PATH" ]; then
        # 优先设置 deadline，如果不支持则尝试 noop (常见于云盘/NVMe)
        if grep -q "deadline" "$SCHEDULER_PATH"; then
            echo deadline > "$SCHEDULER_PATH"
            log_info "  -> 磁盘 $BLK_DEV ($TARGET_DEV) 调度算法已设置为: deadline"
        elif grep -q "none" "$SCHEDULER_PATH"; then
             # NVMe 多队列通常使用 none
            echo none > "$SCHEDULER_PATH"
            log_info "  -> 磁盘 $BLK_DEV ($TARGET_DEV) 为多队列设备，保持模式: none"
        else
            log_info "  -> 磁盘 $BLK_DEV 不支持 deadline，当前状态: $(cat $SCHEDULER_PATH)"
        fi

        # 调整队列深度 (指南建议)
        echo 2048 > "/sys/block/$BLK_DEV/queue/nr_requests" 2>/dev/null || true
    else
        log_info "  -> 无法定位调度器配置文件，跳过 IO 优化。"
    fi
else
    log_info "  -> 数据目录非物理块设备挂载 (可能是 tmpfs/overlay)，跳过 IO 优化。"
fi

# --- 7. 文件描述符上限 (引用依据: 指南 3.3.1 节) ---
log_info "[3.3.1] 检查系统文件描述符限制..."
ulimit -n 65535
log_info "  -> 当前 Shell ulimit -n 已设置为 $(ulimit -n)"

log_info "✅ 操作系统层调优执行完毕。"
