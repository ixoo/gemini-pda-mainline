#!/usr/bin/env bash

set -euo pipefail

readonly PACKAGE="${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel artifact}"
readonly DTB="${PACKAGE}/dtbs/mediatek/mt6797-gemini-pda.dtb"
readonly MAP="${PACKAGE}/System.map"

for command in fdtget rg sha256sum; do
  command -v "${command}" >/dev/null 2>&1 || {
    echo "error: required command not found: ${command}" >&2
    exit 1
  }
done
[[ -f "${DTB}" && -f "${MAP}" ]] || {
  echo "error: package is missing Gemini DTB or System.map" >&2
  exit 1
}

serial0="$(fdtget -t s "${DTB}" /aliases serial0)"
stdout_path="$(fdtget -t s "${DTB}" /chosen stdout-path)"
compatible="$(fdtget -t s "${DTB}" /serial@11002000 compatible)"
status="$(fdtget -t s "${DTB}" /serial@11002000 status)"
reg="$(fdtget -t x "${DTB}" /serial@11002000 reg)"
interrupts="$(fdtget -t x "${DTB}" /serial@11002000 interrupts)"

[[ "${serial0}" == /serial@11002000 ]] || {
  echo "error: serial0 does not target UART0: ${serial0}" >&2
  exit 1
}
[[ "${stdout_path}" == serial0:921600n8 ]] || {
  echo "error: unexpected stdout-path: ${stdout_path}" >&2
  exit 1
}
[[ "${status}" == okay ]] || {
  echo "error: UART0 is not enabled: ${status}" >&2
  exit 1
}

printf 'validation=mainline-console-contract\n'
printf 'package=%s\n' "${PACKAGE}"
printf 'dtb_sha256=%s\n' "$(sha256sum "${DTB}" | awk '{print $1}')"
printf 'system_map_sha256=%s\n' "$(sha256sum "${MAP}" | awk '{print $1}')"
printf 'serial0=%s\n' "${serial0}"
printf 'stdout_path=%s\n' "${stdout_path}"
printf 'uart0_compatible=%s\n' "${compatible}"
printf 'uart0_status=%s\n' "${status}"
printf 'uart0_reg=%s\n' "${reg}"
printf 'uart0_interrupts=%s\n' "${interrupts}"
printf 'kernel_console=ttyS0\n'
printf 'earlycon=uart8250,mmio32,0x11002000\n'
printf 'vendor_console=ttyMT0 (not reused)\n'
printf 'dma=deferred;PIO_first\n'

printf '\n[linked_symbols]\n'
for symbol in mtk8250_probe early_serial8250_setup serial8250_register_8250_port; do
  rg -n " (T|t) ${symbol}$" "${MAP}"
done

printf '\n[decision]\n'
printf '%s\n' \
  'UART0 DT alias and stdout-path select the MT6797 8250 PIO port.' \
  'The standard Linux name is ttyS0; vendor ttyMT0 must not be copied into the mainline command line without runtime evidence.' \
  'The early console uses the 8250 mmio32 path; vendor AP-DMA windows remain deferred.' \
  'runtime_mainline_boot=not_attempted' \
  'hardware_write=none'
