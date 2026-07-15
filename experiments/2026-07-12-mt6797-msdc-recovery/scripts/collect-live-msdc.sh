#!/usr/bin/env bash

# Gemini PDA MT6797 MSDC evidence collector.
# The default path reads cached/runtime state only. --read-registers invokes
# the source-audited vendor debug command that clocks a host, reads its register
# block while explicitly skipping TX/RX FIFOs, then gates the host again.

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

first_line() {
  [[ -r "$1" ]] && head -n 1 "$1" 2>/dev/null
}

heading "running kernel"
uname -a

heading "MSDC bindings"
for host in /sys/class/mmc_host/mmc*; do
  [[ -e "${host}" ]] || continue
  printf '%s|provider=%s\n' "${host##*/}" \
    "$(readlink -f "${host}/device" 2>/dev/null || true)"
done

heading "MMC identity without unique identifiers"
for device in /sys/bus/mmc/devices/*; do
  [[ -e "${device}" ]] || continue
  printf '%s' "${device##*/}"
  # CID, CSD, serial, and raw uevent are deliberately excluded.
  for field in type name manfid oemid date prv hwrev fwrev erase_size \
    preferred_erase_size rel_sectors raw_rpmb_size_mult; do
    [[ -r "${device}/${field}" ]] &&
      printf '|%s=%s' "${field}" "$(first_line "${device}/${field}")"
  done
  printf '\n'
done

heading "MMC runtime IOS"
for host in /sys/kernel/debug/mmc*; do
  [[ -d "${host}" ]] || continue
  printf '[%s]\n' "${host##*/}"
  [[ -r "${host}/ios" ]] && cat "${host}/ios"
  [[ -r "${host}/clock" ]] && printf 'cached-clock=%s\n' "$(first_line "${host}/clock")"
done

heading "eMMC cached status"
for field in status state; do
  path="/sys/kernel/debug/mmc0/mmc0:0001/${field}"
  [[ -r "${path}" ]] && printf '%s=%s\n' "${field}" "$(first_line "${path}")"
done

heading "MSDC interrupts"
grep -Ei 'msdc|mmc' /proc/interrupts 2>/dev/null || true

heading "MSDC clocks"
for directory in /sys/kernel/debug/clk/*msdc*; do
  [[ -d "${directory}" ]] || continue
  printf '%s' "${directory##*/}"
  for field in clk_rate clk_enable_count clk_prepare_count clk_flags; do
    [[ -r "${directory}/${field}" ]] &&
      printf '|%s=%s' "${field}" "$(first_line "${directory}/${field}")"
  done
  printf '\n'
done

heading "storage regulators"
for device in /sys/class/regulator/regulator.*; do
  [[ -e "${device}" ]] || continue
  name="$(first_line "${device}/name")"
  case "${name}" in
    vemc_3v3|vmch|vmc)
      printf '%s|name=%s' "${device##*/}" "${name}"
      for field in state microvolts min_microvolts max_microvolts num_users; do
        [[ -r "${device}/${field}" ]] &&
          printf '|%s=%s' "${field}" "$(first_line "${device}/${field}")"
      done
      printf '\n'
      ;;
  esac
done

heading "MSDC register snapshots"
if [[ "${READ_REGISTERS}" -eq 0 ]]; then
  printf 'not-read=rerun as root with --read-registers after auditing vendor dbg.c\n'
else
  control=/proc/msdc_debug
  if [[ ! -w "${control}" || ! -r "${control}" ]]; then
    printf 'error=/proc/msdc_debug is not readable and writable by this process\n' >&2
    exit 1
  fi
  for id in 0 1; do
    printf '[msdc%s]\n' "${id}"
    # The write only queues a debug request. The following read executes case
    # SD_TOOL_REG_ACCESS/p1=4: clock enable, ordinary register reads, explicit
    # "not read" placeholders for TXDATA/RXDATA, then clock disable.
    printf '5 4 %x\n' "${id}" > "${control}"
    cat "${control}"
  done
fi
