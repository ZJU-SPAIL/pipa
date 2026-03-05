#!/usr/bin/env bash
# Common utility functions for pipa-tree

# Terminal color codes
if [[ -t 2 ]] && [[ "${TERM:-}" != "dumb" ]]; then
  COLOR_RESET='\033[0m'
  COLOR_RED='\033[31m'
  COLOR_GREEN='\033[32m'
  COLOR_YELLOW='\033[33m'
  COLOR_CYAN='\033[36m'
  COLOR_BOLD='\033[1m'
  COLOR_RED_BOLD="${COLOR_BOLD}${COLOR_RED}"
else
  COLOR_RESET=''
  COLOR_RED=''
  COLOR_GREEN=''
  COLOR_YELLOW=''
  COLOR_CYAN=''
  COLOR_BOLD=''
  COLOR_RED_BOLD=''
fi

# Logging functions
log_write() {
  local level="$1"
  shift || true
  local message="$*"
  local timestamp
  timestamp=$(date +"%Y-%m-%dT%H:%M:%S%z")
  local formatted="[$timestamp][$level] $message"

  # Terminal output with colors
  if [[ -t 2 ]]; then
    local color_prefix=""
    case "$level" in
      INFO)  color_prefix="${COLOR_CYAN}" ;;
      WARN)  color_prefix="${COLOR_YELLOW}" ;;
      ERROR) color_prefix="${COLOR_RED}" ;;
      FATAL) color_prefix="${COLOR_RED_BOLD}" ;;
    esac
    printf "%b%s%b%b\n" "$color_prefix" "$formatted" "${COLOR_RESET}" >&2
  else
    printf "%s\n" "$formatted" >&2
  fi

  # Log file without colors
  if [[ -n "${PIPA_TREE_LOG_FILE:-}" ]]; then
    printf "%s\n" "$formatted" >>"$PIPA_TREE_LOG_FILE"
  fi
}

log_info() { log_write INFO "$@"; }
log_warn() { log_write WARN "$@"; }
log_error() { log_write ERROR "$@"; }
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
