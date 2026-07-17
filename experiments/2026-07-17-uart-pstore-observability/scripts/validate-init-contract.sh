#!/usr/bin/env bash
# Source-contract patterns intentionally match literal, unexpanded shell text.
# shellcheck disable=SC2016

set -euo pipefail
export LC_ALL=C

die() {
	echo "error: $*" >&2
	exit 2
}

usage() {
	cat >&2 <<'EOF'
usage: validate-init-contract.sh --init FILE --usb-report FILE

Validate Candidate L's storage-free pstore, UART, bounded TOPRGU expiry, and
optional USB diagnostic contract.
EOF
}

init=
usb_report=
while (($#)); do
	case "$1" in
		--init)
			(($# >= 2)) || die "--init requires FILE"
			init=$2
			shift 2
			;;
		--usb-report)
			(($# >= 2)) || die "--usb-report requires FILE"
			usb_report=$2
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			usage
			die "unknown option: $1"
			;;
	esac
done

[[ -s "$init" ]] || die "--init must name a non-empty file"
[[ -s "$usb_report" ]] || die "--usb-report must name a non-empty file"
for command in grep sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

grep -Fqx 'readonly MARKER="GEMINI_OBSERVABILITY_20260717_L"' "$init" || \
	die "init lacks the exact Candidate L marker"
grep -Fqx 'readonly WATCHDOG_WAIT_SECONDS=10' "$init" || \
	die "watchdog discovery must be bounded to 10 seconds"
grep -Fqx 'readonly WATCHDOG_TIMEOUT_SECONDS=31' "$init" || \
	die "advertised watchdog timeout must remain 31 seconds"
grep -Fqx 'readonly WATCHDOG_FAILURE_SECONDS=40' "$init" || \
	die "watchdog failure boundary must remain 40 seconds"
grep -Fqx $'if exec 3>/dev/watchdog0; then' "$init" || \
	die "init must arm TOPRGU by holding watchdog fd 3 open"
[[ "$(grep -Fxc $'if exec 3>/dev/watchdog0; then' "$init")" == 1 ]] || \
	die "watchdog may be opened at exactly one source site"
grep -Fqx $'\tif printf '\''.'\'' >&3; then' "$init" || \
	die "init must send one post-open ownership-handoff ping"
[[ "$(grep -Fxc $'\tif printf '\''.'\'' >&3; then' "$init")" == 1 ]] || \
	die "watchdog ownership-handoff ping must occur exactly once"
[[ "$(grep -Foc '>&3' "$init")" == 1 ]] || \
	die "watchdog fd 3 may have exactly one write redirection"
if grep -Eq '/(proc/(self|[0-9]+)/fd|dev/fd)/3' "$init"; then
	die "watchdog fd 3 must not be reached through an alias path"
fi
grep -Fqx $'\t\tprintf \'<6>%s\\n\' "$*" >/dev/kmsg 2>/dev/null || true' "$init" || \
	die "markers must enter the kernel console through /dev/kmsg"
if grep -Fq '>/dev/pmsg0' "$init"; then
	die "pmsg is not cross-version recoverable and must not be written"
fi
grep -Fqx $'\tfor output in /dev/console /dev/tty0 /dev/ttyS0; do' "$init" || \
	die "visible markers must cover console, fbcon and corrected UART0"
grep -Fqx 'for watchdog_attribute in identity timeout pretimeout status; do' "$init" || \
	die "watchdog identity and timing attributes must be recorded before open"
grep -Fqx $'\t\trecord "$MARKER watchdog_${watchdog_attribute}=${watchdog_attribute_value:-unreadable}"' \
	"$init" || die "readable watchdog sysfs attributes must enter the durable log"

grep -Fqx 'mount -t proc -o ro,nosuid,nodev,noexec proc /proc 2>/dev/null || true' \
	"$init" || die "procfs must be mounted read-only"
grep -Fqx 'mount -t sysfs -o ro,nosuid,nodev,noexec sysfs /sys 2>/dev/null || true' \
	"$init" || die "sysfs must be mounted read-only"
[[ "$(grep -Ec '^[[:space:]]*(if ! )?mount ' "$init")" == 3 ]] || \
	die "init may mount only devtmpfs, procfs and sysfs"

if grep -Eqi '/dev/(fb|mmc|block|mem|kmem|i2c)|(^|[^[:alnum:]_])(dd|devmem|reboot|poweroff|halt|shutdown|kexec|i2cget|i2cset|i2cdump|mknod|sync)([^[:alnum:]_]|$)' \
	"$init" "$usb_report"; then
	die "initramfs contains forbidden storage, framebuffer, raw-memory, I2C, or generic reset access"
fi
if grep -Eq '^[[:space:]]*watchdog([[:space:]]|$)' "$init"; then
	die "a watchdog userspace applet could ping or close the diagnostic fd"
fi
grep -Fq 'ip link set usb0 up' "$init" || die "optional USB link setup is missing"
grep -Fq 'nc -ll -p 2323 -e /bin/usb-report' "$init" || \
	die "optional USB diagnostic report is missing"
grep -Fqx 'printf '\''%s\n'\'' "storage_access=none"' "$usb_report" || \
	die "USB report must disclose its storage-free contract"
grep -Fqx 'printf '\''%s\n'\'' "interactive_shell=none"' "$usb_report" || \
	die "USB report must explicitly deny an interactive shell"
if grep -Eqi 'exec[[:space:]]+/bin/(ba)?sh|nc[^#]*-e[[:space:]]+/bin/(ba)?sh|(^|[^[:alnum:]_])(ash|bash|sh)[[:space:]]+-[cil]' \
	"$init" "$usb_report"; then
	die "initramfs must not expose an interactive command interpreter"
fi

printf 'validation=uart-pstore-observability-init-contract\n'
printf 'init_sha256=%s\n' "$(sha256sum "$init" | awk '{print $1}')"
printf 'usb_report_sha256=%s\n' "$(sha256sum "$usb_report" | awk '{print $1}')"
printf 'marker=GEMINI_OBSERVABILITY_20260717_L\n'
printf 'marker_path=/dev/kmsg-to-Gemian-primary-console-ramoops\n'
printf 'visible_marker_paths=/dev/console,/dev/tty0,/dev/ttyS0\n'
printf 'watchdog_action=open-fd3,one-handoff-ping,hold-without-further-pings,no-PSCI-reboot\n'
printf 'watchdog_timeout_seconds=31-advertised\n'
printf 'watchdog_failure_boundary_seconds=40-after-handoff-ping\n'
printf 'storage_access=none\n'
printf 'interactive_shell=none\n'
printf 'generic_reset_command=none\n'
