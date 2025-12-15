#!/bin/bash
# -----------------------------------------------------------------------------
# 鲲鹏 Nginx 性能调优官方基线 - 环境配置
# 引用依据: 《鲲鹏 BoostKit Web 使能套件 Nginx 移植&调优指南》 v12
# -----------------------------------------------------------------------------

# --- 基础路径 ---
export SHOWCASE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
export BASE_DIR="$SHOWCASE_DIR/build"
export EVIDENCE_ROOT="$SHOWCASE_DIR/../../evidence"

# --- 软件版本与仓库 (依据合同要求) ---
export NGINX_VERSION="1.19.0"
export NGINX_DOWNLOAD_URL="http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz"

# 压测工具仓库 (禹调科技镜像站，公开可访问，便于复现)
export WRK_REPO_URL="http://gitlab.youtune.tech/pymirror/wrk.git"
export HTTPRESS_REPO_URL="http://gitlab.youtune.tech/pymirror/httpress.git"

# --- 资源隔离策略 (128核鲲鹏920) ---
# Nginx 被测端: 独占 NUMA Node 0 (Cores 0-31)
export NGINX_CORE_START=0
export NGINX_WORKER_COUNT=32

# start_nginx.sh 需要这个变量来做 taskset 启动绑定
export NGINX_CPU_AFFINITY="${NGINX_CORE_START}-$((NGINX_CORE_START + NGINX_WORKER_COUNT - 1))"

# PIPA 分析时需要的预期字符串 (与上面保持一致)
export NGINX_PIPA_EXPECTED_CPUS="$NGINX_CPU_AFFINITY"

# 压测端 (WRK/Httpress) 与 中断处理: 独占 NUMA Node 1-3 (Cores 32-127)
export LOAD_GEN_CPU_AFFINITY="32-127"
export IRQ_BIND_CORES="32-63" # 中断绑定至 Node 1

# --- 内部变量 ---
export NGINX_INSTALL_DIR="$BASE_DIR/nginx"
export NGINX_LOGS_DIR="$BASE_DIR/logs"
export TOOLS_DIR="$BASE_DIR/tools"
export NGINX_CONF_PATH="$NGINX_INSTALL_DIR/conf/nginx.conf"

# 动态生成 worker_cpu_affinity 二进制掩码 (依据指南 P60, 表3-4)
# 用于 nginx.conf 配置文件
generate_affinity_mask() {
    python3 -c "
count = $NGINX_WORKER_COUNT
start = $NGINX_CORE_START
masks = []
for i in range(count):
    mask_int = 1 << (start + i)
    masks.append(bin(mask_int)[2:])
print(' '.join(masks))
"
}
export NGINX_CPU_AFFINITY_MASK=$(generate_affinity_mask)

# --- PIPA 采样配置 ---
export DURATION_STAT=60
export DURATION_RECORD=60

# --- 5. 压测参数 (根据指南 P60 调整) ---
export TARGET_URL="http://127.0.0.1:8000/index.html"

# 短连接场景参数
export LOAD_SHORT_CONN=1000
export LOAD_SHORT_DURATION="140s"

# 长连接场景参数
export LOAD_LONG_CONN=5000
export LOAD_LONG_DURATION="140s"

# 日志格式化输出
log_info() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] [INFO] $1"; }
log_err() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] $1"; }
