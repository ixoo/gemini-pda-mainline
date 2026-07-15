#!/usr/bin/env bash

# Gemini PDA MT6351/PMIC-wrapper evidence collector.
# Default operation is read-only. --read-chip-id performs two explicitly
# source-audited PMIC-wrapper reads through the vendor pmic_access interface.

set -u
export LC_ALL=C

READ_CHIP_ID=0
READ_REGULATORS=0
for argument in "$@"; do
  case "${argument}" in
    --read-chip-id)
      READ_CHIP_ID=1
      ;;
    --read-regulators)
      READ_REGULATORS=1
      ;;
    *)
      printf 'usage: %s [--read-chip-id] [--read-regulators]\n' "${0##*/}" >&2
      exit 2
      ;;
  esac
done

heading() {
  printf '\n===== %s =====\n' "$1"
}

first_line() {
  [[ -r "$1" ]] && head -n 1 "$1" 2>/dev/null
}

pmic_read() {
  local access=$1
  local address=$2

  # A single <=4-character token selects the audited pwrap_wacs2() read path.
  # Supplying a second token would select the PMIC write path and is forbidden.
  [[ "${address}" =~ ^[0-9a-fA-F]{1,4}$ ]] || return 2
  printf '%s' "${address}" > "${access}"
  printf '0x%s=0x%04x\n' "${address}" "$(first_line "${access}")"
}

heading "PMIC platform bindings"
for driver in mt-pmic mt-rtc; do
  for device in "/sys/bus/platform/drivers/${driver}"/*; do
    [[ -L "${device}" ]] || continue
    printf 'driver=%s|device=%s\n' "${driver}" "${device##*/}"
  done
done

heading "PMIC wrapper and external interrupt"
grep -Ei 'pmic_wrap|pmic-eint' /proc/interrupts 2>/dev/null || true

heading "PMIC clocks"
for name in pmicspi_sel infra_pmic_ap infra_pmic_tmr infra_pmic_md infra_pmic_conn; do
  directory="/sys/kernel/debug/clk/${name}"
  [[ -d "${directory}" ]] || continue
  printf '%s' "${name}"
  for field in clk_rate clk_enable_count clk_prepare_count clk_flags; do
    [[ -r "${directory}/${field}" ]] &&
      printf '|%s=%s' "${field}" "$(first_line "${directory}/${field}")"
  done
  printf '\n'
done

heading "PMIC regulator class"
for device in /sys/class/regulator/regulator.*; do
  [[ -e "${device}" ]] || continue
  printf '%s' "${device##*/}"
  for field in name state status microvolts min_microvolts max_microvolts num_users; do
    [[ -r "${device}/${field}" ]] &&
      printf '|%s=%s' "${field}" "$(first_line "${device}/${field}")"
  done
  provider="$(readlink -f "${device}/device" 2>/dev/null || true)"
  [[ -n "${provider}" ]] && printf '|provider=%s' "${provider}"
  printf '\n'
done

heading "PMIC hardware status"
if [[ -r /proc/mt_pmic/dump_ldo_status ]]; then
  cat /proc/mt_pmic/dump_ldo_status
else
  printf 'unavailable=/proc/mt_pmic/dump_ldo_status\n'
fi

heading "RTC interface"
if [[ -r /proc/driver/rtc ]]; then
  # Time/date are transient and may expose user policy. Capture capabilities
  # and alarm state only.
  grep -E '^(alarm_IRQ|alrm_pending|update IRQ enabled|periodic IRQ enabled|periodic IRQ frequency|max user IRQ frequency|24hr)' \
    /proc/driver/rtc || true
fi
for device in /sys/class/rtc/rtc*; do
  [[ -e "${device}" ]] || continue
  printf '%s|name=%s|hctosys=%s|wakealarm=%s\n' \
    "${device##*/}" "$(first_line "${device}/name")" \
    "$(first_line "${device}/hctosys")" "$(first_line "${device}/wakealarm")"
done

heading "PMIC input path"
awk '
  /^N: Name=/ { name=$0 }
  /^H: Handlers=/ && name ~ /mtk-kpd|ACCDET/ { print name "|" $0 }
' /proc/bus/input/devices 2>/dev/null

heading "running kernel PMIC configuration"
if [[ -r /proc/config.gz ]]; then
  gzip -dc /proc/config.gz 2>/dev/null |
    grep -E '^(CONFIG_MTK_PMIC|CONFIG_MTK_RTC|CONFIG_KEYBOARD_MTK|CONFIG_KPD_PWRKEY_USE_PMIC|CONFIG_REGULATOR|CONFIG_RTC_)' || true
fi

heading "PMIC chip identity"
if [[ "${READ_CHIP_ID}" -eq 0 ]]; then
  printf 'not-read=rerun as root with --read-chip-id after auditing the vendor handler\n'
else
  access=/sys/devices/platform/mt-pmic/pmic_access
  if [[ ! -w "${access}" || ! -r "${access}" ]]; then
    printf 'error=pmic_access is not readable and writable by this process\n' >&2
    exit 1
  fi
  # Vendor source proves that a single <=4-character token takes the
  # pwrap_wacs2(read) branch. Never add a second token: that is the PMIC write
  # branch. MT6351 HWCID is register 0x200 and SWCID is register 0x202.
  printf '200' > "${access}"
  hwcid="$(first_line "${access}")"
  printf '202' > "${access}"
  swcid="$(first_line "${access}")"
  printf 'HWCID=0x%x\n' "${hwcid}"
  printf 'SWCID=0x%x\n' "${swcid}"
fi

heading "PMIC regulator control registers"
if [[ "${READ_REGULATORS}" -eq 0 ]]; then
  printf 'not-read=rerun as root with --read-regulators after auditing the vendor handler\n'
else
  access=/sys/devices/platform/mt-pmic/pmic_access
  if [[ ! -w "${access}" || ! -r "${access}" ]]; then
    printf 'error=pmic_access is not readable and writable by this process\n' >&2
    exit 1
  fi

  # Buck CON0/1/2/4/5/6/7 registers expose software-vs-hardware ownership,
  # requested enable/selector, active/sleep selectors, and readback. These are
  # ordinary control registers, not interrupt/status registers with read side
  # effects. Bases are VCORE through VSRAM_PROC at a 0x14 stride.
  for base in 600 614 628 63c 650 664 678 68c 6a0; do
    base_value=$((16#${base}))
    for offset in 0 2 4 8 10 12 14; do
      printf -v address '%x' "$((base_value + offset))"
      pmic_read "${access}" "${address}"
    done
  done

  # LDO enable/control and voltage-selector registers used by the recovered
  # descriptor table. Repeated shared registers are deliberately listed once.
  for address in \
    a00 a04 a08 a0c a12 a16 a1c a22 a28 a2e a34 a3a a40 a46 a4c a52 \
    a58 a5e a64 a68 a6e a74 a7a a80 a86 a8c a98 a9a aa2 aa4 aaa \
    ac4 ac6 ac8 aca acc ace ad2 ad6 ada ae2 ae6 aee af2 af6 afa afc \
    b00 b08 b0c b10 b14 b18 b1c b22; do
    pmic_read "${access}" "${address}"
  done
fi
