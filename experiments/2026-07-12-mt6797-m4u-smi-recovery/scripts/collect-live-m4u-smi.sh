#!/usr/bin/env bash

# Read-only Gemini PDA MT6797 M4U/SMI evidence collector.
# The default path reads kernel-exported state only. --read-registers invokes
# the source-audited vendor debugfs register snapshot.

set -u
export LC_ALL=C

READ_REGISTERS=0
case "${1:-}" in
  "") ;;
  --read-registers) READ_REGISTERS=1 ;;
  *)
    printf 'usage: %s [--read-registers]\n' "${0##*/}" >&2
    exit 2
    ;;
esac

heading() {
  printf '\n===== %s =====\n' "$1"
}

read_field() {
  [[ -r "$1" ]] && head -n 1 "$1" 2>/dev/null
}

heading "running kernel"
uname -a

heading "M4U and SMI interrupts"
grep -Ei 'm4u|iommu|smi|larb' /proc/interrupts 2>/dev/null || true

heading "M4U and SMI iomem resources"
grep -Ei 'm4u|iommu|smi|larb' /proc/iomem 2>/dev/null || true

heading "IOMMU groups"
for group in /sys/kernel/iommu_groups/*; do
  [[ -d "${group}" ]] || continue
  printf '[group %s]\n' "${group##*/}"
  for device in "${group}"/devices/*; do
    [[ -e "${device}" ]] || continue
    printf '%s\n' "${device##*/}"
  done
done

heading "platform devices and drivers"
for directory in /sys/bus/platform/devices/* /sys/bus/platform/drivers/*; do
  [[ -e "${directory}" ]] || continue
  name="${directory##*/}"
  case "${name}" in
    *m4u*|*iommu*|*smi*|*larb*)
      printf '%s|target=%s\n' "${directory}" \
        "$(readlink -f "${directory}" 2>/dev/null || true)"
      ;;
  esac
done

heading "runtime power-management state"
for device in /sys/bus/platform/devices/*; do
  [[ -e "${device}" ]] || continue
  name="${device##*/}"
  case "${name}" in
    10205000.*|12002000.*|14020000.*|14021000.*|14022000.*|15001000.*|16010000.*|17001000.*|1a001000.*)
      printf '%s' "${name}"
      for field in runtime_status runtime_active_time runtime_suspended_time control; do
        value="$(read_field "${device}/power/${field}")"
        [[ -n "${value}" ]] && printf '|%s=%s' "${field}" "${value}"
      done
      printf '\n'
      ;;
  esac
done

heading "M4U and SMI clocks"
for directory in /sys/kernel/debug/clk/*; do
  [[ -d "${directory}" ]] || continue
  name="${directory##*/}"
  case "${name}" in
    *m4u*|*smi*|*larb*|*vdec*|*venc*|*mjc*|*img*|*cam*)
      printf '%s' "${name}"
      for field in clk_rate clk_enable_count clk_prepare_count clk_flags; do
        value="$(read_field "${directory}/${field}")"
        [[ -n "${value}" ]] && printf '|%s=%s' "${field}" "${value}"
      done
      printf '\n'
      ;;
  esac
done

heading "device-tree M4U and SMI nodes"
for node in /sys/firmware/devicetree/base/*/*; do
  [[ -d "${node}" ]] || continue
  name="${node##*/}"
  case "${name}" in
    m4u@*|iommu@*|smi@*|smi_larb*@*|larb@*)
      printf '%s' "${node#/sys/firmware/devicetree/base}"
      [[ -r "${node}/compatible" ]] &&
        printf '|compatible=%s' "$(tr '\0' ',' < "${node}/compatible" | sed 's/,$//')"
      [[ -r "${node}/status" ]] &&
        printf '|status=%s' "$(tr -d '\0' < "${node}/status")"
      printf '\n'
      ;;
  esac
done

heading "M4U register snapshot"
if [[ "${READ_REGISTERS}" -eq 0 ]]; then
  printf 'not-read=rerun as root with --read-registers after auditing vendor m4u_debug.c and m4u_hw.c\n'
else
  register=/sys/kernel/debug/m4u/register
  if [[ ! -r "${register}" ]]; then
    printf 'error=%s is not readable by this process\n' "${register}" >&2
    exit 1
  fi
  # The read handler calls m4u_dump_reg(0, 0), which performs ordinary 32-bit
  # reads from offsets 0x000 through 0x17c and logs them. It does not write a
  # register, change a clock, or use the READ_ENTRY command register.
  cat "${register}"
fi

heading "infracfg 4-GiB mode"
if [[ "${READ_REGISTERS}" -eq 0 ]]; then
  printf 'not-read=rerun as root with --read-registers\n'
elif command -v busybox >/dev/null 2>&1 && busybox --list | grep -Fxq devmem; then
  # INFRACFG_AO is always powered. Linux defines REG_INFRA_MISC at 0xf00
  # and F_DDR_4GB_SUPPORT_EN as bit 13; this performs one 32-bit read.
  busybox devmem 0x10001f00 32
else
  printf 'not-read=BusyBox devmem applet unavailable\n'
fi

heading "targeted M4U control registers"
if [[ "${READ_REGISTERS}" -eq 0 ]]; then
  printf 'not-read=rerun as root with --read-registers\n'
elif command -v busybox >/dev/null 2>&1 && busybox --list | grep -Fxq devmem; then
  # The downstream driver treats the M4U block clock as always on. These are
  # ordinary control/status reads already covered by m4u_dump_reg(0, 0).
  for pair in \
    038:0x10205038 048:0x10205048 050:0x10205050 054:0x10205054 \
    080:0x10205080 084:0x10205084 088:0x10205088 110:0x10205110 \
    114:0x10205114 120:0x10205120 124:0x10205124 134:0x10205134; do
    offset="${pair%%:*}"
    address="${pair#*:}"
    printf '%s=' "${offset}"
    busybox devmem "${address}" 32
  done
else
  printf 'not-read=BusyBox devmem applet unavailable\n'
fi

heading "kernel messages"
dmesg 2>/dev/null | grep -Ei 'm4u|iommu|smi|larb' || true
