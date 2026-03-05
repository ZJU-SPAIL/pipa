#!/usr/bin/env bash
# pipa-tree uninstallation script

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
INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"
LIB_INSTALL_DIR="/usr/local/lib/pipa-tree"
SUDOERS_FILE="/etc/sudoers.d/pipa-tree"
SCRIPT_NAME="pipa-tree"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
  log_error "This script requires root privileges."
  log_info "Please run with: sudo $0"
  exit 1
fi

# Check if pipa-tree is installed
if [[ ! -f "$INSTALL_DIR/$SCRIPT_NAME" ]]; then
  log_warn "$SCRIPT_NAME is not installed in $INSTALL_DIR"
  log_info "Nothing to remove."
  exit 0
fi

# Confirm uninstallation
sudoers_will_be_removed=0
if [[ -f "$SUDOERS_FILE" ]]; then
  sudoers_will_be_removed=1
fi

echo ""
echo "This will uninstall pipa-tree from the following locations:"
echo "  - $INSTALL_DIR/$SCRIPT_NAME"
echo "  - $LIB_INSTALL_DIR"
if (( sudoers_will_be_removed == 1 )); then
  echo "  - $SUDOERS_FILE (sudoers configuration)"
fi
echo ""
read -p "Are you sure you want to continue? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  log_info "Uninstallation cancelled."
  exit 0
fi

# Remove sudoers configuration if exists
if [[ -f "$SUDOERS_FILE" ]]; then
  log_info "Removing sudoers configuration from $SUDOERS_FILE..."
  rm -f "$SUDOERS_FILE"
  log_success "Removed $SUDOERS_FILE"
fi

# Remove pipa-tree executable
log_info "Removing $INSTALL_DIR/$SCRIPT_NAME..."
rm -f "$INSTALL_DIR/$SCRIPT_NAME"
log_success "Removed $INSTALL_DIR/$SCRIPT_NAME"

# Remove library directory
if [[ -d "$LIB_INSTALL_DIR" ]]; then
  log_info "Removing $LIB_INSTALL_DIR..."
  rm -rf "$LIB_INSTALL_DIR"
  log_success "Removed $LIB_INSTALL_DIR"
else
  log_warn "$LIB_INSTALL_DIR does not exist"
fi

log_success "Uninstallation complete!"
echo ""
echo "pipa-tree has been uninstalled from your system."
echo "To reinstall, run: sudo ./install.sh"
