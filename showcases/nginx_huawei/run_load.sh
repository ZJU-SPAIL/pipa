#!/bin/bash
set -e
# -----------------------------------------------------------------------------
# 负载生成器 - 修复版 (强制参数检查)
# -----------------------------------------------------------------------------
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

TOOL=$1 # [wrk|httpress]
MODE=$2 # [short|long]

if [[ -z "$TOOL" || -z "$MODE" ]]; then
    echo "[LoadGen] ❌ Error: Usage: $0 [wrk|httpress] [short|long]"
    exit 1
fi

log_info() { echo "[LoadGen] $1"; }

# 施压端核心绑定策略
CPU_BIND="taskset -c $LOAD_GEN_CPU_AFFINITY"

# --- 核心修复：明确变量映射 ---
if [ "$MODE" == "short" ]; then
    DURATION=$LOAD_SHORT_DURATION
    CONNS=$LOAD_SHORT_CONN
else
    DURATION=$LOAD_LONG_DURATION
    CONNS=$LOAD_LONG_CONN
fi

log_info "配置检查: 工具=$TOOL, 模式=$MODE, 时长=$DURATION, 连接数=$CONNS"

if [ "$TOOL" == "wrk" ]; then
    BIN="$TOOLS_DIR/bin/wrk"
    if [ "$MODE" == "short" ]; then
        # 短连接
        CMD="$CPU_BIND $BIN -t12 -c$CONNS -d$DURATION -H \"Connection: close\" $TARGET_URL"
    else
        # 长连接
        CMD="$CPU_BIND $BIN -t12 -c$CONNS -d$DURATION $TARGET_URL"
    fi

    log_info "执行命令: $CMD"
    eval $CMD

elif [ "$TOOL" == "httpress" ]; then
    BIN="$TOOLS_DIR/bin/httpress"
    # 给一个巨大的请求数，保证它不会提前跑完
    HUGE_REQUESTS=1000000000

    # [核心修复] 使用 timeout 命令强制控制时长！
    # 格式: timeout -s SIGINT <秒数> <命令>
    # 发送 SIGINT (Ctrl+C) 信号，这样 httpress 还能打印出最后的统计数据

    # 这里的 DURATION 变量已经是 "140s" 这种格式了，timeout 命令需要纯数字
    # 去掉 's' 后缀
    TIME_LIMIT=$(echo $DURATION | tr -d 's')

    if [ "$MODE" == "short" ]; then
        # 短连接
        CMD="timeout -s SIGINT $TIME_LIMIT $CPU_BIND $BIN -n $HUGE_REQUESTS -c $CONNS -t 12 $TARGET_URL"
    else
        # 长连接
        CMD="timeout -s SIGINT $TIME_LIMIT $CPU_BIND $BIN -n $HUGE_REQUESTS -c $CONNS -t 12 -k $TARGET_URL"
    fi

    log_info "执行命令 (带超时控制): $CMD"
    eval $CMD

    # timeout 如果杀掉了进程，返回码是 124，我们把它视为正常
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        log_info "✅ Httpress 达到时间限制，已停止。"
    elif [ $EXIT_CODE -eq 0 ]; then
        log_info "✅ Httpress 提前完成任务。"
    else
        log_info "⚠️ Httpress 异常退出 (Code: $EXIT_CODE)"
    fi
fi
