# pipa-tree Installation Guide

## Quick Installation

Run the installation script with root privileges:

```bash
sudo ./install.sh
```

### Installation Options

| Option | Description |
|--------|-------------|
| (default) | Install to `/usr/local/bin` (requires sudo for perf) |
| `--all-users` | Configure sudoers to allow all users to run perf with sudo automatically |

```bash
sudo ./install.sh              # Standard installation
sudo ./install.sh --all-users   # Enable sudo for perf (recommended for multi-user)
```

## What Gets Installed

| Path | Content |
|-------|----------|
| `/usr/local/bin/pipa-tree` | Main executable script |
| `/usr/local/lib/pipa-tree/` | Library modules |
| `/etc/sudoers.d/pipa-tree` | Sudoers configuration (if `--all-users` used) |

## Usage After Installation

```bash
# Show help
pipa-tree help

# Run performance sampling (generates .tar.gz archive)
pipa-tree collect --output mydata.tar.gz

# With custom durations
pipa-tree collect --duration-stat 30 --duration-record 30
```

## Permission Requirements

### Standard Installation

**Perf commands require elevated privileges** for system-wide profiling (`-a` flag).

**Option 1**: Run pipa-tree with sudo
```bash
sudo pipa-tree collect --output data.tar.gz
```

**Option 2**: Adjust `perf_event_paranoid` kernel parameter (requires root)
```bash
echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid
```

### All Users Mode (`--all-users`)

```bash
sudo ./install.sh --all-users
```

This creates a sudoers rule that allows **all users** to run perf commands with elevated privileges:

- **No sudo required** when running pipa-tree
- **Any user** can run: `pipa-tree collect`
- Ideal for multi-user environments

**How it works**: perf.sh detects the sudoers configuration at runtime and automatically prefixes perf commands with `sudo`.

**Security Note**: The sudoers rule is scoped to `perf stat` and `perf record` commands only, not arbitrary sudo access.

## Library Path Resolution

`pipa-tree` automatically detects library path in this order:

1. **Environment variable** `PIPA_TREE_LIB_DIR` (if set)
2. **Installed path** `/usr/local/lib/pipa-tree` (if exists)
3. **Local lib** `./lib` (for development)

### Custom Library Location

To use libraries from a custom location:

```bash
export PIPA_TREE_LIB_DIR=/path/to/your/lib
pipa-tree collect --output data.tar.gz
```

## Uninstallation

Run the uninstallation script with root privileges:

```bash
sudo ./uninstall.sh
```

The script will:
1. Remove `/usr/local/bin/pipa-tree`
2. Remove `/usr/local/lib/pipa-tree/`

You will be prompted to confirm the uninstallation before proceeding.

## Troubleshooting

### Error: `/usr/local/lib/pipa-tree: No such file or directory`

**Cause**: Libraries were not installed correctly.

**Fix**: Re-run installation script:
```bash
sudo ./install.sh
```

### Error: Permission denied

**Cause**: Script requires root privileges to write to `/usr/local/bin` and `/usr/local/lib`.

**Fix**: Run with sudo:
```bash
sudo ./install.sh
```

## Development Mode

To run pipa-tree without installing (from source directory):

```bash
./pipa-tree collect --output data.tar.gz
```

This uses the `./lib` directory directly.
