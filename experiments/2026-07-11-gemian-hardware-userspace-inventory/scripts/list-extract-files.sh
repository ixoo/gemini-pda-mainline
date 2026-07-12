#!/usr/bin/env bash

# Emit a NUL-delimited, root-relative list for extract-device-userspace.
# This helper is sent over SSH and performs no writes.

set -euo pipefail
export LC_ALL=C

readonly MODE="${1:-all}"

case "${MODE}" in
  all|vendor-only) ;;
  *)
    printf 'invalid mode: %s\n' "${MODE}" >&2
    exit 2
    ;;
esac

emit_tree() {
  local root="$1"
  [[ -d "${root}" ]] || return 0
  find "${root}" -xdev \( -type f -o -type l \) -printf '%P\0' 2>/dev/null \
    | while IFS= read -r -d '' relative; do
        printf '%s\0' "${root#/}/${relative}"
      done
}

emit_path() {
  local path="$1"
  [[ -f "${path}" || -L "${path}" ]] || return 0
  printf '%s\0' "${path#/}"
}

emit_package() {
  local package="$1"
  local path

  dpkg-query -W "${package}" >/dev/null 2>&1 || return 0
  while IFS= read -r path; do
    case "${path}" in
      /usr/lib/lxc-android/70-*.rules)
        case "$(basename "${path}")" in
          70-aeon6797_6m_n.rules|70-generic.rules)
            emit_path "${path}"
            ;;
        esac
        ;;
      /bin/*|/sbin/*|/usr/bin/*|/usr/sbin/*|/usr/lib/*|/lib/systemd/*|/etc/systemd/*|/lib/udev/*|/etc/udev/*|/etc/lxc/*|/etc/hybris-*|/etc/ofono/*|/etc/pulse/*)
        emit_path "${path}"
        ;;
    esac
  done < <(dpkg-query -L "${package}" 2>/dev/null)
}

{
  # Complete Android hardware-vendor payload. These are system-partition files,
  # not device-unique NVRAM or protected-partition contents.
  emit_tree /system/vendor/bin
  emit_tree /system/vendor/lib
  emit_tree /system/vendor/lib64
  emit_tree /system/vendor/firmware
  emit_tree /system/etc/firmware

  # Android framework processes that load the hardware HAL entry points.
  emit_path /system/bin/cameraserver
  emit_path /system/bin/sensorservice
  emit_path /system/bin/surfaceflinger

  if [[ "${MODE}" == all ]]; then
    packages=(
      lxc-android
      libandroid-properties1
      libhardware2
      libmedia1
      libhybris
      libhybris-common1
      libhybris-utils
      drihybris
      glamor-hybris
      xserver-xorg-video-hwcomposer
      pulseaudio-module-droid
      ofono
      telepathy-ofono
      libgrilio
      connman-plugin-suspend-wmtwifi
      repowerd
      gemian-leds
      hybris-usb
    )
    for package in "${packages[@]}"; do
      emit_package "${package}"
    done
  fi
} | sort -zu
