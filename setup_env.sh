#!/bin/bash

# ===================================================================
# Python 3.11.12 项目环境自动化配置脚本 (增强鲁棒性 & OpenEuler 兼容)
# 源码下载至 /tmp 目录
# ===================================================================

# --- 配置区 ---
PYTHON_VERSION="3.11.12"
SOURCE_TARBALL="Python-${PYTHON_VERSION}.tar.xz"
HUAWEI_DOWNLOAD_URL="https://mirrors.huaweicloud.com/python/${PYTHON_VERSION}/${SOURCE_TARBALL}"

# 下载目录设置为 /tmp
DOWNLOAD_DIR="/tmp"

# 隔离的本地安装目录 (此目录必须保留，作为 venv 的基础)
INSTALL_BASE_DIR="./.python_base_${PYTHON_VERSION}"

# 最终虚拟环境目录
VENV_DIR="./.venv"
SOURCE_DIR="Python-${PYTHON_VERSION}"

# 编译 Python 3.11 所需的核心依赖包列表 (适用于 OpenEuler / DNF/YUM)
REQUIRED_DEPS=(
    "gcc" "zlib-devel" "bzip2-devel" "openssl-devel" 
    "libffi-devel" "readline-devel" "sqlite-devel" 
    "make" "xz-devel"
)
# --- 配置区结束 ---

# ===================================================================
# 鲁棒性增强：清理函数和信号捕获
# ===================================================================

cleanup() {
    EXIT_CODE=$?
    echo ""
    echo "--- 执行退出清理 ---"
    
    # 确保退出 venv (如果激活了)
    if [ -n "$VIRTUAL_ENV" ] && [ "$VIRTUAL_ENV" != "/" ]; then
        deactivate 2>/dev/null
    fi

    # 清理源码目录 (无论成功失败，都清理解压后的源码目录)
    if [ -d "$SOURCE_DIR" ]; then
        echo "清理解压后的源码目录: $SOURCE_DIR"
        rm -rf "$SOURCE_DIR"
    fi

    # 清理 /tmp 中的下载文件
    DOWNLOADED_FILE="$DOWNLOAD_DIR/$SOURCE_TARBALL"
    if [ -f "$DOWNLOADED_FILE" ]; then
        echo "清理下载文件: $DOWNLOADED_FILE"
        rm -f "$DOWNLOADED_FILE"
    fi

    # 关键修复: 只有在脚本非正常退出时，才清理 INSTALL_BASE_DIR
    if [ $EXIT_CODE -ne 0 ]; then
        if [ -d "$INSTALL_BASE_DIR" ]; then
            echo "脚本失败，清理本地安装基础目录: $INSTALL_BASE_DIR"
            rm -rf "$INSTALL_BASE_DIR"
        fi
        echo "脚本因错误或中断退出 (Exit Code: $EXIT_CODE)"
    else
        echo "临时编译文件清理完成. 项目基础环境 $INSTALL_BASE_DIR 已保留"
    fi
}

# 注册 trap: 捕获 EXIT (正常或非零退出) 和 INT (Ctrl+C) 信号
trap cleanup EXIT INT

# ===================================================================
# OpenEuler 兼容性函数
# ===================================================================

detect_pkg_manager() {
    if command -v dnf &> /dev/null; then
        echo "dnf"
    elif command -v yum &> /dev/null; then
        echo "yum"
    else
        echo ""
    fi
}

check_and_install_dependencies() {
    echo "--- 1.1 检查编译依赖 ---"
    
    PACKAGE_MANAGER=$(detect_pkg_manager)
    if [ -z "$PACKAGE_MANAGER" ]; then
        echo "错误: 未找到 dnf 或 yum 包管理器. 请手动安装依赖"
        return 1
    fi

    MISSING_DEPS=()
    for dep in "${REQUIRED_DEPS[@]}"; do
        if ! rpm -q "$dep" &> /dev/null; then
            MISSING_DEPS+=("$dep")
        fi
    done

    if [ ${#MISSING_DEPS[@]} -eq 0 ]; then
        echo "所有必需的编译依赖项已安装. 继续..."
        return 0
    else
        echo "检测到以下缺失的编译依赖项:"
        echo "${MISSING_DEPS[@]}"
        echo ""
        
        read -r -p "是否尝试使用 'sudo $PACKAGE_MANAGER install' 安装这些依赖? (y/N): " response
        response=${response,,}

        if [[ "$response" =~ ^(yes|y)$ ]]; then
            echo "正在尝试安装缺失依赖..."
            sudo "$PACKAGE_MANAGER" groupinstall "Development Tools" -y 2>/dev/null
            sudo "$PACKAGE_MANAGER" install -y "${MISSING_DEPS[@]}"

            if [ $? -ne 0 ]; then
                echo "致命错误: 依赖安装失败. 请手动解决或检查内部源配置"
                return 1
            fi
            echo "依赖安装完成."
            return 0
        else
            echo "警告: 用户选择跳过依赖安装. 如果编译失败，请手动安装缺失依赖"
            return 0
        fi
    fi
}


echo "--- 1. 启动配置流程 ---"

# 1.1 依赖检查与安装
check_and_install_dependencies || exit 1


echo "--- 1.2 检查和下载源码 ---"

# 检查下载工具
if ! command -v wget &> /dev/null && ! command -v curl &> /dev/null; then
    echo "错误: 未找到下载工具 (wget 或 curl). 请先安装"
    exit 1
fi

# 尝试下载源码包到 /tmp
DOWNLOAD_TARGET="$DOWNLOAD_DIR/$SOURCE_TARBALL"
if [ ! -f "$DOWNLOAD_TARGET" ]; then
    echo "尝试从华为云镜像下载 Python $PYTHON_VERSION 源码包到 $DOWNLOAD_DIR ..."
    if command -v curl &> /dev/null; then
        curl -L "$HUAWEI_DOWNLOAD_URL" -o "$DOWNLOAD_TARGET"
    elif command -v wget &> /dev/null; then
        wget "$HUAWEI_DOWNLOAD_URL" -O "$DOWNLOAD_TARGET"
    fi

    if [ $? -ne 0 ]; then
        echo "致命错误: 自动下载 $SOURCE_TARBALL 失败. 请检查您的网络是否能访问华为云镜像"
        exit 1
    fi
    echo "源码包下载成功: $DOWNLOAD_TARGET"
else
    echo "源码包 $DOWNLOAD_TARGET 已存在，跳过下载步骤"
fi

# 确保在开始解压前没有残留的旧目录
rm -rf "$SOURCE_DIR" "$INSTALL_BASE_DIR"


echo "--- 2. 解压源码 ---"
# 在当前项目目录下解压源码，但源文件在 /tmp
tar -xf "$DOWNLOAD_TARGET"
cd "$SOURCE_DIR" || exit 1

# 获取当前项目绝对路径 (重要)
PROJECT_ROOT=$(pwd)/..
echo "--- 3. 配置编译参数 ---"
# 为了鲁棒性和速度，移除 --enable-optimizations
./configure --prefix="$PROJECT_ROOT/$INSTALL_BASE_DIR"
if [ $? -ne 0 ]; then
    echo "配置失败"
    exit 1
fi


echo "--- 4. 编译 Python 解释器 ---"
make -j $(nproc)
if [ $? -ne 0 ]; then
    echo "编译失败"
    exit 1
fi


echo "--- 5. 本地安装 ---"
make install
if [ $? -ne 0 ]; then
    echo "本地安装失败"
    exit 1
fi

# 返回项目根目录
cd ..


echo "--- 6. 创建 venv 虚拟环境 ---"
rm -rf "$VENV_DIR"
PYTHON_EXECUTABLE="$INSTALL_BASE_DIR/bin/python3.11"
$PYTHON_EXECUTABLE -m venv --copies "$VENV_DIR"
if [ $? -ne 0 ]; then
    echo "venv 环境创建失败"
    exit 1
fi


echo "--- 7. 验证环境 ---"
source "$VENV_DIR/bin/activate"
echo "环境已激活. 当前 Python 版本:"
python --version


echo "--- 8. 安装项目依赖 ---"
# 如果失败，只会给出警告
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "警告: 依赖安装失败. 请检查 requirements.txt 文件和网络"
fi

echo "=========================================="
echo "配置成功. 项目级环境 $VENV_DIR 已创建"
echo "请使用 'source $VENV_DIR/bin/activate' 激活"
echo "=========================================="

# 脚本正常退出，trap 会处理最终清理