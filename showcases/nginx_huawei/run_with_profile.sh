#!/bin/bash
set -e
# -----------------------------------------------------------------------------
# 场景执行引擎 (Profile Runner)
# -----------------------------------------------------------------------------
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../" && pwd)

# 加载全局环境
source "$SCRIPT_DIR/env.sh"

PROFILE=$1
if [ -z "$PROFILE" ]; then
    echo "Usage: $0 <profile_name>"
    echo "Available: wrk_long, wrk_short, httpress_long, httpress_short"
    exit 1
fi

PROFILE_ENV="$SCRIPT_DIR/profiles/$PROFILE/env.sh"
if [ ! -f "$PROFILE_ENV" ]; then
    echo "❌ Profile not found: $PROFILE"
    exit 1
fi

# 加载场景环境
source "$PROFILE_ENV"

PIPA_CMD="$PROJECT_ROOT/.venv/bin/pipa"
SCENARIO_NAME="nginx_${PROFILE}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EVIDENCE_DIR="$EVIDENCE_ROOT/${TIMESTAMP}_${SCENARIO_NAME}"
mkdir -p "$EVIDENCE_DIR"

log() { echo "[Runner:$PROFILE] $1"; }

# 清理钩子
cleanup() {
    log "Cleaning up..."
    "$SCRIPT_DIR/stop_nginx.sh" >/dev/null 2>&1
}
trap cleanup EXIT

log ">>> 开始执行场景: $PROFILE <<<"
log "工具: $TOOL | 模式: $MODE | Evidence: $EVIDENCE_DIR"

# --- 1. 修复报错：强制重建日志目录 ---
mkdir -p "$NGINX_LOGS_DIR"
touch "$NGINX_LOGS_DIR/error.log" "$NGINX_LOGS_DIR/access.log"

# --- 2. 渲染 Nginx 配置 (根据场景动态调整 Keepalive) ---
log "Rendering Nginx config (Keepalive: ${KEEPALIVE_TIMEOUT}s)..."
envsubst '${NGINX_WORKER_COUNT} ${NGINX_CPU_AFFINITY_MASK} ${NGINX_LOGS_DIR} ${KEEPALIVE_TIMEOUT} ${KEEPALIVE_REQUESTS}' < "$SHOWCASE_DIR/config/nginx_base.conf.template" > "$NGINX_INSTALL_DIR/conf/nginx.conf"

# --- 3. 启动 Nginx ---
log "Starting Nginx..."
"$SCRIPT_DIR/start_nginx.sh"
# 获取 PID 用于 PIPA
NGINX_PIDS=$(pgrep -f "nginx: worker" | tr '\n' ',' | sed 's/,$//')

# --- 4. 启动负载 ---
log "Starting Load Generator ($TOOL)..."
"$SCRIPT_DIR/run_load.sh" "$TOOL" "$MODE" > "$EVIDENCE_DIR/load.log" 2>&1 &
LOAD_PID=$!
log "   -> PID: $LOAD_PID, Logs: load.log"

# --- 5. PIPA 采样 ---
log "PIPA Sampling..."
$PIPA_CMD sample \
    --attach-to-pid "$NGINX_PIDS" \
    --duration-stat "$DURATION_STAT" \
    --duration-record "$DURATION_RECORD" \
    --output "$EVIDENCE_DIR/snapshot.pipa"

# --- 6. 分析报告 ---
log "Generating Report..."
$PIPA_CMD analyze \
    --input "$EVIDENCE_DIR/snapshot.pipa" \
    --output "$EVIDENCE_DIR/report.html" \
    --expected-cpus "$NGINX_PIPA_EXPECTED_CPUS"

# ==============================================================================
# [新增] 等待压测工具自然结束，以获取 RPS 统计日志
# ==============================================================================
log "⏳ Waiting for Load Generator to finish naturally (getting RPS stats)..."
wait $LOAD_PID || true
log "   -> Load Generator finished."

# --- 7. 留痕 ---
cp "$PROFILE_ENV" "$EVIDENCE_DIR/profile.sh"
cp "$NGINX_INSTALL_DIR/conf/nginx.conf" "$EVIDENCE_DIR/nginx_running.conf"

log "✅ 场景执行完毕！"
