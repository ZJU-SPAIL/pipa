#!/bin/bash

# =================================================================
# Pipa Showcase: Nginx - 环境配置文件
# 这是本案例的"单一事实来源"(Single Source of Truth)。
# 在运行任何脚本之前，请先 source 此文件: `source showcases/nginx/env.sh`
# =================================================================

# --- 用户可配置区域 ---

# --- 核心路径定义 ---
# 获取此脚本所在的目录，作为 showcase 的根目录
export SHOWCASE_DIR
SHOWCASE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

# 所有构建产物和数据都将存放在 showcase 目录下的 build/ 子目录中
export BASE_DIR="$SHOWCASE_DIR/build"
export NGINX_INSTALL_DIR="$BASE_DIR/nginx"
export NGINX_LOGS_DIR="$BASE_DIR/logs"
export WRK_INSTALL_DIR="$BASE_DIR/wrk"

# --- 衍生路径 (无需修改) ---
export NGINX_PID_PATH="$NGINX_LOGS_DIR/nginx.pid"
export NGINX_CONF_PATH="$NGINX_INSTALL_DIR/conf/nginx.conf"

# --- Nginx 配置参数 ---
export NGINX_VERSION="1.24.0"
export NGINX_DOWNLOAD_URL="http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz"
export NGINX_WORKER_PROCESSES=4
export NGINX_CPU_AFFINITY="0-3"

# --- WRK 基准测试工具配置 ---
export WRK_VERSION="4.1.0"
#export WRK_DOWNLOAD_URL="https://github.com/wg/wrk.git"
export WRK_DOWNLOAD_URL="http://gitlab.youtune.tech/pymirror/wrk.git"

export WRK_THREADS=4
export WRK_CONNECTIONS=100
export WRK_DURATION="30s"
export WRK_CPU_AFFINITY="4-7"
export WRK_TARGET_URL="http://localhost:8000/"

# --- 输出目录 ---
export NGINX_OUTPUT_DIR="$BASE_DIR/output"

# --- 服务用户 (通常为当前用户) ---
export SERVICE_USER="$(whoami)"
