#!/bin/bash
# showcases/mysql/run_with_profile.sh - 纯粹的实验执行脚本
set -e

# ==================== 路径锚定与环境检查 ====================
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../" && pwd)

VENV_ACTIVATE="$PROJECT_ROOT/.venv/bin/activate"
if [ -f "$VENV_ACTIVATE" ]; then
    source "$VENV_ACTIVATE"
fi
source "$SCRIPT_DIR/env.sh"
if ! command -v pipa &> /dev/null; then echo "❌ 致命错误: 未找到 'pipa' 命令！" >&2; exit 127; fi
if ! command -v envsubst &> /dev/null; then echo "❌ 致命错误: 未找到 'envsubst' 命令！" >&2; exit 127; fi

SAFETY_GUARD_SCRIPT="$PROJECT_ROOT/showcases/safety-guard.sh"
if [ -f "$SAFETY_GUARD_SCRIPT" ]; then
    source "$SAFETY_GUARD_SCRIPT"
fi
# ===============================================================

# ==================== Trap (仅中断时强制清理) ====================
cleanup_force() {
    echo -e "\n🛑 实验中断，执行强制清理..."
    "$SCRIPT_DIR/stop_mysql_force.sh"
}
trap cleanup_force INT TERM
# ===============================================================

PROFILE=${1:-baseline}
PROFILE_DIR="$SCRIPT_DIR/profiles/$PROFILE"
if [ ! -d "$PROFILE_DIR" ]; then echo "❌ 错误: Profile '$PROFILE' 不存在。" >&2; exit 1; fi

echo "🎬 PIPA 实验开始: $PROFILE"

echo "[实验] [阶段 1] 检查数据集..."
if [ ! -d "$MYSQL_DATA_DIR/sbtest" ]; then
    echo "❌ 错误: 数据集不存在！请先运行 'force_rebuild.sh' 进行一次性数据准备。"
    exit 1
fi

# 加载配置
source "$SCRIPT_DIR/env.sh"
source "$PROFILE_DIR/env.sh"
RUN_LUA_SCRIPT="$SYSBENCH_LUA_DIR/${SYSBENCH_LUA}.lua"
echo "📝 实验描述: $DESCRIPTION"

echo "[实验] [阶段 2] 启动实验实例 ('$PROFILE')..."
envsubst < "$SCRIPT_DIR/config/my.cnf.template" > "$MYSQL_INSTALL_DIR/etc/my.cnf"
"$SCRIPT_DIR/start_mysql.sh"
MYSQL_PID=$(pgrep -x mysqld)

echo "[实验] [阶段 3] 运行负载并采样..."
EVIDENCE_DIR="$PROJECT_ROOT/evidence/$(date +%Y%m%d_%H%M%S)_${PROFILE}"
mkdir -p "$EVIDENCE_DIR"
ulimit -n 65535 || echo "⚠️ 警告: 提升 ulimit -n 失败。"

LD_LIBRARY_PATH="$MYSQL_INSTALL_DIR/lib" "$SYSBENCH_INSTALL_DIR/bin/sysbench" "$RUN_LUA_SCRIPT" --mysql-socket="$MYSQL_SOCKET_PATH" --mysql-user=root --tables="$SYSBENCH_TABLES" --table-size="$SYSBENCH_TABLE_SIZE" --report-interval=1 --threads="$SYSBENCH_THREADS" --time=300 run > "$EVIDENCE_DIR/sysbench.log" &
SYSBENCH_PID=$!
echo "   -> 负载已启动 (PID: $SYSBENCH_PID)，等待 10 秒预热..."
sleep 10
if ! kill -0 $SYSBENCH_PID 2>/dev/null; then
    echo "❌ 致命错误: Sysbench 进程已过早退出！" >&2
    tail -n 10 "$EVIDENCE_DIR/sysbench.log"
    exit 1
fi

pipa -vv sample --attach-to-pid "$MYSQL_PID" --duration-stat 60 --duration-record 60 --output "$EVIDENCE_DIR/snapshot.pipa"

echo "[实验] [阶段 4] 分析并归档证据..."
pipa analyze --input "$EVIDENCE_DIR/snapshot.pipa" --output "$EVIDENCE_DIR/report.html" --expected-cpus "$MYSQL_CPU_AFFINITY"
cp "$PROFILE_DIR/env.sh" "$EVIDENCE_DIR/profile_env.sh"
cp "$MYSQL_INSTALL_DIR/etc/my.cnf" "$EVIDENCE_DIR/actual_my.cnf"

# --- 实验结束后的优雅关停 ---
echo "🏁 实验完成！正在执行优雅关停..."
"$SCRIPT_DIR/stop_mysql_graceful.sh"

echo "证据保存于: $EVIDENCE_DIR"
