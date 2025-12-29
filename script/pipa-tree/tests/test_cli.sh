#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/xyjiang/project/pipa"
CLI="$ROOT_DIR/script/pipa-tree/pipa-tree"
TMP_DIR=$(mktemp -d -t pipa_tree_tests_XXXX)
FAKE_BIN_DIR=$(mktemp -d -t pipa_tree_fakebin_XXXX)

cleanup() {
  rm -rf "$TMP_DIR" "$FAKE_BIN_DIR"
}
trap cleanup EXIT

setup_fake_tools() {
  cat <<'EOF' >"$FAKE_BIN_DIR/perf"
#!/usr/bin/env bash
set -euo pipefail
trap 'exit 0' INT TERM
if [[ $# -lt 1 ]]; then
  exit 0
fi
cmd="$1"
shift
case "$cmd" in
  stat)
    # Emit stub metrics to stderr
    echo "fake-perf-stat;value" >&2
    sleep 0.1
    ;;
  record)
    output_file=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        -o)
          output_file="$2"
          shift 2
          ;;
        --)
          shift
          break
          ;;
        *)
          shift
          ;;
      esac
    done
    : "${output_file:=perf.data}"
    echo "fake perf data" >"$output_file"
    sleep 0.1
    ;;
  *)
    ;;
 esac
EOF

  cat <<'EOF' >"$FAKE_BIN_DIR/sar"
#!/usr/bin/env bash
set -euo pipefail
output_file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o)
      output_file="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
: "${output_file:?missing -o}"
printf "stub" >"$output_file"
sleep 0.1
EOF

  cat <<'EOF' >"$FAKE_BIN_DIR/sadf"
#!/usr/bin/env bash
set -euo pipefail
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "--" ]]; then
    shift
    break
  fi
  shift
done
input_file="${1:-}"
: "${input_file:?missing input file}"
cat <<'CSV'
timestamp;value
0;0
CSV
EOF

  cat <<'EOF' >"$FAKE_BIN_DIR/fake_healthcheck.sh"
#!/usr/bin/env bash
set -euo pipefail
output_file="$1"
cat <<'YAML' >"$output_file"
os_info:
  name: fake
cpu_info:
  architecture: fake
YAML
EOF

  chmod +x "$FAKE_BIN_DIR"/perf "$FAKE_BIN_DIR"/sar "$FAKE_BIN_DIR"/sadf "$FAKE_BIN_DIR"/fake_healthcheck.sh
  export PATH="$FAKE_BIN_DIR:$PATH"
  export PIPA_TREE_SPEC_COLLECTOR="$FAKE_BIN_DIR/fake_healthcheck.sh"
}

setup_fake_tools

run_expect_success() {
  local description="$1"
  shift
  if ! "$@"; then
    echo "[FAIL] $description" >&2
    exit 1
  else
    echo "[PASS] $description"
  fi
}

run_expect_failure() {
  local description="$1"
  shift
  if "$@"; then
    echo "[FAIL] $description (unexpected success)" >&2
    exit 1
  else
    echo "[PASS] $description"
  fi
}

run_expect_success "bash syntax check" bash -n "$CLI"
run_expect_success "main help" "$CLI" help >/dev/null

SYSTEM_ARCHIVE="$TMP_DIR/system_collection.tar.gz"
run_expect_success "system-wide sampling" \
  "$CLI" collect \
    --output "$SYSTEM_ARCHIVE" \
    --duration-stat 1 \
    --duration-record 1

run_expect_success "system archive is valid tar" tar -tzf "$SYSTEM_ARCHIVE" >/dev/null

DEFAULT_OUTPUT_DIR="$TMP_DIR/default_output"
mkdir -p "$DEFAULT_OUTPUT_DIR"
run_expect_success "default output path" bash -c "cd \"$DEFAULT_OUTPUT_DIR\" && \"$CLI\" collect --duration-stat 1 --duration-record 1 --no-spec-info"
LATEST_ARCHIVE=$(ls -t "$DEFAULT_OUTPUT_DIR"/pipa-collection-*.tar.gz 2>/dev/null | head -1)
if [[ -z "$LATEST_ARCHIVE" ]]; then
  echo "[FAIL] default output archive not found" >&2
  exit 1
fi
run_expect_success "default archive is valid tar" tar -tzf "$LATEST_ARCHIVE" >/dev/null

NOINFO_ARCHIVE="$TMP_DIR/system_noinfo.tar.gz"
run_expect_success "system-wide sampling without spec info" \
  "$CLI" collect \
    --output "$NOINFO_ARCHIVE" \
    --duration-stat 1 \
    --duration-record 1 \
    --no-spec-info

run_expect_success "system no-info archive is valid tar" tar -tzf "$NOINFO_ARCHIVE" >/dev/null

run_expect_failure "require at least one phase" \
  bash -c "cd \"$TMP_DIR\" && \"$CLI\" collect --no-spec-info --no-stat --no-record"

echo "All CLI tests passed."
