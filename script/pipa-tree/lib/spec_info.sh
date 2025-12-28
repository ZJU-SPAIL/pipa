#!/usr/bin/env bash
# Spec info collection module (based on healthcheck.py)

# Source common functions
source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${source_dir}/common.sh"

write_os_info_section() {
  local dest="$1"
  printf "os_info:\n" >>"$dest"
  if [[ ! -f /etc/os-release ]]; then
    yaml_write_scalar "$dest" "  " "status" "/etc/os-release not found"
    return
  fi
  while IFS='=' read -r key value; do
    [[ -z "$key" ]] && continue
    [[ "$key" == "#"* ]] && continue
    value=${value%\"}
    value=${value#\"}
    yaml_write_scalar "$dest" "  " "$key" "$value"
  done < /etc/os-release
}

write_kernel_version_section() {
  local dest="$1"
  local version
  if ! version=$(uname -r 2>/dev/null); then
    version="unknown"
  fi
  printf "kernel_version:\n" >>"$dest"
  yaml_write_scalar "$dest" "  " "version" "$version"
}

write_cpu_info_section() {
  local dest="$1"
  declare -A info=(
    ["Architecture"]="N/A"
    ["CPU(s)"]="0"
    ["Model name"]="N/A"
    ["Vendor ID"]="N/A"
    ["CPU MHz"]="N/A"
    ["BogoMIPS"]="N/A"
    ["Flags"]="N/A"
  )

  # Strategy 1: Try lscpu (Preferred)
  if command -v lscpu >/dev/null 2>&1; then
    while IFS=':' read -r key value; do
      [[ -z "$key" || -z "$value" ]] && continue
      value=$(trim_whitespace "$value")
      case "$key" in
        Architecture) info["Architecture"]="$value" ;;
        "CPU(s)")
          if [[ "$value" =~ ^[0-9]+$ ]]; then
            info["CPU(s)"]="$value"
          fi
          ;;
        "Model name") info["Model name"]="$value" ;;
        "Vendor ID") info["Vendor ID"]="$value" ;;
        "CPU max MHz") info["CPU MHz"]="$value" ;;
        BogoMIPS) info["BogoMIPS"]="$value" ;;
        Flags) info["Flags"]="$value" ;;
      esac
    done < <(LC_ALL=C lscpu 2>/dev/null || true)
  fi

  # Strategy 2: Fallback to /proc/cpuinfo if needed
  if [[ "${info["Model name"]}" == "N/A" || "${info["Vendor ID"]}" == "N/A" || "${info["CPU MHz"]}" == "N/A" || "${info["Flags"]}" == "N/A" || "${info["CPU(s)"]}" == "0" ]]; then
    local processors=0
    if [[ -f /proc/cpuinfo ]]; then
      while IFS=':' read -r key value; do
        key=$(trim_whitespace "$key")
        value=$(trim_whitespace "$value")
        case "$key" in
          processor)
            if [[ "$value" =~ ^[0-9]+$ ]]; then
              processors=$((processors + 1))
            fi
            ;;
          model\ name|Model|Processor)
            if [[ "${info["Model name"]}" == "N/A" && -n "$value" ]]; then
              info["Model name"]="$value"
            fi
            ;;
          vendor_id|CPU\ implementer)
            if [[ "${info["Vendor ID"]}" == "N/A" && -n "$value" ]]; then
              info["Vendor ID"]="$value"
            fi
            ;;
          cpu\ MHz|clock)
            if [[ "${info["CPU MHz"]}" == "N/A" && -n "$value" ]]; then
              info["CPU MHz"]="$value"
            fi
            ;;
          bogomips|BogoMIPS)
            if [[ "${info["BogoMIPS"]}" == "N/A" && -n "$value" ]]; then
              info["BogoMIPS"]="$value"
            fi
            ;;
          flags|Features)
            if [[ "${info["Flags"]}" == "N/A" && -n "$value" ]]; then
              info["Flags"]="$value"
            fi
            ;;
        esac
      done < /proc/cpuinfo
    fi
    if [[ "${info["CPU(s)"]}" == "0" && $processors -gt 0 ]]; then
      info["CPU(s)"]="$processors"
    fi
    if [[ "${info["Architecture"]}" == "N/A" ]]; then
      info["Architecture"]=$(uname -m 2>/dev/null || echo "unknown")
    fi
  fi

  printf "cpu_info:\n" >>"$dest"
  yaml_write_scalar "$dest" "  " "Architecture" "${info["Architecture"]}"
  if [[ "${info["CPU(s)"]}" =~ ^[0-9]+$ ]]; then
    yaml_write_number "$dest" "  " "CPU(s)" "${info["CPU(s)"]}"
  else
    yaml_write_scalar "$dest" "  " "CPU(s)" "${info["CPU(s)"]}"
  fi
  yaml_write_scalar "$dest" "  " "Model name" "${info["Model name"]}"
  yaml_write_scalar "$dest" "  " "Vendor ID" "${info["Vendor ID"]}"
  yaml_write_scalar "$dest" "  " "CPU MHz" "${info["CPU MHz"]}"
  yaml_write_scalar "$dest" "  " "BogoMIPS" "${info["BogoMIPS"]}"
  yaml_write_scalar "$dest" "  " "Flags" "${info["Flags"]}"
}

write_numa_info_section() {
  local dest="$1"
  local node_dir="/sys/devices/system/node"
  printf "numa_info:\n" >>"$dest"
  if [[ ! -d "$node_dir" ]]; then
    yaml_write_scalar "$dest" "  " "status" "NUMA not supported or /sys/devices/system/node not found."
    return
  fi
  local -a nodes=()
  while IFS= read -r -d '' node_path; do
    local node_name
    node_name=$(basename "$node_path")
    local cpulist_file="$node_path/cpulist"
    if [[ -f "$cpulist_file" ]]; then
      local cpu_list
      cpu_list=$(trim_whitespace "$(cat "$cpulist_file")")
      nodes+=("$node_name|$cpu_list")
    fi
  done < <(find "$node_dir" -maxdepth 1 -mindepth 1 -type d -name 'node[0-9]*' -print0 2>/dev/null)
  if (( ${#nodes[@]} == 0 )); then
    yaml_write_scalar "$dest" "  " "status" "No NUMA nodes detected."
    return
  fi
  printf "  numa_topology:\n" >>"$dest"
  local entry
  IFS=$'\n' nodes=($(printf "%s\n" "${nodes[@]}" | sort))
  for entry in "${nodes[@]}"; do
    local node_name=${entry%%|*}
    local cpu_list=${entry#*|}
    yaml_write_scalar "$dest" "    " "$node_name" "$cpu_list"
  done
}

write_cpu_governor_section() {
  local dest="$1"
  printf "cpu_governor:\n" >>"$dest"
  local -A seen=()
  local -a governors=()
  local path
  for path in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
    [[ -f "$path" ]] || continue
    local governor
    governor=$(trim_whitespace "$(cat "$path")")
    [[ -z "$governor" ]] && continue
    if [[ -z "${seen[$governor]:-}" ]]; then
      seen[$governor]=1
      governors+=("$governor")
    fi
  done
  if (( ${#governors[@]} == 0 )); then
    yaml_write_scalar "$dest" "  " "status" "Not available or not configured"
    return
  fi
  yaml_write_string_list "$dest" "  " "unique_governors" "${governors[@]}"
}

write_memory_info_section() {
  local dest="$1"
  printf "memory_info:\n" >>"$dest"
  if [[ ! -f /proc/meminfo ]]; then
    yaml_write_scalar "$dest" "  " "status" "/proc/meminfo not found"
    return
  fi
  while IFS=':' read -r key value; do
    key=$(trim_whitespace "$key")
    value=$(trim_whitespace "$value")
    [[ -z "$key" ]] && continue
    yaml_write_scalar "$dest" "  " "$key" "$value"
  done < /proc/meminfo
}

# Shared filesystem usage cache (module-level)
declare -a FS_USAGE_ENTRIES=()

build_fs_usage_cache() {
  FS_USAGE_ENTRIES=()
  if ! command -v df >/dev/null 2>&1; then
    return
  fi
  local line
  while read -r line; do
    [[ -z "$line" ]] && continue
    local filesystem total_kb used_kb avail_kb percent mount
    read -r filesystem total_kb used_kb avail_kb percent mount _ <<<"$line"
    [[ -z "$filesystem" || -z "$mount" ]] && continue
    if ! [[ "$total_kb" =~ ^[0-9]+$ && "$used_kb" =~ ^[0-9]+$ && "$avail_kb" =~ ^[0-9]+$ ]]; then
      continue
    fi
    percent=${percent%%%}
    local percent_value=0
    if [[ "$percent" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
      percent_value=$percent
    fi
    local total_bytes=$((total_kb * 1024))
    local used_bytes=$((used_kb * 1024))
    local avail_bytes=$((avail_kb * 1024))
    FS_USAGE_ENTRIES+=("$filesystem|$total_bytes|$used_bytes|$avail_bytes|$percent_value|$mount")
  done < <(df -P -k 2>/dev/null | tail -n +2)
}

print_fs_usage_block() {
  local dest="$1"
  local indent="$2"
  shift 2
  local -a search_paths=()
  local path
  for path in "$@"; do
    [[ -n "$path" ]] && search_paths+=("$path")
  done
  (( ${#search_paths[@]} == 0 )) && return 1
  local entry
  for entry in "${FS_USAGE_ENTRIES[@]}"; do
    IFS='|' read -r fs total used free percent mount <<<"$entry"
    for path in "${search_paths[@]}"; do
      if [[ "$fs" == "$path" ]]; then
        printf "%sfs_usage:\n" "$indent" >>"$dest"
        printf "%s  total: %s\n" "$indent" "$total" >>"$dest"
        printf "%s  used: %s\n" "$indent" "$used" >>"$dest"
        printf "%s  free: %s\n" "$indent" "$free" >>"$dest"
        printf "%s  percent: %s\n" "$indent" "$percent" >>"$dest"
        yaml_write_scalar "$dest" "$indent  " "mount" "$mount"
        return 0
      fi
    done
  done
  return 1
}

write_disk_info_section() {
  local dest="$1"
  printf "disk_info:\n" >>"$dest"
  build_fs_usage_cache
  local has_device=0
  local device_path
  for device_path in /sys/class/block/*; do
    [[ -e "$device_path" ]] || continue
    local dev_name
    dev_name=$(basename "$device_path")
    if [[ "$dev_name" == loop* || "$dev_name" == ram* ]]; then
      continue
    fi
    if [[ -f "$device_path/partition" ]]; then
      continue
    fi
    local size_file="$device_path/size"
    [[ -f "$size_file" ]] || continue
    local size_sectors
    size_sectors=$(trim_whitespace "$(cat "$size_file")")
    [[ "$size_sectors" =~ ^[0-9]+$ ]] || continue
    if (( has_device == 0 )); then
      printf "  block_devices:\n" >>"$dest"
      has_device=1
    fi
    local size_bytes=$((size_sectors * 512))
    local type="disk"
    local model="N/A"
    local vendor="N/A"
    local rotational="N/A"
    local dm_name=""
    if [[ -f "$device_path/device/model" ]]; then
      model=$(trim_whitespace "$(cat "$device_path/device/model")")
    fi
    if [[ -f "$device_path/device/vendor" ]]; then
      vendor=$(trim_whitespace "$(cat "$device_path/device/vendor")")
    fi
    if [[ -f "$device_path/queue/rotational" ]]; then
      local rot
      rot=$(trim_whitespace "$(cat "$device_path/queue/rotational")")
      rotational=$([[ "$rot" == "1" ]] && echo "HDD" || echo "SSD")
    fi
    if [[ "$dev_name" == dm-* ]]; then
      type="lvm/dm"
      if [[ -f "$device_path/dm/name" ]]; then
        dm_name=$(trim_whitespace "$(cat "$device_path/dm/name")")
        [[ -n "$dm_name" ]] && model="$dm_name"
      fi
    fi
    printf "    - name: \"%s\"\n" "$dev_name" >>"$dest"
    yaml_write_scalar "$dest" "      " "type" "$type"
    yaml_write_number "$dest" "      " "size_bytes" "$size_bytes"
    yaml_write_scalar "$dest" "      " "model" "$model"
    yaml_write_scalar "$dest" "      " "vendor" "$vendor"
    yaml_write_scalar "$dest" "      " "rotational" "$rotational"
    print_fs_usage_block "$dest" "      " "/dev/$dev_name" "/dev/mapper/$dm_name" || true

    local partitions=()
    local real_path
    real_path=$(readlink -f "$device_path" 2>/dev/null || true)
    if [[ -n "$real_path" && -d "$real_path" ]]; then
      while IFS= read -r -d '' sub_path; do
        if [[ -f "$sub_path/partition" && -f "$sub_path/size" ]]; then
          local part_name
          part_name=$(basename "$sub_path")
          local part_sectors
          part_sectors=$(trim_whitespace "$(cat "$sub_path/size")")
          [[ "$part_sectors" =~ ^[0-9]+$ ]] || continue
          local part_bytes=$((part_sectors * 512))
          partitions+=("$part_name|$part_bytes")
        fi
      done < <(find "$real_path" -maxdepth 1 -mindepth 1 -type d -print0 2>/dev/null)
    fi

    if (( ${#partitions[@]} == 0 )); then
      printf "      partitions: []\n" >>"$dest"
    else
      printf "      partitions:\n" >>"$dest"
      IFS=$'\n' partitions=($(printf "%s\n" "${partitions[@]}" | sort))
      local part_entry
      for part_entry in "${partitions[@]}"; do
        local part_name=${part_entry%%|*}
        local part_bytes=${part_entry#*|}
        printf "        - name: \"%s\"\n" "$part_name" >>"$dest"
        yaml_write_scalar "$dest" "          " "type" "partition"
        yaml_write_number "$dest" "          " "size_bytes" "$part_bytes"
        print_fs_usage_block "$dest" "          " "/dev/$part_name" || true
      done
    fi
  done
  if (( has_device == 0 )); then
    printf "  block_devices: []\n" >>"$dest"
  fi
}

write_io_scheduler_section() {
  local dest="$1"
  printf "io_scheduler:\n" >>"$dest"
  local found=0
  local device_path
  for device_path in /sys/class/block/*; do
    [[ -e "$device_path" ]] || continue
    local scheduler_path="$device_path/queue/scheduler"
    [[ -f "$scheduler_path" ]] || continue
    local scheduler_line
    scheduler_line=$(trim_whitespace "$(cat "$scheduler_path")")
    [[ -z "$scheduler_line" ]] && continue
    local active="$scheduler_line"
    if [[ "$scheduler_line" =~ \[([^]]+)\] ]]; then
      active="${BASH_REMATCH[1]}"
    fi
    if (( found == 0 )); then
      found=1
    fi
    yaml_write_scalar "$dest" "  " "$(basename "$device_path")" "$active"
  done
  if (( found == 0 )); then
    yaml_write_scalar "$dest" "  " "status" "Could not read I/O scheduler info"
  fi
}

write_network_info_section() {
  local dest="$1"
  printf "net_info:\n" >>"$dest"
  if ! command -v ip >/dev/null 2>&1; then
    yaml_write_scalar "$dest" "  " "error" "ip command not found"
    return
  fi
  local ip_output
  if ! ip_output=$(ip addr 2>/dev/null); then
    yaml_write_scalar "$dest" "  " "error" "Failed to run 'ip addr'"
    return
  fi
  declare -A iface_mac=()
  declare -A iface_states=()
  declare -A iface_ipv4=()
  declare -A iface_ipv6=()
  local current_iface=""
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    if [[ $line =~ ^[0-9]+:\ ([^:]+): ]]; then
      current_iface="${BASH_REMATCH[1]}"
      iface_mac["$current_iface"]="N/A"
      iface_states["$current_iface"]=""
      iface_ipv4["$current_iface"]=""
      iface_ipv6["$current_iface"]=""
      if [[ $line =~ \<([^>]+)\> ]]; then
        iface_states["$current_iface"]="${BASH_REMATCH[1]}"
      fi
      continue
    fi
    [[ -z "$current_iface" ]] && continue
    local trimmed
    trimmed=$(trim_whitespace "$line")
    if [[ "$trimmed" == link/ether* ]]; then
      iface_mac["$current_iface"]=$(echo "$trimmed" | awk '{print $2}')
    elif [[ "$trimmed" == inet\ * ]]; then
      local addr=${trimmed#inet }
      addr=${addr%% *}
      iface_ipv4["$current_iface"]+="${addr},"
    elif [[ "$trimmed" == inet6\ * ]]; then
      local addr=${trimmed#inet6 }
      addr=${addr%% *}
      iface_ipv6["$current_iface"]+="${addr},"
    fi
  done <<<"$ip_output"

  printf "  network_interfaces:\n" >>"$dest"
  if (( ${#iface_mac[@]} == 0 )); then
    yaml_write_scalar "$dest" "    " "status" "No interfaces detected"
    return
  fi
  local -a iface_names=()
  local iface
  for iface in "${!iface_mac[@]}"; do
    iface_names+=("$iface")
  done
  IFS=$'\n' iface_names=($(printf "%s\n" "${iface_names[@]}" | sort))
  for iface in "${iface_names[@]}"; do
    printf "    %s:\n" "$iface" >>"$dest"
    local states_raw="${iface_states[$iface]}"
    local -a states=()
    if [[ -n "$states_raw" ]]; then
      IFS=',' read -r -a states <<<"$states_raw"
    fi
    yaml_write_string_list "$dest" "      " "state" "${states[@]}"
    yaml_write_scalar "$dest" "      " "mac" "${iface_mac[$iface]}"
    local ipv4_raw="${iface_ipv4[$iface]%","}"
    local -a ipv4_list=()
    if [[ -n "$ipv4_raw" ]]; then
      IFS=',' read -r -a ipv4_list <<<"$ipv4_raw"
    fi
    yaml_write_string_list "$dest" "      " "ipv4" "${ipv4_list[@]}"
    local ipv6_raw="${iface_ipv6[$iface]%","}"
    local -a ipv6_list=()
    if [[ -n "$ipv6_raw" ]]; then
      IFS=',' read -r -a ipv6_list <<<"$ipv6_raw"
    fi
    yaml_write_string_list "$dest" "      " "ipv6" "${ipv6_list[@]}"
  done
}

write_kernel_parameters_section() {
  local dest="$1"
  printf "kernel_parameters:\n" >>"$dest"
  local params=(
    vm.swappiness
    kernel.pid_max
    net.core.somaxconn
    vm.dirty_ratio
    vm.dirty_background_ratio
    vm.dirty_bytes
    vm.dirty_background_bytes
    vm.overcommit_memory
    fs.file-max
  )
  if ! command -v sysctl >/dev/null 2>&1; then
    yaml_write_scalar "$dest" "  " "status" "sysctl command not available"
    return
  fi
  local output
  if ! output=$(sysctl "${params[@]}" 2>/dev/null); then
    yaml_write_scalar "$dest" "  " "status" "Could not collect sysctl parameters"
    return
  fi
  while IFS='=' read -r key value; do
    key=$(trim_whitespace "$key")
    value=$(trim_whitespace "$value")
    [[ -z "$key" ]] && continue
    yaml_write_scalar "$dest" "  " "$key" "$value"
  done <<<"$output"
}

# Main spec info collector
collect_spec_info_locally() {
  local dest_file="$1"
  : >"$dest_file"

  write_os_info_section "$dest_file"
  printf "\n" >>"$dest_file"
  write_kernel_version_section "$dest_file"
  printf "\n" >>"$dest_file"
  write_cpu_info_section "$dest_file"
  printf "\n" >>"$dest_file"
  write_numa_info_section "$dest_file"
  printf "\n" >>"$dest_file"
  write_cpu_governor_section "$dest_file"
  printf "\n" >>"$dest_file"
  write_memory_info_section "$dest_file"
  printf "\n" >>"$dest_file"
  write_disk_info_section "$dest_file"
  printf "\n" >>"$dest_file"
  write_io_scheduler_section "$dest_file"
  printf "\n" >>"$dest_file"
  write_network_info_section "$dest_file"
  printf "\n" >>"$dest_file"
  write_kernel_parameters_section "$dest_file"
}

prepare_spec_info() {
  local dest_file="$1"
  local skip_spec="$2"
  local spec_info_path="$3"

  if [[ "$skip_spec" == "1" ]]; then
    log_info "Spec info collection skipped per --no-spec-info."
    return
  fi

  if [[ -n "$spec_info_path" ]]; then
    cp "$spec_info_path" "$dest_file"
    log_info "Copied spec info from $spec_info_path"
    return
  fi

  local default_spec_info="$PWD/pipa_spec_info.yaml"
  if [[ -f "$default_spec_info" ]]; then
    cp "$default_spec_info" "$dest_file"
    log_info "Copied spec info from $default_spec_info"
    return
  fi

  collect_spec_info "$dest_file"
}

collect_spec_info() {
  local dest_file="$1"

  if [[ -n "${PIPA_TREE_SPEC_COLLECTOR:-}" ]]; then
    log_info "Running custom spec info collector: $PIPA_TREE_SPEC_COLLECTOR"
    if "$PIPA_TREE_SPEC_COLLECTOR" "$dest_file"; then
      return
    fi
    log_fatal "Custom spec info collector failed."
  fi

  collect_spec_info_locally "$dest_file"
}
