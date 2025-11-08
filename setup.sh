#!/bin/bash

# ===================================================================
# pipa 项目环境自动化配置脚本 (v2)
# 优先使用系统 Python (>=3.9)，失败则回退到源码编译。
# ===================================================================

# --- 配置区 ---
MIN_PYTHON_VERSION="3.9"
COMPILE_PYTHON_VERSION="3.11.12"
VENV_DIR="./.venv"

# 编译 Python 所需的核心依赖包列表 (适用于 OpenEuler / DNF/YUM)
REQUIRED_DEPS=(
    "gcc" "zlib-devel" "bzip2-devel" "openssl-devel"
    "libffi-devel" "readline-devel" "sqlite-devel"
    "make" "xz-devel"
)
# --- 配置区结束 ---

# --- 信号捕获与清理 ---
cleanup() {
    EXIT_CODE=$?
    echo ""
    if [ "$EXIT_CODE" -ne 0 ]; then
        echo "--- 脚本因错误退出，执行清理 ---"
    fi
    if [ -d "Python-${COMPILE_PYTHON_VERSION}" ]; then
        rm -rf "Python-${COMPILE_PYTHON_VERSION}"
    fi
    if [ -f "/tmp/Python-${COMPILE_PYTHON_VERSION}.tar.xz" ]; then
        rm -f "/tmp/Python-${COMPILE_PYTHON_VERSION}.tar.xz"
    fi
}
trap cleanup EXIT INT

# --- 核心逻辑函数 ---

# 检查系统 Python 版本是否满足要求
check_system_python() {
    echo "--- 1. 检查系统 Python 环境 ---"
    if ! command -v python3 &>/dev/null; then
        echo "未找到 'python3' 命令。将尝试编译 Python ${COMPILE_PYTHON_VERSION}。"
        return 1
    fi

    SYSTEM_PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "检测到系统 Python 版本: ${SYSTEM_PYTHON_VERSION}"

    # 使用 sort -V 进行版本比较
    if printf '%s\n' "$MIN_PYTHON_VERSION" "$SYSTEM_PYTHON_VERSION" | sort -V -C; then
        echo "系统 Python 版本满足 >= ${MIN_PYTHON_VERSION} 的要求。将使用系统 Python。"
        return 0
    else
        echo "系统 Python 版本低于要求。将尝试编译 Python ${COMPILE_PYTHON_VERSION}。"
        return 1
    fi
}

# 编译 Python 的逻辑
compile_and_install_python() {
    echo -e "\n--- 2. 编译安装 Python ${COMPILE_PYTHON_VERSION} ---"
    SOURCE_TARBALL="Python-${COMPILE_PYTHON_VERSION}.tar.xz"
    HUAWEI_DOWNLOAD_URL="https://mirrors.huaweicloud.com/python/${COMPILE_PYTHON_VERSION}/${SOURCE_TARBALL}"
    DOWNLOAD_TARGET="/tmp/${SOURCE_TARBALL}"

    # 自动安装依赖
    if command -v dnf &>/dev/null; then
        echo "使用 dnf 自动安装编译依赖..."
        sudo dnf install -y "${REQUIRED_DEPS[@]}"
    elif command -v yum &>/dev/null; then
        echo "使用 yum 自动安装编译依赖..."
        sudo yum install -y "${REQUIRED_DEPS[@]}"
    else
        echo "警告: 未找到 dnf 或 yum，请手动确保编译依赖已安装。"
    fi

    # 下载
    if [ ! -f "$DOWNLOAD_TARGET" ]; then
        echo "从华为云镜像下载源码..."
        curl -L "$HUAWEI_DOWNLOAD_URL" -o "$DOWNLOAD_TARGET" || { echo "下载失败"; exit 1; }
    fi

    # 编译和安装
    tar -xf "$DOWNLOAD_TARGET"
    pushd "Python-${COMPILE_PYTHON_VERSION}" || exit 1
    ./configure --prefix="$(pwd)/../.python_base_${COMPILE_PYTHON_VERSION}"
    make -j "$(nproc)" && make install
    if [ $? -ne 0 ]; then
        echo "Python 编译或安装失败。"
        exit 1
    fi
    popd
    # 返回新编译的 Python 执行路径
    echo "$(pwd)/.python_base_${COMPILE_PYTHON_VERSION}/bin/python${MIN_PYTHON_VERSION%.*}"
}


# --- 主执行流程 ---

PYTHON_EXECUTABLE="python3"
if ! check_system_python; then
    PYTHON_EXECUTABLE=$(compile_and_install_python)
    if [ ! -x "$PYTHON_EXECUTABLE" ]; then
        echo "致命错误：无法确定可用的 Python 执行文件。"
        exit 1
    fi
fi

echo -e "\n--- 3. 创建 venv 虚拟环境 ---"
rm -rf "$VENV_DIR"
"$PYTHON_EXECUTABLE" -m venv "$VENV_DIR" || { echo "创建 venv 失败"; exit 1; }

echo "--- 4. 激活环境并安装依赖 ---"
source "$VENV_DIR/bin/activate"

echo "当前 Python 版本:"
python --version

echo "正在以可编辑模式安装项目..."
pip install -e .
if [ $? -ne 0 ]; then
    echo "警告: 依赖安装失败。请检查 pyproject.toml 文件和网络。"
fi

echo "====================================================="
echo "✅ 配置成功！项目级环境 '$VENV_DIR' 已创建并配置。"
echo "请运行 'source $VENV_DIR/bin/activate' 来激活环境。"
echo "====================================================="
