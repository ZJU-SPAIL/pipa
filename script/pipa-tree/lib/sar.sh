#!/usr/bin/env bash
# SAR collection and conversion module

# Source common functions
source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${source_dir}/common.sh"

# Shared last background PID variable
LAST_BG_PID=""

start_sar_job() {
  local duration="$1"
  local interval="$2"
  local output_bin="$3"
  local log_file="$4"
  local count=$((duration / interval))
  if (( count * interval < duration )); then
    count=$((count + 2))
  else
    count=$((count + 1))
  fi

  (
    LC_ALL=C sar -A -o "$output_bin" "$interval" "$count" >/dev/null 2>"$log_file"
  ) &
  LAST_BG_PID=$!
}

convert_sar_outputs() {
  local output_bin="$1"
  local level_dir="$2"

  declare -A sar_map=(
    [cpu]="-d -- -P ALL"
    [network]="-d -- -n DEV"
    [io]="-d -- -b"
    [disk]="-d -- -d -p"
    [memory]="-d -- -r"
    [paging]="-d -- -B"
    [load]="-d -- -q"
    [cswch]="-d -- -w"
  )

  local key
  for key in "${!sar_map[@]}"; do
    local csv_file="$level_dir/sar_${key}.csv"
    local options="${sar_map[$key]}"
    if ! sadf $options -- "$output_bin" >"$csv_file" 2>/dev/null; then
      log_warn "Failed to convert sar ${key} metrics via sadf."
      rm -f "$csv_file"
    else
      log_info "Generated $csv_file"
    fi
  done
}
