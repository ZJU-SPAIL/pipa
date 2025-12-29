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
  local old_ifs="$IFS"
  IFS=$'\n' nodes=($(printf "%s\n" "${nodes[@]}" | sort))
  IFS="$old_ifs"
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
      local old_ifs="$IFS"
      IFS=$'\n' partitions=($(printf "%s\n" "${partitions[@]}" | sort))
      IFS="$old_ifs"
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
  local old_ifs="$IFS"
  IFS=$'\n' iface_names=($(printf "%s\n" "${iface_names[@]}" | sort))
  IFS="$old_ifs"
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

write_interrupt_info_section() {
  local dest="$1"
  printf "interrupt_info:\n" >>"$dest"
  if [[ ! -f /proc/interrupts ]]; then
    yaml_write_scalar "$dest" "  " "status" "/proc/interrupts not found"
    return
  fi
  local cpu_count=0
  local header_line
  header_line=$(grep -E 'CPU[0-9]' /proc/interrupts | head -1)
  if [[ -n "$header_line" ]]; then
    cpu_count=$(echo "$header_line" | grep -oE 'CPU[0-9]+' | wc -l)
  fi
  yaml_write_number "$dest" "  " "cpu_count" "$cpu_count"
  printf "  interrupt_counts:\n" >>"$dest"
  local line
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    if [[ "$line" =~ CPU[0-9]+ ]]; then
      continue
    fi
    local irq_number=""
    if [[ "$line" =~ ^[[:space:]]*([0-9]+): ]]; then
      irq_number="${BASH_REMATCH[1]}"
    fi
    local irq_name=""
    local rest="${line#*:}"
    local total=0
    local count=0
    for word in $rest; do
      if [[ "$count" -lt "$cpu_count" && "$word" =~ ^[0-9]+$ ]]; then
        total=$((total + word))
      fi
      count=$((count + 1))
    done
    if [[ "$count" -ge "$cpu_count" ]]; then
      local irq_name_fields=($rest)
      irq_name="${irq_name_fields[@]:$cpu_count}"
      irq_name=$(echo "$irq_name" | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
    fi
    if [[ -n "$irq_name" && -n "$irq_number" ]]; then
      printf "    - irq: \"%s\"\n" "$irq_name" >>"$dest"
      printf "      number: %s\n" "$irq_number" >>"$dest"
      printf "      total: %s\n" "$total" >>"$dest"
    fi
  done < /proc/interrupts
}

write_ulimit_info_section() {
  local dest="$1"
  printf "ulimit_info:\n" >>"$dest"
  local ulimit_output
  if ! ulimit_output=$(ulimit -a 2>/dev/null); then
    yaml_write_scalar "$dest" "  " "status" "ulimit command failed"
    return
  fi
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    if [[ "$line" =~ ^([a-z][a-z ]+)[[:space:]]+(.+)$ ]]; then
      local key="${BASH_REMATCH[1]}"
      local value="${BASH_REMATCH[2]}"
      key=$(trim_whitespace "$key")
      yaml_write_scalar "$dest" "  " "$key" "$value"
    fi
  done <<<"$ulimit_output"
}

write_lsmod_info_section() {
  local dest="$1"
  printf "module_info:\n" >>"$dest"
  local lsmod_cmd=""
  if command -v lsmod >/dev/null 2>&1; then
    lsmod_cmd="lsmod"
  elif command -v sudo >/dev/null 2>&1; then
    if sudo -n lsmod >/dev/null 2>&1; then
      lsmod_cmd="sudo lsmod"
    fi
  fi
  if [[ -z "$lsmod_cmd" ]]; then
    yaml_write_scalar "$dest" "  " "status" "lsmod command not found or requires sudo access"
    return
  fi
  local lsmod_output
  if ! lsmod_output=$($lsmod_cmd 2>/dev/null); then
    yaml_write_scalar "$dest" "  " "status" "lsmod command failed"
    return
  fi
  printf "  loaded_modules:\n" >>"$dest"
  local skip_header=1
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    if (( skip_header == 1 )); then
      skip_header=0
      continue
    fi
    read -r module size used_by deps <<<"$line"
    [[ -z "$module" ]] && continue
    printf "    - name: \"%s\"\n" "$module" >>"$dest"
    if [[ "$size" =~ ^[0-9]+$ ]]; then
      yaml_write_number "$dest" "      " "size" "$size"
    else
      yaml_write_scalar "$dest" "      " "size" "$size"
    fi
    yaml_write_scalar "$dest" "      " "used_by" "$used_by"
    yaml_write_scalar "$dest" "      " "deps" "$deps"
  done <<<"$lsmod_output"
}

write_lspci_info_section() {
  local dest="$1"
  printf "pci_info:\n" >>"$dest"
  local lspci_cmd=""
  if command -v lspci >/dev/null 2>&1; then
    lspci_cmd="lspci"
  elif command -v sudo >/dev/null 2>&1; then
    if sudo -n lspci -v >/dev/null 2>&1; then
      lspci_cmd="sudo lspci"
    fi
  fi
  if [[ -z "$lspci_cmd" ]]; then
    yaml_write_scalar "$dest" "  " "status" "lspci command not found or requires sudo access"
    return
  fi
  local lspci_output
  if ! lspci_output=$($lspci_cmd -v 2>/dev/null); then
    yaml_write_scalar "$dest" "  " "status" "lspci command failed"
    return
  fi
  local -a devices=()
  local current_device=""
  while IFS= read -r line; do
    if [[ "$line" =~ ^[0-9a-fA-F]+:[0-9a-fA-F]+\.[0-9a-fA-F]+ ]]; then
      if [[ -n "$current_device" ]]; then
        devices+=("$current_device")
      fi
      current_device="$line"
    else
      if [[ -n "$current_device" ]]; then
        current_device="${current_device}"$'\n'"${line}"
      fi
    fi
  done <<<"$lspci_output"
  if [[ -n "$current_device" ]]; then
    devices+=("$current_device")
  fi
  printf "  pci_devices:\n" >>"$dest"
  local device_id=0
  local device
  for device in "${devices[@]}"; do
    printf "    - device_id: %d\n" "$device_id" >>"$dest"
    local device_line
    device_line=$(echo "$device" | head -1)
    yaml_write_scalar "$dest" "      " "device" "$device_line"
    local details
    details=$(echo "$device" | tail -n +2 | head -20)
    if [[ -n "$details" ]]; then
      yaml_write_scalar "$dest" "      " "details" "$details"
    fi
    device_id=$((device_id + 1))
  done
}

write_dmidecode_info_section() {
  local dest="$1"
  printf "bios_hardware_info:\n" >>"$dest"
  local dmidecode_cmd=""
  if command -v dmidecode >/dev/null 2>&1; then
    dmidecode_cmd="dmidecode"
  elif command -v sudo >/dev/null 2>&1; then
    if sudo -n dmidecode --version >/dev/null 2>&1; then
      dmidecode_cmd="sudo dmidecode"
    fi
  fi
  if [[ -z "$dmidecode_cmd" ]]; then
    yaml_write_scalar "$dest" "  " "status" "dmidecode command not found or requires sudo access"
    return
  fi
  local dmidecode_types=(
    "bios"
    "system"
    "baseboard"
    "chassis"
    "processor"
    "memory"
  )
  local dmitype
  for dmitype in "${dmidecode_types[@]}"; do
    printf "  %s:\n" "$dmitype" >>"$dest"
    local output
    if output=$($dmidecode_cmd --type "$dmitype" 2>/dev/null); then
      while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        if [[ "$line" =~ ^[A-Z].*: ]]; then
          local key="${line%%:*}"
          local value="${line#*:}"
          key=$(trim_whitespace "$key")
          value=$(trim_whitespace "$value")
          [[ -n "$value" ]] && yaml_write_scalar "$dest" "    " "$key" "$value"
        fi
      done <<<"$output"
    else
      yaml_write_scalar "$dest" "    " "status" "Failed to retrieve $dmitype info"
    fi
  done
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
  printf "\n" >>"$dest_file"
  write_interrupt_info_section "$dest_file"
  printf "\n" >>"$dest_file"
  write_ulimit_info_section "$dest_file"
  printf "\n" >>"$dest_file"
  write_lsmod_info_section "$dest_file"
  printf "\n" >>"$dest_file"
  write_lspci_info_section "$dest_file"
  printf "\n" >>"$dest_file"
  write_dmidecode_info_section "$dest_file"
}

prepare_spec_info() {
  local dest_file="$1"
  local skip_spec="$2"
  local force_refresh="$3"

  if [[ "$skip_spec" == "1" ]]; then
    log_info "Spec info collection skipped per --no-spec-info."
    return
  fi

  local data_dir="${PIPA_TREE_DATA_DIR:-$PWD/data}"
  mkdir -p "$data_dir"
  local cached_spec="$data_dir/spec_info.yaml"

  if [[ "$force_refresh" != "1" && -f "$cached_spec" ]]; then
    log_info "Using cached spec info from $cached_spec"
    cp "$cached_spec" "$dest_file"
    return
  fi

  collect_spec_info "$dest_file"
  cp "$dest_file" "$cached_spec"
  log_info "Cached spec info to $cached_spec"
}

collect_spec_info() {
  local dest_file="$1"

  collect_spec_info_locally "$dest_file"
}
