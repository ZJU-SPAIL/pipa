#!/bin/bash
set -e
# -----------------------------------------------------------------------------
# 软件环境自动化安装脚本 (含源码编译)
# -----------------------------------------------------------------------------

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

log_info ">>> 开始执行软件安装流程 <<<"

# 1. 依赖安装
log_info "正在通过系统包管理器安装编译依赖..."
sudo yum install -y pcre-devel zlib-devel openssl-devel git gcc make wget gnutls-devel libev-devel

# 2. 目录初始化
mkdir -p "$BASE_DIR/src" "$NGINX_INSTALL_DIR" "$TOOLS_DIR/bin"

# 3. Nginx 1.19.0 源码下载与编译
cd "$BASE_DIR/src"
if [ ! -f "nginx-${NGINX_VERSION}.tar.gz" ]; then
    log_info "正在下载 Nginx ${NGINX_VERSION} 源码..."
    wget -q "$NGINX_DOWNLOAD_URL"
fi

if [ ! -d "nginx-${NGINX_VERSION}" ]; then
    tar -zxf "nginx-${NGINX_VERSION}.tar.gz"
fi

cd "nginx-${NGINX_VERSION}"
if [ ! -f "$NGINX_INSTALL_DIR/sbin/nginx" ]; then
    log_info "正在配置并编译 Nginx (鲲鹏架构优化)..."
    ./configure \
        --prefix="$NGINX_INSTALL_DIR" \
        --with-http_stub_status_module \
        --with-http_ssl_module \
        --with-file-aio \
        --with-threads

    make -j$(nproc)
    make install
    log_info "✅ Nginx 安装完成。"
fi

# 4. WRK 编译安装 (禹调科技镜像源)
cd "$BASE_DIR/src"
if [ ! -d "wrk" ]; then
    log_info "正在从镜像站克隆 WRK 源码..."
    git clone "$WRK_REPO_URL" wrk
fi
cd wrk
if [ ! -f "$TOOLS_DIR/bin/wrk" ]; then
    log_info "正在编译 WRK..."
    make -j$(nproc)
    cp wrk "$TOOLS_DIR/bin/"
    log_info "✅ WRK 安装完成。"
fi

# 5. httpress 编译安装 (禹调科技镜像源)
cd "$BASE_DIR/src"
if [ ! -d "httpress" ]; then
    log_info "正在从镜像站克隆 httpress 源码..."
    git clone "$HTTPRESS_REPO_URL" httpress
fi
cd httpress
if [ ! -f "$TOOLS_DIR/bin/httpress" ]; then
    log_info "正在编译 httpress..."
    make -j$(nproc)
    cp bin/Release/httpress "$TOOLS_DIR/bin/"
    log_info "✅ httpress 安装完成。"
fi

log_info "🏆 所有软件环境安装成功。"
