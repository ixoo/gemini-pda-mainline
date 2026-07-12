#!/usr/bin/env bash

# Read-only Gemini PDA hardware inventory collector.
# Run from the host with either:
#   ssh gemini@DEVICE 'bash -s -- SECTION' < collect.sh
#   ssh gemini@DEVICE 'sudo -n bash -s -- SECTION' < collect.sh
# Root may expose additional protected resources, but is not required.

set -u
export LC_ALL=C

readonly SECTION="${1:-all}"
DT_ROOT="$(readlink -f /proc/device-tree 2>/dev/null || printf /proc/device-tree)"
readonly DT_ROOT

heading() {
  printf '\n===== %s =====\n' "$1"
}

read_text() {
  local path="$1"
  if [[ -r "${path}" ]]; then
    tr '\000' ' ' < "${path}" 2>/dev/null
  fi
}

read_hex() {
  local path="$1"
  if [[ -r "${path}" ]]; then
    od -An -v -tx1 "${path}" 2>/dev/null | tr -d ' \n'
  fi
}

read_first() {
  local path="$1"
  if [[ -r "${path}" ]]; then
    head -n 1 "${path}" 2>/dev/null
  fi
}

sanitize_bootargs() {
  sed -E \
    -e 's/((androidboot\.)?(serialno|imei|meid|cid|wifi_mac|bt_mac|macaddr))=[^ ]+/\1=<redacted>/Ig' \
    -e 's/([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}/<redacted-mac>/g'
}

identity() {
  heading "operating system"
  uname -a
  if [[ -r /etc/os-release ]]; then
    sed -n 's/^\(PRETTY_NAME\|ID\|VERSION_ID\)=/\1=/p' /etc/os-release
  fi
  printf 'machine=%s\n' "$(uname -m)"

  heading "device tree identity"
  printf 'model=%s\n' "$(read_text "${DT_ROOT}/model")"
  printf 'compatible=%s\n' "$(read_text "${DT_ROOT}/compatible")"
  if [[ -r "${DT_ROOT}/chosen/bootargs" ]]; then
    printf 'bootargs='
    read_text "${DT_ROOT}/chosen/bootargs" | sanitize_bootargs
    printf '\n'
  fi

  heading "cpu"
  if command -v lscpu >/dev/null 2>&1; then
    lscpu
  fi
  sed -E '/^[Ss]erial[[:space:]]*:/d' /proc/cpuinfo

  heading "memory"
  grep -E '^(MemTotal|MemFree|MemAvailable|Buffers|Cached|SwapTotal|HugePages_Total|CmaTotal|CmaFree):' /proc/meminfo || true
  if [[ -r "${DT_ROOT}/memory/reg" ]]; then
    printf 'device-tree-memory-reg=%s\n' "$(read_hex "${DT_ROOT}/memory/reg")"
  fi
}

device_tree() {
  heading "device tree nodes"
  if [[ ! -d "${DT_ROOT}" ]]; then
    echo "device tree not mounted"
    return
  fi

  find "${DT_ROOT}" -type f -name compatible -print 2>/dev/null | sort | while IFS= read -r compatible; do
    local node="${compatible%/compatible}"
    local relative="/${node#"${DT_ROOT}"/}"
    local status="okay"
    local reg=""
    local interrupts=""
    local interrupt_parent=""

    [[ -r "${node}/status" ]] && status="$(read_text "${node}/status")"
    [[ -r "${node}/reg" ]] && reg="$(read_hex "${node}/reg")"
    [[ -r "${node}/interrupts" ]] && interrupts="$(read_hex "${node}/interrupts")"
    [[ -r "${node}/interrupt-parent" ]] && interrupt_parent="$(read_hex "${node}/interrupt-parent")"
    printf '%s|compatible=%s|status=%s|reg=%s|interrupts=%s|interrupt-parent=%s\n' \
      "${relative}" \
      "$(read_text "${compatible}")" \
      "${status}" \
      "${reg}" \
      "${interrupts}" \
      "${interrupt_parent}"
  done

  heading "device tree property inventory"
  find "${DT_ROOT}" -type f \
    ! -name serial-number \
    ! -name mac-address \
    ! -name local-mac-address \
    ! -name rng-seed \
    ! -name kaslr-seed \
    -printf '/%P\n' 2>/dev/null | sort
}

sysfs_bus() {
  local bus="$1"
  local device
  local driver
  local modalias
  local of_node

  heading "${bus} devices"
  for device in "/sys/bus/${bus}/devices"/*; do
    [[ -e "${device}" ]] || continue
    driver=""
    modalias=""
    of_node=""
    [[ -L "${device}/driver" ]] && driver="$(basename "$(readlink "${device}/driver")")"
    [[ -r "${device}/modalias" ]] && modalias="$(read_first "${device}/modalias")"
    [[ -L "${device}/of_node" ]] && of_node="$(readlink -f "${device}/of_node")"
    printf '%s|driver=%s|modalias=%s|of_node=%s\n' \
      "$(basename "${device}")" "${driver}" "${modalias}" "${of_node#"${DT_ROOT}"}"
  done
}

buses() {
  local device
  local field

  sysfs_bus platform
  sysfs_bus i2c
  sysfs_bus spi
  sysfs_bus mmc
  sysfs_bus usb

  heading "mmc identity without unique identifiers"
  for device in /sys/bus/mmc/devices/*; do
    [[ -e "${device}" ]] || continue
    printf '%s' "$(basename "${device}")"
    for field in type name manfid oemid date hwrev fwrev; do
      [[ -r "${device}/${field}" ]] && printf '|%s=%s' "${field}" "$(read_first "${device}/${field}")"
    done
    printf '\n'
  done

  heading "usb identity without serials"
  for device in /sys/bus/usb/devices/*; do
    [[ -e "${device}" ]] || continue
    [[ -r "${device}/idVendor" ]] || continue
    printf '%s|vendor=%s|product=%s|bcdDevice=%s|manufacturer=%s|name=%s\n' \
      "$(basename "${device}")" \
      "$(read_first "${device}/idVendor")" \
      "$(read_first "${device}/idProduct")" \
      "$(read_first "${device}/bcdDevice")" \
      "$(read_first "${device}/manufacturer")" \
      "$(read_first "${device}/product")"
  done

  heading "block devices without serials or UUIDs"
  if command -v lsblk >/dev/null 2>&1; then
    lsblk -b -o NAME,SIZE,RO,TYPE,FSTYPE,MOUNTPOINT 2>/dev/null || true
  else
    cat /proc/partitions
  fi

  heading "input devices without unique identifiers"
  if [[ -r /proc/bus/input/devices ]]; then
    sed -E '/^U: Uniq=/d' /proc/bus/input/devices
  fi

  heading "network interfaces without addresses"
  for device in /sys/class/net/*; do
    [[ -e "${device}" ]] || continue
    printf '%s|type=%s|driver=%s\n' \
      "$(basename "${device}")" \
      "$(read_first "${device}/type")" \
      "$([[ -L "${device}/device/driver" ]] && basename "$(readlink "${device}/device/driver")")"
  done

  heading "interrupts"
  cat /proc/interrupts

  heading "physical resource map"
  [[ -r /proc/iomem ]] && cat /proc/iomem || echo "unavailable to this user"
}

class_inventory() {
  local class="$1"
  local device
  heading "${class} class"
  for device in "/sys/class/${class}"/*; do
    [[ -e "${device}" ]] || continue
    printf '%s|device=%s\n' "$(basename "${device}")" "$(readlink -f "${device}/device" 2>/dev/null || true)"
  done
}

power_and_peripherals() {
  local device
  local field

  heading "power supplies"
  for device in /sys/class/power_supply/*; do
    [[ -e "${device}" ]] || continue
    printf '%s' "$(basename "${device}")"
    for field in type status health technology manufacturer model_name capacity voltage_now voltage_min_design voltage_max_design current_now charge_now charge_full charge_full_design energy_now energy_full energy_full_design temp online present; do
      [[ -r "${device}/${field}" ]] && printf '|%s=%s' "${field}" "$(read_first "${device}/${field}")"
    done
    printf '\n'
  done

  heading "thermal zones"
  for device in /sys/class/thermal/thermal_zone*; do
    [[ -e "${device}" ]] || continue
    printf '%s|type=%s|temp=%s\n' "$(basename "${device}")" "$(read_first "${device}/type")" "$(read_first "${device}/temp")"
  done

  heading "cpu frequency"
  for device in /sys/devices/system/cpu/cpufreq/policy* /sys/devices/system/cpu/cpu*/cpufreq; do
    [[ -e "${device}" ]] || continue
    printf '%s' "$(basename "${device}")"
    for field in affected_cpus scaling_driver scaling_governor scaling_available_governors scaling_available_frequencies cpuinfo_min_freq cpuinfo_max_freq scaling_cur_freq; do
      [[ -r "${device}/${field}" ]] && printf '|%s=%s' "${field}" "$(read_first "${device}/${field}")"
    done
    printf '\n'
  done

  heading "regulator class"
  for device in /sys/class/regulator/regulator.*; do
    [[ -e "${device}" ]] || continue
    printf '%s' "$(basename "${device}")"
    for field in name state status microvolts min_microvolts max_microvolts num_users type; do
      [[ -r "${device}/${field}" ]] && printf '|%s=%s' "${field}" "$(read_first "${device}/${field}")"
    done
    printf '\n'
  done

  heading "framebuffers"
  for device in /sys/class/graphics/fb*; do
    [[ -e "${device}" ]] || continue
    printf '%s|name=%s|modes=%s|virtual_size=%s|bpp=%s\n' \
      "$(basename "${device}")" \
      "$(read_first "${device}/name")" \
      "$(tr '\n' ',' < "${device}/modes" 2>/dev/null)" \
      "$(read_first "${device}/virtual_size")" \
      "$(read_first "${device}/bits_per_pixel")"
  done

  heading "alsa"
  [[ -r /proc/asound/cards ]] && cat /proc/asound/cards
  [[ -r /proc/asound/pcm ]] && cat /proc/asound/pcm

  for field in drm backlight leds hwmon iio gpio; do
    class_inventory "${field}"
  done
}

debugfs_inventory() {
  local path
  heading "debugfs status"
  if ! mount | grep -q ' on /sys/kernel/debug '; then
    echo "debugfs is not mounted; skipped without changing system state"
    return
  fi

  for path in \
    /sys/kernel/debug/clk/clk_summary \
    /sys/kernel/debug/regulator/regulator_summary \
    /sys/kernel/debug/gpio \
    /sys/kernel/debug/wakeup_sources; do
    heading "${path#/sys/kernel/debug/}"
    [[ -r "${path}" ]] && cat "${path}" || echo "unavailable"
  done

  heading "pinctrl debug inventory"
  find /sys/kernel/debug/pinctrl -maxdepth 2 -type f -print 2>/dev/null | sort | while IFS= read -r path; do
    case "$(basename "${path}")" in
      pins|pinmux-pins|pinconf-pins|gpio-ranges)
        echo "--- ${path}"
        cat "${path}" 2>/dev/null || true
        ;;
    esac
  done
}

kernel_inventory() {
  local config=""

  heading "loaded modules"
  cat /proc/modules

  heading "relevant kernel configuration"
  if [[ -r /proc/config.gz ]]; then
    config='gzip -dc /proc/config.gz'
  elif [[ -r "/boot/config-$(uname -r)" ]]; then
    config="cat /boot/config-$(uname -r)"
  fi
  if [[ -n "${config}" ]]; then
    eval "${config}" | grep -E '^(CONFIG_(ARM64|ARCH_MEDIATEK|MACH_MT|MTK|MEDIATEK|SERIAL|PINCTRL|GPIO|I2C|SPI|MMC|MFD|REGULATOR|POWER_SUPPLY|BATTERY|CHARGER|THERMAL|CPU_FREQ|CPU_IDLE|FB|DRM|BACKLIGHT|INPUT|KEYBOARD|TOUCHSCREEN|USB|SND|BT|WLAN|CFG80211|RFKILL|IIO|WATCHDOG|RTC|PM_SLEEP|SUSPEND|HIBERNATION|DEBUG_FS)|# CONFIG_(ARCH_MEDIATEK|MTK|MEDIATEK|DRM|PM_SLEEP|SUSPEND)_)' || true
  else
    echo "kernel configuration unavailable"
  fi

  heading "hardware-related boot log (sanitized)"
  dmesg 2>/dev/null \
    | head -n 2500 \
    | grep -Ei 'machine|model|cpu|memory|reserved|psci|gic|timer|clock|pinctrl|gpio|i2c|spi|mmc|msdc|usb|uart|serial|input|keyboard|touch|framebuffer|display|drm|mipi|dsi|battery|charger|regulator|thermal|watchdog|rtc|wifi|wlan|bluetooth|firmware|mediatek|mt6797' \
    | grep -Eiv 'imei|serial(number|no)?|mac address|random seed|key|credential' \
    | sed -E 's/([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}/<redacted-mac>/g' || true
}

case "${SECTION}" in
  identity) identity ;;
  device-tree) device_tree ;;
  buses) buses ;;
  peripherals) power_and_peripherals ;;
  debugfs) debugfs_inventory ;;
  kernel) kernel_inventory ;;
  all)
    identity
    device_tree
    buses
    power_and_peripherals
    debugfs_inventory
    kernel_inventory
    ;;
  *)
    echo "usage: $0 identity|device-tree|buses|peripherals|debugfs|kernel|all" >&2
    exit 2
    ;;
esac
