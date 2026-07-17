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
usage: validate-init-contract.sh --init FILE

Validate Candidate K's storage-free two-phase tty contract. The first phase
must perform exactly 20 one-second carriage-return updates without a newline;
the second must emit 12 one-second newline-terminated lines, then hold.
EOF
}

init=
while (($#)); do
	case "$1" in
		--init)
			(($# >= 2)) || die "--init requires FILE"
			init=$2
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
for command in awk grep sha256sum tail wc; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

grep -Fqx 'readonly MARKER="GEMINI_FBCON_BOUNDARY_20260717_K"' "$init" || \
	die "init lacks the exact Candidate K marker"
grep -Fqx 'readonly CR_TICKS=20' "$init" || \
	die "phase 1 must contain exactly 20 iterations"
grep -Fqx 'readonly NEWLINE_TICKS=12' "$init" || \
	die "phase 2 must contain exactly 12 iterations"
[[ "$(grep -Fxc 'tick=0' "$init")" == 2 ]] || \
	die "both phases must reset their counter at zero"
grep -Fqx 'while [ "$tick" -lt "$CR_TICKS" ]; do' "$init" || \
	die "phase 1 lacks its exact bounded loop"
grep -Fqx 'while [ "$tick" -lt "$NEWLINE_TICKS" ]; do' "$init" || \
	die "phase 2 lacks its exact bounded loop"
[[ "$(grep -Ec '^[[:space:]]*sleep 1$' "$init")" == 2 ]] || \
	die "each bounded phase must have exactly one one-second sleep site"
[[ "$(grep -Ec '^[[:space:]]*sleep 3600$' "$init")" == 2 ]] || \
	die "only failure and final static holds may sleep indefinitely"
[[ "$(grep -Fxc $'\tfor output in /dev/tty0 /dev/ttyS0; do' "$init")" == 2 ]] || \
	die "both emitters must target exactly tty0 and ttyS0"

grep -Fqx $'\t\t\tprintf \'\\r%s\' "$1" >"$output" 2>/dev/null || true' "$init" || \
	die "phase-1 emitter must use leading carriage return with no newline"
[[ "$(grep -Fxc $'\t\t\tprintf \'\\r%s\' "$1" >"$output" 2>/dev/null || true' "$init")" == 1 ]] || \
	die "no-newline tty format must occur exactly once"
grep -Fqx $'\t\t\tprintf \'\\r%s\\n\' "$1" >"$output" 2>/dev/null || true' "$init" || \
	die "phase-2 emitter must be newline terminated"
grep -Fqx $'\temit_cr "$MARKER PHASE1 CR-NO-NL $tick_label/20"' "$init" || \
	die "phase 1 lacks its fixed-width distinctive update"
[[ "$(grep -Ec '^[[:space:]]*emit_cr ' "$init")" == 1 ]] || \
	die "phase 1 must have exactly one no-newline emit call site"
grep -Fqx 'emit_line "$MARKER PHASE2 NEWLINE BEGIN 00/12"' "$init" || \
	die "phase transition marker is missing"
grep -Fqx $'\temit_line "$MARKER PHASE2 NEWLINE $tick_label/12"' "$init" || \
	die "phase 2 lacks its controlled newline line"
grep -Fqx 'emit_line "$MARKER STATIC HOLD; NO FURTHER CONSOLE WRITES"' "$init" || \
	die "final static-hold marker is missing"

sleep_first="$(grep -nF $'\tsleep 1' "$init" | awk -F: 'NR == 1 {print $1}')"
sleep_second="$(grep -nF $'\tsleep 1' "$init" | awk -F: 'NR == 2 {print $1}')"
increment_first="$(grep -nF $'\ttick=$((tick + 1))' "$init" | awk -F: 'NR == 1 {print $1}')"
increment_second="$(grep -nF $'\ttick=$((tick + 1))' "$init" | awk -F: 'NR == 2 {print $1}')"
emit_first="$(grep -nE '^[[:space:]]*emit_(cr|line) "\$MARKER PHASE[12].*\$tick_label' "$init" | awk -F: 'NR == 1 {print $1}')"
emit_second="$(grep -nE '^[[:space:]]*emit_(cr|line) "\$MARKER PHASE[12].*\$tick_label' "$init" | awk -F: 'NR == 2 {print $1}')"
((sleep_first < increment_first && increment_first < emit_first)) || \
	die "phase 1 must order sleep before increment before emit"
((sleep_second < increment_second && increment_second < emit_second)) || \
	die "phase 2 must order sleep before increment before emit"

# Both endpoint expansions are the same width; the only varying field is a
# zero-padded two-digit counter. This makes each carriage-return update cover
# one fixed console line without relying on trailing spaces.
marker=GEMINI_FBCON_BOUNDARY_20260717_K
phase1_first="$marker PHASE1 CR-NO-NL 01/20"
phase1_last="$marker PHASE1 CR-NO-NL 20/20"
phase1_width="$(printf %s "$phase1_first" | wc -c | awk '{print $1}')"
[[ "$phase1_width" == \
	"$(printf %s "$phase1_last" | wc -c | awk '{print $1}')" ]] || \
	die "phase-1 endpoint lines are not fixed width"
((phase1_width <= 72)) || \
	die "phase-1 line exceeds the conservative 72-column no-wrap limit"

grep -Fqx 'mount -t proc -o ro,nosuid,nodev,noexec proc /proc 2>/dev/null || true' \
	"$init" || die "procfs must be mounted read-only"
grep -Fqx 'mount -t sysfs -o ro,nosuid,nodev,noexec sysfs /sys 2>/dev/null || true' \
	"$init" || die "sysfs must be mounted read-only"
[[ "$(grep -Ec '^[[:space:]]*(if ! )?mount ' "$init")" == 3 ]] || \
	die "init may mount only devtmpfs, procfs and sysfs"

if grep -Eqi '/dev/(fb|mmc|block|mem|kmem|i2c)|/proc/|/sys/|(^|[^[:alnum:]_])(dd|devmem|reboot|poweroff|halt|shutdown|reset|kexec|watchdog|i2cget|i2cset|i2cdump|ifconfig|ip|route|nc|telnet|wget|tftp|udhcpc|mknod)([^[:alnum:]_]|$)' "$init"; then
	die "init contains forbidden storage, framebuffer, raw-memory, MMIO, I2C, reset, watchdog, network, USB, or sysfs-control access"
fi

final_emit_line="$(grep -nE '^[[:space:]]*emit_(cr|line) ' "$init" | tail -n 1)"
[[ "$final_emit_line" == *'emit_line "$MARKER STATIC HOLD; NO FURTHER CONSOLE WRITES"' ]] || \
	die "static hold must be the final console-write call"

printf 'validation=fbcon-newline-boundary-init-contract\n'
printf 'init_sha256=%s\n' "$(sha256sum "$init" | awk '{print $1}')"
printf 'marker=GEMINI_FBCON_BOUNDARY_20260717_K\n'
printf 'phase1=20x-one-second-fixed-width-leading-cr-no-newline\n'
printf 'phase1_width=%s\n' "$phase1_width"
printf 'phase2=transition-plus-12x-one-second-newline-terminated\n'
printf 'final_state=static-hold-no-further-console-writes\n'
printf 'tty_targets=tty0,ttyS0\n'
printf 'tracked_init_forbidden_storage_fbdev_raw_memory_mmio_i2c_reset_watchdog_network_usb_control_access=none\n'
printf 'tracked_init_persistent_or_control_write=none\n'
