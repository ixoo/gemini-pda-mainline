#!/usr/bin/env bash

set -euo pipefail

readonly LK_TREE="${LK_TREE:?set LK_TREE to the retained LK source tree}"
readonly PACKAGE="${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel artifact}"
readonly UART_SOURCE="${LK_TREE}/platform/mt6797/uart.c"
readonly REG_BASE_SOURCE="${LK_TREE}/platform/mt6797/include/platform/mt_reg_base.h"
readonly BOOT_SOURCE="${LK_TREE}/app/mt_boot/mt_boot.c"
readonly DTB="${PACKAGE}/dtbs/mediatek/mt6797-gemini-pda.dtb"
readonly MAP="${PACKAGE}/System.map"
readonly LIVE_IDENTITY="${LIVE_IDENTITY:-}"

for command in fdtget git rg sha256sum; do
  command -v "${command}" >/dev/null 2>&1 || {
    echo "error: required command not found: ${command}" >&2
    exit 1
  }
done

git -C "${LK_TREE}" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "error: LK tree is not a Git worktree: ${LK_TREE}" >&2
  exit 1
}
[[ -f "${UART_SOURCE}" && -f "${REG_BASE_SOURCE}" && -f "${BOOT_SOURCE}" ]] || {
  echo "error: LK tree is missing the expected MT6797 sources" >&2
  exit 1
}
[[ -f "${DTB}" && -f "${MAP}" ]] || {
  echo "error: package is missing Gemini DTB or System.map" >&2
  exit 1
}

has() {
  rg -q -- "$1" "$2"
}

has_fixed() {
  rg -Fq -- "$1" "$2"
}

anchor_line() {
  rg -n --no-filename -m 1 -- "$1" "$2" | cut -d: -f1
}

has 'COMMANDLINE_TO_KERNEL.*console=ttyMT3,921600n1' "${REG_BASE_SOURCE}" || {
  echo "error: non-FPGA LK command-line default was not found" >&2
  exit 1
}
has 'log_port = g_boot_arg->log_port' "${UART_SOURCE}" || {
  echo "error: LK UART selection no longer reads log_port" >&2
  exit 1
}
has 'log_enable = g_boot_arg->log_enable' "${UART_SOURCE}" || {
  echo "error: LK UART selection no longer reads log_enable" >&2
  exit 1
}
if ! has 'case UART1:' "${UART_SOURCE}" || ! has 'return 1;' "${UART_SOURCE}"; then
  echo "error: LK UART1 mapping is missing" >&2
  exit 1
fi
if ! has 'case UART2:' "${UART_SOURCE}" || ! has 'return 2;' "${UART_SOURCE}"; then
  echo "error: LK UART2 mapping is missing" >&2
  exit 1
fi
if ! has 'case UART3:' "${UART_SOURCE}" || ! has 'return 3;' "${UART_SOURCE}"; then
  echo "error: LK UART3 mapping is missing" >&2
  exit 1
fi
if ! has 'case UART4:' "${UART_SOURCE}" || ! has 'return 4;' "${UART_SOURCE}"; then
  echo "error: LK UART4 mapping is missing" >&2
  exit 1
fi
has_fixed "change_uart_port(command, '0')" "${UART_SOURCE}" || {
  echo "error: LK UART0 console mutation is missing" >&2
  exit 1
}
has_fixed "change_uart_port(command, '1')" "${UART_SOURCE}" || {
  echo "error: LK UART1 console mutation is missing" >&2
  exit 1
}
has_fixed "change_uart_port(command, '2')" "${UART_SOURCE}" || {
  echo "error: LK UART2 console mutation is missing" >&2
  exit 1
}
has_fixed "change_uart_port(command, '3')" "${UART_SOURCE}" || {
  echo "error: LK UART3 console mutation is missing" >&2
  exit 1
}
has_fixed 'custom_port_in_kernel(g_boot_mode, cmdline_get())' "${BOOT_SOURCE}" || {
  echo "error: LK boot handoff no longer calls custom_port_in_kernel" >&2
  exit 1
}
has_fixed 'cmdline_append(g_boot_hdr->cmdline)' "${BOOT_SOURCE}" || {
  echo "error: LK boot header command line append is missing" >&2
  exit 1
}
has_fixed 'fdt_setprop_string(fdt, offset, "bootargs", (char *)cmdline_get())' "${BOOT_SOURCE}" || {
  echo "error: LK bootargs overwrite is missing" >&2
  exit 1
}

serial0="$(fdtget -t s "${DTB}" /aliases serial0)"
stdout_path="$(fdtget -t s "${DTB}" /chosen stdout-path)"
[[ "${serial0}" == /serial@11002000 ]] || {
  echo "error: packaged serial0 alias changed: ${serial0}" >&2
  exit 1
}
[[ "${stdout_path}" == serial0:921600n8 ]] || {
  echo "error: packaged stdout-path changed: ${stdout_path}" >&2
  exit 1
}

printf 'validation=lk-console-mutation\n'
printf 'lk_source_revision=%s\n' "$(git -C "${LK_TREE}" rev-parse HEAD)"
printf 'lk_uart_source_sha256=%s\n' "$(sha256sum "${UART_SOURCE}" | awk '{print $1}')"
printf 'lk_reg_base_source_sha256=%s\n' "$(sha256sum "${REG_BASE_SOURCE}" | awk '{print $1}')"
printf 'lk_boot_source_sha256=%s\n' "$(sha256sum "${BOOT_SOURCE}" | awk '{print $1}')"
printf 'lk_source_anchor_uart_switch_guard=%s:%s\n' "platform/mt6797/uart.c" "$(anchor_line '^#ifdef __ENABLE_UART_LOG_SWITCH_FEATURE__' "${UART_SOURCE}")"
printf 'lk_source_anchor_uart_selection=%s:%s\n' "platform/mt6797/uart.c" "$(anchor_line 'log_port = g_boot_arg->log_port' "${UART_SOURCE}")"
printf 'lk_source_anchor_uart_change_first_token=%s:%s\n' "platform/mt6797/uart.c" "$(anchor_line 'ptr\[5\] = new_val' "${UART_SOURCE}")"
printf 'lk_source_anchor_custom_port=%s:%s\n' "platform/mt6797/uart.c" "$(anchor_line '^void custom_port_in_kernel' "${UART_SOURCE}")"
printf 'lk_source_anchor_default_bootargs=%s:%s\n' "platform/mt6797/include/platform/mt_reg_base.h" "$(anchor_line '^#define COMMANDLINE_TO_KERNEL.*maxcpus=5' "${REG_BASE_SOURCE}")"
printf 'lk_source_anchor_printk_disable_uart=%s:%s\n' "app/mt_boot/mt_boot.c" "$(anchor_line 'cmdline_append\("printk.disable_uart=1"\)' "${BOOT_SOURCE}")"
printf 'lk_source_anchor_boot_header_append=%s:%s\n' "app/mt_boot/mt_boot.c" "$(anchor_line 'cmdline_append\(g_boot_hdr->cmdline\)' "${BOOT_SOURCE}")"
printf 'lk_source_anchor_bootargs_write=%s:%s\n' "app/mt_boot/mt_boot.c" "$(anchor_line 'fdt_setprop_string\(fdt, offset, "bootargs"' "${BOOT_SOURCE}")"
printf 'package=%s\n' "${PACKAGE}"
printf 'dtb_sha256=%s\n' "$(sha256sum "${DTB}" | awk '{print $1}')"
printf 'system_map_sha256=%s\n' "$(sha256sum "${MAP}" | awk '{print $1}')"
printf 'lk_default_console=ttyMT3,921600n1\n'
printf 'lk_uart_selection=preloader_log_enable_and_log_port\n'
printf 'lk_console_mapping=UART1->ttyMT0;UART2->ttyMT1;UART3->ttyMT2;UART4->ttyMT3\n'
printf 'lk_selection_default=UART2_when_log_disabled_or_unknown\n'
printf 'lk_default_bootargs=console=tty0_console=ttyMT3,921600n1_root=/dev/ram_vmalloc=496M_slub_max_order=0_slub_debug=OFZPU_androidboot.hardware=mt6797_maxcpus=5\n'
printf 'lk_printk_disable_uart=appended_by_build_type_and_meta_log_policy\n'
printf 'lk_console_mutation=first_ttyMT_token_only\n'
printf 'lk_handoff_mutates_bootargs=yes\n'
printf 'lk_custom_port_before_boot_header_cmdline=yes\n'
printf 'lk_bootargs_mutation_order=static_default;runtime_appends;custom_port;boot_header_cmdline;final_atag_and_chosen_bootargs_write\n'
printf 'lk_bootargs_source=final_LK_cmdline\n'
printf 'mainline_serial0=%s\n' "${serial0}"
printf 'mainline_stdout_path=%s\n' "${stdout_path}"
printf 'mainline_console=ttyS0\n'

if [[ -n "${LIVE_IDENTITY}" ]]; then
  [[ -f "${LIVE_IDENTITY}" ]] || {
    echo "error: LIVE_IDENTITY is not a file: ${LIVE_IDENTITY}" >&2
    exit 1
  }
  live_bootargs="$(rg -m 1 '^bootargs=' "${LIVE_IDENTITY}" || true)"
  live_bootargs="${live_bootargs#bootargs=}"
  live_bootargs="$(printf '%s' "${live_bootargs}" | sed -E 's/androidboot\.serialno=[^ ]+/androidboot.serialno=<redacted>/g')"
  [[ -n "${live_bootargs}" ]] || {
    echo "error: LIVE_IDENTITY has no bootargs record" >&2
    exit 1
  }
  printf 'live_identity=%s\n' "${LIVE_IDENTITY}"
  printf 'live_identity_sha256=%s\n' "$(sha256sum "${LIVE_IDENTITY}" | awk '{print $1}')"
  printf 'live_bootargs=%s\n' "${live_bootargs// /_}"
  printf 'live_has_console_ttyMT0=%s\n' "$(grep -q 'console=ttyMT0,' <<<"${live_bootargs}" && echo yes || echo no)"
  printf 'live_has_maxcpus5=%s\n' "$(grep -q 'maxcpus=5' <<<"${live_bootargs}" && echo yes || echo no)"
  printf 'live_has_printk_disable_uart1=%s\n' "$(grep -q 'printk.disable_uart=1' <<<"${live_bootargs}" && echo yes || echo no)"
fi

printf '\n[decision]\n'
printf '%s\n' \
  'The retained LK source does not pass the DTB bootargs through unchanged.' \
  'Its non-FPGA default already contains maxcpus=5; runtime policy appends printk.disable_uart and rewrites only the first ttyMT token from preloader log settings, then appends the boot-image command line.' \
  'The fresh vendor capture contains console=ttyMT0, maxcpus=5, and printk.disable_uart=1, matching the retained LK mutation path but not proving any mainline policy.' \
  'Therefore a mainline console=ttyS0 token must be validated from a booted image; stdout-path alone is not authoritative for the console token.' \
  'The current package remains a static candidate only: runtime_mainline_boot=not_attempted' \
  'hardware_write=none'
