#!/usr/bin/env bash

set -e
set -o pipefail

# =================================================================
# Pipa Showcase: 运行 Nginx 性能基准测试和性能数据收集 (已修复)
# 职责: 启动 WRK 基准测试，同时正确地收集 Nginx 进程的系统性能指标。
# =================================================================

# 获取脚本自身所在的目录
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source "$SCRIPT_DIR/env.sh"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - $1"
}

log "启动 Nginx 基准测试和性能数据收集..."
log "重要: 请确保 Nginx 服务器正在运行。使用 ./start_nginx_server.sh 启动"

CSV_FILE="$NGINX_OUTPUT_DIR/nginx_performance_data.csv"
TMP_DIR="$NGINX_OUTPUT_DIR/tmp"

declare -a SCRIPT_PIDS=()
mkdir -p "$NGINX_OUTPUT_DIR" "$TMP_DIR"

cleanup() {
    log "清理临时文件和后台进程..."
    rm -rf "$TMP_DIR"
    if [ ${#SCRIPT_PIDS[@]} -gt 0 ]; then
        kill "${SCRIPT_PIDS[@]}" 2>/dev/null || true
    fi
    log "✅ 清理完成。"
}
trap cleanup EXIT

# 保持原始的 CSV 文件头
echo "User,System,Total,IRQ,SoftIRQ,Cycles,Instructions,Branch,BranchMisses,stalled-cycles-frontend,stalled-cycles-backend,mem_access,remote_access,Context_Switches,L1D_Access,L1D_Refill,L1D_TLB_Access,L1D_TLB_Refill,L1I_Access,L1I_Refill,L1I_TLB_Access,L1I_TLB_Refill,L2D_Access,L2D_Refill,L2D_TLB_Access,L2D_TLB_Refill,L2I_Access,L2I_Refill,L2I_TLB_Access,L2I_TLB_Refill,LLC_Misses,LLC_Loads,nonvoluntary_ctxt_switches,Latency,ReqSec" > "$CSV_FILE"

log "开始收集 10 轮测试数据..."

for i in {1..10}; do
    log "--- 开始第 $i 轮 ---"

    wrk_output_file="$TMP_DIR/wrk_output_${i}.log"
    log "启动 WRK 基准测试..."
    taskset -c "$WRK_CPU_AFFINITY" "$WRK_INSTALL_DIR/bin/wrk" \
        -t"$WRK_THREADS" -c"$WRK_CONNECTIONS" -d"$WRK_DURATION" \
        -H "Connection: keep-alive" "$WRK_TARGET_URL" > "$wrk_output_file" &
    WRK_PID=$!
    SCRIPT_PIDS+=($!)

    sleep 2
    collection_interval=10

    # ========================== 核心修复区 START ==========================

    # 1. 新增：获取 Nginx worker 进程的 PIDs
    NGINX_WORKER_PIDS=$(pgrep -f "nginx: worker process" | tr '\n' ',' | sed 's/,$//')
    if [ -z "$NGINX_WORKER_PIDS" ]; then
        log "❌ 错误: 在第 $i 轮未找到 Nginx worker 进程！跳过此轮。"
        wait $WRK_PID
        continue
    fi
    log "   -> 本轮监控的 Nginx worker PIDs: $NGINX_WORKER_PIDS"

    # ========================== 核心修复区 END ==========================

    sar_tmp="$TMP_DIR/sar.tmp"
    mpstat_tmp="$TMP_DIR/mpstat.tmp"
    perf_tmp1="$TMP_DIR/perf_1.tmp"

    declare -a local_pids=()

    # sar 和 mpstat 的 -P 参数是针对 CPU 核心的，用法正确，无需修改
    sar -P "$NGINX_CPU_AFFINITY" -u 1 "$collection_interval" > "$sar_tmp" &
    local_pids+=($!); SCRIPT_PIDS+=($!)
    mpstat -P "$NGINX_CPU_AFFINITY" 1 "$collection_interval" > "$mpstat_tmp" &
    local_pids+=($!); SCRIPT_PIDS+=($!)

    # 2. 核心修复：使用 -p 参数将 perf stat 附加到 Nginx PIDs 上，而不是监控 sleep
    perf stat -p "$NGINX_WORKER_PIDS" -e cycles,instructions,branch-loads,branch-misses,mem_access,remote_access,cs,stalled-cycles-backend,stalled-cycles-frontend,l1d_cache,l1d_cache_refill,l1d_tlb,l1d_tlb_refill,l1i_cache,l1i_cache_refill,l1i_tlb,l1i_tlb_refill,l2d_cache,l2d_cache_refill,l2d_tlb,l2d_tlb_refill,l2i_cache,l2i_cache_refill,l2i_tlb,l2i_tlb_refill,LLC-load-misses,LLC-loads sleep "$collection_interval" > "$perf_tmp1" 2>&1 &
    local_pids+=($!); SCRIPT_PIDS+=($!)

    PIDS=$(pgrep nginx | grep -v master)
    cont1=0
    for pid in $PIDS; do
        val=$(grep nonvoluntary_ctxt_switches "/proc/$pid/status" 2>/dev/null | awk '{print $2}' || echo "0")
        cont1=$((cont1 + val))
    done

    log "等待监控工具完成..."
    wait "${local_pids[@]}"

    cont2=0
    for pid in $PIDS; do
        val=$(grep nonvoluntary_ctxt_switches "/proc/$pid/status" 2>/dev/null | awk '{print $2}' || echo "0")
        cont2=$((cont2 + val))
    done

    log "提取和处理数据..."
    # 以下数据提取逻辑保持不变
    sar_data=$(awk '/^Average:/ {count++; use+=$3; sys+=$5; idl+=$8} END {if(count>0) printf "%.2f,%.2f,%.2f", use/count, sys/count, 100-idl/count}' "$sar_tmp")
    mpstat_data=$(awk '/^Average:/ {count++; irq+=$7; soft+=$8} END {if(count>0) printf "%.2f,%.2f", irq/count, soft/count}' "$mpstat_tmp")
    perf_data_all=$(awk 'function cn(str){gsub(/,/,"",str); return str+0} $2 == "cycles" {cy=cn($1)} $2 == "instructions" {ins=cn($1)} $2 == "branch-loads" {bl=cn($1)} $2 == "branch-misses" {bm=cn($1)} $2 == "stalled-cycles-frontend" {scf=cn($1)} $2 == "stalled-cycles-backend" {scb=cn($1)} $2 == "mem_access" {ma=cn($1)} $2 == "remote_access" {ra=cn($1)} $2 == "cs" {cstotal=cn($1)} /l1d_cache / {l1d=cn($1)} /l1d_cache_refill/ {l1dr=cn($1)} /l1d_tlb / {l1dt=cn($1)} /l1d_tlb_refill/ {l1dtr=cn($1)} /l1i_cache / {l1i=cn($1)} /l1i_cache_refill/ {l1ir=cn($1)} /l1i_tlb / {l1it=cn($1)} /l1i_tlb_refill/ {l1itr=cn($1)} /l2d_cache / {l2d=cn($1)} /l2d_cache_refill/ {l2dr=cn($1)} /l2d_tlb / {l2dt=cn($1)} /l2d_tlb_refill/ {l2dtr=cn($1)} /l2i_cache / {l2i=cn($1)} /l2i_cache_refill/ {l2ir=cn($1)} /l2i_tlb / {l2it=cn($1)} /l2i_tlb_refill/ {l2itr=cn($1)} /LLC-load-misses/ {llcm=cn($1)} /LLC-loads/ {llcl=cn($1)} END {printf "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d", cy,ins,bl,bm,scf,scb,ma,ra,cstotal,l1d,l1dr,l1dt,l1dtr,l1i,l1ir,l1it,l1itr,l2d,l2dr,l2dt,l2dtr,l2i,l2ir,l2it,l2itr,llcm,llcl}' "$perf_tmp1")
    switch_data=$(($cont2-$cont1))

    wait $WRK_PID
    wrk_data=$(awk '/Latency/ {lat=$2} /Req\/Sec/ {req=$2} END {print lat","req}' "$wrk_output_file")

    echo "$sar_data,$mpstat_data,$perf_data_all,$switch_data,$wrk_data" >> "$CSV_FILE"
    log "第 $i 轮数据已附加到 CSV。"

    rm -f "$TMP_DIR"/*
    log "清理 Nginx 访问日志..."
    : > "$NGINX_LOGS_DIR/access.log"
done

log "✅ 基准测试和数据收集完成。"
log "   结果文件: $CSV_FILE"
