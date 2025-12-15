#!/bin/bash
set -e
# -----------------------------------------------------------------------------
# 终极测试入口 - 默认执行 wrk_long (华为基线场景)
# -----------------------------------------------------------------------------
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

# 确保有执行权限
chmod +x "$SCRIPT_DIR/run_with_profile.sh"

# 默认跑 wrk 长连接
"$SCRIPT_DIR/run_with_profile.sh" wrk_long
