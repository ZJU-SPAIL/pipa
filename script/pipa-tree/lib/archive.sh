#!/usr/bin/env bash
# Archive and utility functions module

# Source common functions
source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${source_dir}/common.sh"

cleanup_work_dir() {
  if [[ -n "${WORK_DIR:-}" && -d "$WORK_DIR" ]]; then
    rm -rf "$WORK_DIR"
  fi
}

generate_default_output_path() {
  local timestamp
  timestamp=$(date +%Y%m%d_%H%M%S)
  printf "%s/pipa-collection-%s.tar.gz" "$PWD" "$timestamp"
}

archive_results() {
  local work_dir="$1"
  local output_path="$2"
  local parent_dir
  parent_dir=$(dirname "$output_path")
  mkdir -p "$parent_dir"
  local tmp_archive="${output_path}.tmp"
  tar -C "$work_dir" -czf "$tmp_archive" .
  mv "$tmp_archive" "$output_path"
  log_info "Archive created at $output_path"
}
