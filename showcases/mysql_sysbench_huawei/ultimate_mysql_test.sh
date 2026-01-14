#!/bin/bash
# 包装脚本：运行 MySQL 终极测试，默认使用 baseline 配置
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
./run_with_profile.sh baseline
