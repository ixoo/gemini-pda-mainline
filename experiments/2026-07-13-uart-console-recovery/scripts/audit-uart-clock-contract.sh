#!/usr/bin/env bash

set -euo pipefail

readonly LINUX_TREE="${LINUX_TREE:?set LINUX_TREE to the prepared Linux source tree}"
readonly SOURCE="${LINUX_TREE}/drivers/tty/serial/8250/8250_mtk.c"

for command in rg sha256sum; do
  command -v "${command}" >/dev/null 2>&1 || {
    echo "error: required command not found: ${command}" >&2
    exit 1
  }
done
[[ -f "${SOURCE}" ]] || {
  echo "error: 8250_mtk source is missing" >&2
  exit 1
}

for marker in \
  'data->uart_clk = devm_clk_get_enabled' \
  'data->bus_clk = devm_clk_get_enabled'; do
  rg -q -- "${marker}" "${SOURCE}" || {
    echo "error: UART clock lifetime rule is missing: ${marker}" >&2
    exit 1
  }
done

printf 'validation=uart-clock-contract\n'
printf 'linux_source=drivers/tty/serial/8250/8250_mtk.c\n'
printf 'linux_source_sha256=%s\n' "$(sha256sum "${SOURCE}" | awk '{print $1}')"
printf 'baud_clock=devm_clk_get_enabled\n'
printf 'unnamed_clock_fallback=devm_clk_get_enabled\n'
printf 'bus_clock=devm_clk_get_enabled\n'
printf 'clk_ignore_unused=not_required_by_driver_contract\n'
printf 'runtime_mainline_boot=not_attempted\n'
printf 'hardware_write=none\n'
