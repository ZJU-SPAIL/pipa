#!/usr/bin/env bash
# Common utility functions for pipa-tree

# Logging functions
log_info() { printf "[INFO] %s\n" "$*" >&2; }
log_warn() { printf "[WARN] %s\n" "$*" >&2; }
log_error() { printf "[ERROR] %s\n" "$*" >&2; }
log_fatal() {
  log_error "$*"
  exit 1
}

# String utility functions
trim_whitespace() {
  local value="${1:-}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf "%s" "$value"
}

# YAML utility functions
yaml_escape_string() {
  local raw="${1:-}"
  raw=${raw//$'\r'/ }
  raw=${raw//$'\n'/\\n}
  raw=${raw//\\/\\\\}
  raw=${raw//\"/\\\"}
  printf "%s" "$raw"
}

yaml_write_scalar() {
  local dest="$1"
  local indent="$2"
  local key="$3"
  local value="${4:-}"
  local escaped
  escaped=$(yaml_escape_string "$value")
  printf "%s%s: \"%s\"\n" "$indent" "$key" "$escaped" >>"$dest"
}

yaml_write_number() {
  local dest="$1"
  local indent="$2"
  local key="$3"
  local value="${4:-0}"
  printf "%s%s: %s\n" "$indent" "$key" "$value" >>"$dest"
}

yaml_write_string_list() {
  local dest="$1"
  local indent="$2"
  local key="$3"
  shift 3
  if (( $# == 0 )); then
    printf "%s%s: []\n" "$indent" "$key" >>"$dest"
    return
  fi
  printf "%s%s:\n" "$indent" "$key" >>"$dest"
  local entry
  for entry in "$@"; do
    local escaped
    escaped=$(yaml_escape_string "$entry")
    printf "%s  - \"%s\"\n" "$indent" "$escaped" >>"$dest"
  done
}

# Command availability check
ensure_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    log_fatal "Required command '$cmd' not found in PATH."
  fi
}
