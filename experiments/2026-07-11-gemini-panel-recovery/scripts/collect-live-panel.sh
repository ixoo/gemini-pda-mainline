#!/usr/bin/env bash

# Read-only Gemini PDA display-selection probe.
# Run as root when debugfs or /proc/config.gz is not readable by the SSH user:
#   ssh gemini@DEVICE 'sudo -n bash -s' < collect-live-panel.sh

set -u
export LC_ALL=C

heading() {
  printf '\n===== %s =====\n' "$1"
}

heading "framebuffer geometry"
for path in /sys/class/graphics/fb0/virtual_size \
            /sys/class/graphics/fb0/bits_per_pixel \
            /sys/class/graphics/fb0/stride \
            /sys/class/graphics/fb0/name; do
  if [[ -r "${path}" ]]; then
    printf '%s=' "${path##*/}"
    head -n 1 "${path}"
  fi
done

heading "selected MediaTek display state"
if [[ -r /sys/kernel/debug/mtkfb ]]; then
  # Keep only stable selection, geometry, and mode fields. The complete file
  # contains volatile buffer addresses, fence state, and a very large dump.
  sed -n \
    -e '/LCM Driver=/p' \
    -e '/|State=.*lcm_fps=/p' \
    -e '/Current display driver status=/p' \
    -e '/DISP_OPT_USE_DEVICE_TREE/p' \
    -e '/DISP_OPT_FAKE_LCM_[XY]/p' \
    -e '/DISP_OPT_FAKE_LCM_WIDTH/p' \
    -e '/DISP_OPT_FAKE_LCM_HEIGHT/p' \
    /sys/kernel/debug/mtkfb
else
  printf 'unavailable=/sys/kernel/debug/mtkfb\n'
fi

heading "running kernel display configuration"
if [[ -r /proc/config.gz ]]; then
  gzip -dc /proc/config.gz 2>/dev/null |
    grep -E '^(CONFIG_MTK_(FB|LCM)=|CONFIG_MTK_LCM_PHYSICAL_ROTATION=|CONFIG_CUSTOM_LCM_[XY]=)'
elif [[ -r "/boot/config-$(uname -r)" ]]; then
  grep -E '^(CONFIG_MTK_(FB|LCM)=|CONFIG_MTK_LCM_PHYSICAL_ROTATION=|CONFIG_CUSTOM_LCM_[XY]=)' \
    "/boot/config-$(uname -r)"
else
  printf 'unavailable=running kernel config\n'
fi

heading "LCD bias controller binding"
for device in /sys/bus/i2c/devices/*-003e; do
  [[ -e "${device}" ]] || continue
  printf 'device=%s\n' "${device##*/}"
  if [[ -L "${device}/driver" ]]; then
    printf 'driver=%s\n' "$(basename "$(readlink -f "${device}/driver")")"
  fi
  if [[ -r "${device}/name" ]]; then
    printf 'name='
    head -n 1 "${device}/name"
  fi
done

heading "panel-specific kernel messages"
if command -v dmesg >/dev/null 2>&1; then
  dmesg 2>/dev/null |
    grep -E 'NT36672|lcm_(poweron|resume|suspend)' |
    tail -n 80
fi
