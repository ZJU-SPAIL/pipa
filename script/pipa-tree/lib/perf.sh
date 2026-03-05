#!/usr/bin/env bash
# Perf stat and record module

# Source common functions
source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${source_dir}/common.sh"

# Global variable for perf event groups
PERF_EVENT_GROUPS=()
# Shared last background PID variable
LAST_BG_PID=""
# Sudo prefix for perf commands (always use sudo)
PERF_SUDO="sudo"

prepare_perf_output_file() {
  local output_file="$1"
  if [[ -z "$output_file" ]]; then
    return
  fi

  local output_dir
  output_dir=$(dirname "$output_file")
  mkdir -p "$output_dir"
  : >"$output_file"
  chmod 0644 "$output_file"
}

select_perf_event_groups() {
  local override="$1"
  local arch=$(uname -m)
  PERF_EVENT_GROUPS=()
  if [[ -n "$override" ]]; then
    PERF_EVENT_GROUPS=("$override")
    return
  fi
  case "$arch" in
    aarch64)
      PERF_EVENT_GROUPS=(
        "cpu-cycles,instructions"
        "branch-misses"
        "l1d_cache,l1d_cache_refill"
        "l2d_cache,l2d_cache_refill"
        "ll_cache_rd,ll_cache_miss_rd"
        "dTLB-load-misses,iTLB-load-misses"
        "page-faults,context-switches,cpu-migrations"
      )
      ;;
    *)
      PERF_EVENT_GROUPS=(
        "cycles,instructions"
        "cache-references,cache-misses"
        "branch-instructions,branch-misses"
        "L1-dcache-loads,L1-dcache-load-misses"
        "LLC-loads,LLC-load-misses"
        "dTLB-loads,dTLB-load-misses"
        "iTLB-loads,iTLB-load-misses"
        "page-faults,context-switches,cpu-migrations"
      )
      ;;
  esac
}

start_perf_stat_job() {
  local duration="$1"
  local interval="$2"
  local output_file="$3"
  local metrics="backend_bound,frontend_bound,retiring,bad_speculation"
  local -a cmd=(perf stat -x ',')

  cmd+=(-a)

  cmd+=(-I "${interval}")
  cmd+=(-M "$metrics")

  local group
  for group in "${PERF_EVENT_GROUPS[@]}"; do
    cmd+=(-e "$group")
  done

  if command -v timeout >/dev/null 2>&1; then
    (
      timeout --signal=INT --kill-after=5 "${duration}s" ${PERF_SUDO} "${cmd[@]}" 1>/dev/null 2>"$output_file"
    ) &
    LAST_BG_PID=$!
  else
    (
      ${PERF_SUDO} "${cmd[@]}" 1>/dev/null 2>"$output_file" &
      local inner_pid=$!
      sleep "$duration"
      kill -INT "$inner_pid" >/dev/null 2>&1 || true
      wait "$inner_pid" || true
    ) &
    LAST_BG_PID=$!
  fi
}

run_profiling_phase() {
  local duration="$1"
  local freq="$2"
  local output_file="$3"

  prepare_perf_output_file "$output_file"

  local -a cmd=(
    perf
    record
    -e
    cpu-clock
    -g
    -a
    --call-graph
    dwarf
    -N
    -F
    "$freq"
    -o
    "$output_file"
    --
    sleep
    "$duration"
  )

  ${PERF_SUDO} "${cmd[@]}" >/dev/null 2>&1 || true
}
