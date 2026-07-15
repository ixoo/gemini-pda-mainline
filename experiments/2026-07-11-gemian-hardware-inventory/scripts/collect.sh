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
    tr '\000' ' ' < "${path}" 2>/dev/null | sed 's/[[:space:]]*$//'
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

dt_relative() {
  local node="$1"
  if [[ "${node}" == "${DT_ROOT}" ]]; then
    printf '/'
  else
    printf '/%s' "${node#"${DT_ROOT}"/}"
  fi
}

emit_dt_property() {
  local node="$1"
  local property="$2"
  local name="${property##*/}"
  local relative=""
  local value=""

  relative="$(dt_relative "${node}")"

  if [[ ! -s "${property}" ]]; then
    value="<present>"
  else
    case "${name}" in
      compatible|status|model|device_type|label|charger_name|regulator-name|*-names)
        value="$(read_text "${property}")"
        ;;
      *)
        value="$(read_hex "${property}")"
        ;;
    esac
  fi
  printf '%s|%s=%s\n' "${relative}" "${name}" "${value}"
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
    local relative=""
    local status="okay"
    local reg=""
    local interrupts=""
    local interrupt_parent=""

    [[ -r "${node}/status" ]] && status="$(read_text "${node}/status")"
    [[ -r "${node}/reg" ]] && reg="$(read_hex "${node}/reg")"
    [[ -r "${node}/interrupts" ]] && interrupts="$(read_hex "${node}/interrupts")"
    [[ -r "${node}/interrupt-parent" ]] && interrupt_parent="$(read_hex "${node}/interrupt-parent")"
    relative="$(dt_relative "${node}")"
    printf '%s|compatible=%s|status=%s|reg=%s|interrupts=%s|interrupt-parent=%s\n' \
      "${relative}" \
      "$(read_text "${compatible}")" \
      "${status}" \
      "${reg}" \
      "${interrupts}" \
      "${interrupt_parent}"
  done

  heading "selected device tree property values"
  find "${DT_ROOT}" -type f -print 2>/dev/null | sort | while IFS= read -r property; do
    local node="${property%/*}"
    local name="${property##*/}"

    case "${name}" in
      '#address-cells'|'#size-cells'|'#clock-cells'|'#reset-cells'|'#power-domain-cells'|'#iommu-cells'|'#phy-cells'|'#dma-cells'|'#gpio-cells'|'#interrupt-cells'|\
      compatible|status|model|device_type|label|phandle|linux,phandle|reg|ranges|dma-ranges|\
      interrupts|interrupts-extended|interrupt-parent|interrupt-names|\
      clocks|clock-names|assigned-clocks|assigned-clock-parents|assigned-clock-rates|\
      resets|reset-names|power-domains|iommus|phys|phy-names|dmas|dma-names|\
      pinctrl-[0-9]*|pinctrl-names|*-gpios|*-gpio|*_gpio|*-supply|\
      pins|pinmux|output-high|output-low|slew-rate|drive-strength|bias-disable|\
      bus-width|max-frequency|clock-frequency|spi-max-frequency|reg-names|\
      clk_src|clock-div|host_function|cd_level|cell-index|id|debounce|\
      register_setting|pinctl|pinctl_*|bootable|mmc-ddr-1_8v|\
      cap-sd-highspeed|sd-uhs-*|mediatek,use-*|mediatek,*_used|\
      mediatek,max_eint_num|mediatek,max_hw_deb_cnt|mediatek,mapping_table_entry|mediatek,mapping_table|\
      mediatek,max_deint_cnt|mediatek,deint_possible_irq|mediatek,builtin_eint_hw_deb|\
      mediatek,builtin_entry|mediatek,builtin_mapping|mediatek,debtime_setting_entry|mediatek,debtime_setting_array|\
      mediatek,kpd-*|\
      regulator-name|regulator-min-microvolt|regulator-max-microvolt|regulator-always-on|regulator-boot-on|\
      non-removable|cap-mmc-highspeed|mmc-hs200-1_8v|mmc-hs400-1_8v|broken-cd|disable-wp|cd-inverted|\
      charger_name|aicr|cv|ichg|ieoc|mivr|ircmp_resistor|ircmp_vclamp|safety_timer|en_te|en_wdt|rt,intr_gpio_num|\
      lcm_params-*|\
      gpio-controller|interrupt-controller|wakeup-source|enable-active-high)
        emit_dt_property "${node}" "${property}"
        ;;
    esac

    if [[ "$(dt_relative "${node}")" == /lcm_ops ]]; then
      case "${name}" in
        init|compare_id|suspend|backlight|backlight_cmdq)
          emit_dt_property "${node}" "${property}"
          ;;
      esac
    fi
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
