#!/usr/bin/env bash
# pipa-tree installation script

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { printf "[INFO] %s\n" "$*" >&2; }
log_success() { printf "${GREEN}[SUCCESS] %s${NC}\n" "$*" >&2; }
log_warn() { printf "${YELLOW}[WARN] %s${NC}\n" "$*" >&2; }
log_error() { printf "${RED}[ERROR] %s${NC}\n" "$*" >&2; }

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"
LIB_INSTALL_DIR="/usr/local/lib/pipa-tree"
SUDOERS_FILE="/etc/sudoers.d/pipa-tree"
SCRIPT_NAME="pipa-tree"
ALL_USERS=0

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --all-users)
      ALL_USERS=1
      shift
      ;;
    *)
      log_error "Unknown option: $1"
      log_info "Usage: sudo $0 [--all-users]"
      exit 1
      ;;
  esac
done

# Check if running as root
if [[ $EUID -ne 0 ]]; then
  log_error "This script requires root privileges."
  log_info "Please run with: sudo $0"
  exit 1
fi

# Check if pipa-tree exists
if [[ ! -f "$SCRIPT_DIR/$SCRIPT_NAME" ]]; then
  log_error "$SCRIPT_NAME not found in $SCRIPT_DIR"
  log_info "Please run this script from pipa-tree directory."
  exit 1
fi

# Check if lib directory exists
if [[ ! -d "$SCRIPT_DIR/lib" ]]; then
  log_error "lib directory not found in $SCRIPT_DIR"
  exit 1
fi

# Create install directory if it doesn't exist
if [[ ! -d "$INSTALL_DIR" ]]; then
  log_info "Creating installation directory: $INSTALL_DIR"
  mkdir -p "$INSTALL_DIR"
fi

# Copy pipa-tree to install directory
log_info "Installing $SCRIPT_NAME to $INSTALL_DIR..."
cp "$SCRIPT_DIR/$SCRIPT_NAME" "$INSTALL_DIR/$SCRIPT_NAME"

# Make it executable (owner:rwx, group:rx, others:rx)
chmod 755 "$INSTALL_DIR/$SCRIPT_NAME"
log_success "Made $INSTALL_DIR/$SCRIPT_NAME executable (755)"

# Create lib directory for libraries
mkdir -p "$LIB_INSTALL_DIR"
log_info "Installing library files to $LIB_INSTALL_DIR..."

# Copy all library files
cp -r "$SCRIPT_DIR/lib"/* "$LIB_INSTALL_DIR/"

# Set proper permissions for library files and directory
chmod 755 "$LIB_INSTALL_DIR"
find "$LIB_INSTALL_DIR" -type f -exec chmod 644 {} \;
log_success "Set library permissions (755/644)"

# Configure sudoers if --all-users is specified
if (( ALL_USERS == 1 )); then
  log_info "Configuring sudoers for all users..."
  cat > "$SUDOERS_FILE" << 'EOF'
# pipa-tree sudoers configuration
# Allows all users to execute perf commands without password
# This enables full perf functionality for non-root users
Cmnd_Alias PIPA_PERF = /usr/bin/perf stat *, /usr/bin/perf record *
ALL ALL=(ALL) NOPASSWD: PIPA_PERF
EOF
  chmod 440 "$SUDOERS_FILE"
  log_success "Sudoers configuration written to $SUDOERS_FILE"
fi

log_success "Installation complete!"
echo ""
echo "pipa-tree has been installed to $INSTALL_DIR/$SCRIPT_NAME"
echo "Library files installed to $LIB_INSTALL_DIR"
if (( ALL_USERS == 1 )); then
  echo "Sudoers configuration enabled: all users can run perf with sudo"
fi
echo ""
echo "You can now run:"
echo "  $SCRIPT_NAME help"
echo "  $SCRIPT_NAME collect --output mydata.pipa"
echo ""
echo "To uninstall, run:"
echo "  sudo ./uninstall.sh"
echo ""
echo "Note: pipa-tree uses the PIPA_TREE_LIB_DIR environment variable."
echo "If you have installed libraries elsewhere, set:"
echo "  export PIPA_TREE_LIB_DIR=/path/to/lib"
