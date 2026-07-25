#!/usr/bin/env bash

# Mutation strings intentionally contain unexpanded shell expressions.
# shellcheck disable=SC2016

set -euo pipefail
export LC_ALL=C
umask 077

readonly EXPECTED_MUTATIONS=75

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --baseline EXACT_Y_ARTIFACT\n' "$0" >&2; }

baseline=
while (($#)); do
	case "$1" in
	--baseline)
		(($# >= 2)) || die "$1 requires a value"
		baseline=$2
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux && -d "$baseline" && ! -L "$baseline" ]] || \
	die 'run in Linux with the exact Candidate Y artifact'
case "$(uname -m)" in
aarch64|arm64) ;;
*) die 'exact BusyBox mutation controls require a Linux aarch64 host' ;;
esac
for command in awk bash basename chmod cpio cp find gzip ln mkdir mktemp mv \
	python3 rm sha256sum sort touch uname xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
y_validator="$script_dir/validate-y-baseline.py"
initramfs_builder="$script_dir/build-initramfs.sh"
initramfs_validator="$script_dir/validate-initramfs.py"
dispatch_validator="$script_dir/validate-ash-dispatch.py"
boot_builder="$script_dir/build-boot-from-y.py"
boot_validator="$script_dir/validate-boot.py"
top_builder="$script_dir/build-keyboard-reboot-dispatch-candidate.sh"
final_validator="$script_dir/validate-final-artifact.py"
y_boot="$baseline/gemini-keyboard-typed-watchdog-reboot.boot.img"
y_initramfs="$baseline/gemini-keyboard-typed-watchdog-reboot-initramfs.img"
y_dtb="$baseline/mt6797-gemini-pda-keyboard-typed-watchdog-reboot.dtb"

workdir="$(mktemp -d /tmp/candidate-z-mutations.XXXXXX)"
cleanup() { [[ ! -d "$workdir" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT

passed=0
expect_fail() {
	local name=$1
	shift
	set +e
	"$@" >"$workdir/$name.out" 2>"$workdir/$name.err"
	local rc=$?
	set -e
	[[ "$rc" == 2 ]] || \
		die "mutation was not rejected with status 2: $name (status $rc)"
	passed=$((passed + 1))
}

replace_once() {
	local path=$1
	local old=$2
	local new=$3
	python3 -c '
import pathlib, sys
path = pathlib.Path(sys.argv[1])
old, new = sys.argv[2], sys.argv[3]
text = path.read_text(encoding="utf-8")
if text.count(old) != 1:
    raise SystemExit(f"expected one mutation target in {path}, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
' "$path" "$old" "$new"
}

delete_line_once() {
	replace_once "$1" "$2"$'\n' ''
}

insert_before_once() {
	replace_once "$1" "$2" "$3"$'\n'"$2"
}

insert_after_once() {
	replace_once "$1" "$2" "$2"$'\n'"$3"
}

move_matching_line() {
	local path=$1
	local needle=$2
	local anchor=$3
	local direction=$4
	python3 -c '
import pathlib, sys
path = pathlib.Path(sys.argv[1])
needle, anchor, direction = sys.argv[2:5]
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
moving = [index for index, line in enumerate(lines) if needle in line]
if len(moving) != 1:
    raise SystemExit(f"expected one moving line in {path}, found {len(moving)}")
line = lines.pop(moving[0])
anchors = [index for index, value in enumerate(lines) if anchor in value]
if len(anchors) != 1:
    raise SystemExit(f"expected one anchor line in {path}, found {len(anchors)}")
offset = 1 if direction == "after" else 0
lines.insert(anchors[0] + offset, line)
path.write_text("".join(lines), encoding="utf-8")
' "$path" "$needle" "$anchor" "$direction"
}

remove_visible_countdown() {
	local path=$1
	python3 -c '
import pathlib, sys
path = pathlib.Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
out = []
removed = 0
index = 0
while index < len(lines):
    line = lines[index]
    if "printf" in line and (
        "Candidate Z: hardware watchdog armed" in line
        or "Candidate Z: reset overdue" in line
    ):
        indent = line[:len(line) - len(line.lstrip("\t "))]
        out.append(indent + ": # visible countdown removed\n")
        removed += 1
        if "Candidate Z: reset overdue" in line and line.rstrip().endswith("\\"):
            index += 2
            continue
    else:
        out.append(line)
    index += 1
if removed != 3:
    raise SystemExit(f"expected three countdown printfs in {path}, found {removed}")
path.write_text("".join(out), encoding="utf-8")
' "$path"
}

pack_fixture() {
	local fixture=$1
	(
		cd "$fixture/root"
		find . -print0 | sort -z | cpio --null --create --format=newc \
			--owner=0:0 --reproducible --quiet
	) | gzip -n -9 >"$fixture/candidate.img"
}

prepare_archive_fixture() {
	local fixture=$1
	mkdir -p "$fixture/root" "$fixture/source"
	gzip -dc "$workdir/z-initramfs.img" | \
		(cd "$fixture/root" && cpio -idmu --quiet)
	# cpio leaves this pre-created directory at the caller's umask rather than
	# restoring the canonical archived `.` mode.
	chmod 0755 "$fixture/root"
	cp "$experiment_dir/initramfs/"{init,local-shell,reboot,x-record,reboot-dispatch.env} \
		"$fixture/source/"
}

archive_mutation() {
	local name=$1
	local fixture="$workdir/archive-$name"
	local root_init="$fixture/root/init"
	local root_shell="$fixture/root/bin/local-shell"
	local root_reboot="$fixture/root/bin/reboot"
	local root_record="$fixture/root/bin/x-record"
	local root_dispatch="$fixture/root/bin/reboot-dispatch.env"
	local source_init="$fixture/source/init"
	local source_shell="$fixture/source/local-shell"
	local source_reboot="$fixture/source/reboot"
	local source_record="$fixture/source/x-record"
	local source_dispatch="$fixture/source/reboot-dispatch.env"
	local target

	prepare_archive_fixture "$fixture"
	case "$name" in
	dispatch_alias_removed)
		chmod 0644 "$root_dispatch"
		for target in "$root_dispatch" "$source_dispatch"; do
			replace_once "$target" "alias reboot='/bin/reboot'" '# alias removed'
		done
		chmod 0444 "$root_dispatch"
		;;
	dispatch_member_missing)
		rm -- "$root_dispatch"
		;;
	dispatch_env_retargeted)
		for target in "$root_shell" "$source_shell"; do
			replace_once "$target" \
				'readonly DISPATCH_ENV=/bin/reboot-dispatch.env' \
				'readonly DISPATCH_ENV=/bin/wrong-dispatch.env'
		done
		;;
	dispatch_env_not_exported)
		for target in "$root_shell" "$source_shell"; do
			delete_line_once "$target" 'export ENV'
		done
		;;
	dispatch_late_unalias)
		chmod 0644 "$root_dispatch"
		for target in "$root_dispatch" "$source_dispatch"; do
			insert_after_once "$target" "alias reboot='/bin/reboot'" 'unalias reboot'
		done
		chmod 0444 "$root_dispatch"
		;;
	dispatch_alias_busybox_target)
		chmod 0644 "$root_dispatch"
		for target in "$root_dispatch" "$source_dispatch"; do
			replace_once "$target" "alias reboot='/bin/reboot'" \
				"alias reboot='/bin/busybox reboot'"
		done
		chmod 0444 "$root_dispatch"
		;;
	exec_open_regression)
		for target in "$root_reboot" "$source_reboot"; do
			replace_once "$target" \
				'if watchdog_session 3>/dev/watchdog0; then' \
				'if exec 3>/dev/watchdog0; then'
		done
		;;
	preflight_after_open)
		for target in "$root_reboot" "$source_reboot"; do
			move_matching_line "$target" \
				'[ "$identity" = mtk-wdt ] || refuse watchdog-identity-mismatch' \
				'if watchdog_session 3>/dev/watchdog0; then' after
		done
		;;
	validated_before_final_gate)
		for target in "$root_reboot" "$source_reboot"; do
			move_matching_line "$target" 'manual_reboot=validated class_device=' \
				'case "$pretimeout" in' before
		done
		;;
	second_ping_spaced)
		for target in "$root_reboot" "$source_reboot"; do
			insert_before_once "$target" \
				'/bin/x-record "manual_reboot=armed watchdog0=armed' \
				$'\tprintf \'.\' >& 3'
		done
		;;
	second_ping_variable)
		for target in "$root_reboot" "$source_reboot"; do
			insert_before_once "$target" \
				'/bin/x-record "manual_reboot=armed watchdog0=armed' \
				$'\twatchdog_fd=3\n\tprintf \'.\' >&"$watchdog_fd"'
		done
		;;
	fd3_close_alternate)
		for target in "$root_reboot" "$source_reboot"; do
			insert_before_once "$target" \
				'/bin/x-record "manual_reboot=armed watchdog0=armed' $'\t: 3>&-'
		done
		;;
	bare_busybox_reboot)
		for target in "$root_reboot" "$source_reboot"; do
			insert_before_once "$target" \
				$'\thold_armed \'manual_reboot=watchdog-expiry-failed' \
				$'\tbusybox reboot -n -f'
		done
		;;
	command_reboot)
		for target in "$root_reboot" "$source_reboot"; do
			insert_before_once "$target" \
				$'\thold_armed \'manual_reboot=watchdog-expiry-failed' \
				$'\tcommand reboot -f'
		done
		;;
	busybox_sync)
		for target in "$root_reboot" "$source_reboot"; do
			insert_before_once "$target" \
				$'\thold_armed \'manual_reboot=watchdog-expiry-failed' \
				$'\tbusybox sync'
		done
		;;
	sysrq_reboot)
		for target in "$root_reboot" "$source_reboot"; do
			insert_before_once "$target" \
				$'\thold_armed \'manual_reboot=watchdog-expiry-failed' \
				$'\t/bin/busybox echo b >/proc/sysrq-trigger'
		done
		;;
	countdown_removed)
		for target in "$root_reboot" "$source_reboot"; do
			remove_visible_countdown "$target"
		done
		;;
	countdown_sleep_removed)
		for target in "$root_reboot" "$source_reboot"; do
			replace_once "$target" $'\t\t/bin/busybox sleep 1' $'\t\t/bin/busybox true'
		done
		;;
	countdown_redirected)
		for target in "$root_reboot" "$source_reboot"; do
			replace_once "$target" \
				$'\tprintf \'Candidate Z: hardware watchdog armed; reset expected in %2s seconds.\' "$remaining"' \
				$'\tprintf \'Candidate Z: hardware watchdog armed; reset expected in %2s seconds.\' "$remaining" >/dev/null'
		done
		;;
	recorder_tty1)
		for target in "$root_record" "$source_record"; do
			replace_once "$target" 'output=/dev/ttyS0' 'output=/dev/tty1'
		done
		;;
	background_console)
		for target in "$root_init" "$source_init"; do
			insert_before_once "$target" 'exec /bin/busybox init' \
				"printf '%s\\n' 'background leak' >/dev/console"
		done
		;;
	dispatch_oracle_changed)
		for target in "$root_shell" "$source_shell"; do
			replace_once "$target" "ash -ic 'type reboot'" "ash -ic 'type /bin/reboot'"
		done
		;;
	dispatch_failure_hold_removed)
		for target in "$root_shell" "$source_shell"; do
			replace_once "$target" $'\t\t/bin/busybox sleep 3600' \
				$'\t\t/bin/busybox true'
		done
		;;
	request_removed)
		for target in "$root_reboot" "$source_reboot"; do
			delete_line_once "$target" \
				"/bin/x-record 'manual_reboot=requested trigger=bare-reboot dispatch=absolute-wrapper method=mtk-wdt-expiry watchdog_armed=no storage_access=none'"
		done
		;;
	irq_gate_removed)
		for target in "$root_reboot" "$source_reboot"; do
			delete_line_once "$target" \
				'[ ! -e "$LIVE_WATCHDOG/interrupts" ] || refuse live-watchdog-interrupts-present'
		done
		;;
	irq_extended_gate_removed)
		for target in "$root_reboot" "$source_reboot"; do
			replace_once "$target" \
				$'[ ! -e "$LIVE_WATCHDOG/interrupts-extended" ] || \\\n\trefuse live-watchdog-interrupts-extended-present' \
				': # interrupts-extended gate removed'
		done
		;;
	ramoops_gate_removed)
		for target in "$root_reboot" "$source_reboot"; do
			delete_line_once "$target" \
				'[ "$ramoops_driver" = ramoops ] || refuse ramoops-driver-mismatch'
		done
		;;
	class_platform_gate_removed)
		for target in "$root_reboot" "$source_reboot"; do
			delete_line_once "$target" \
				'[ "$class_device" = "$platform_device" ] || refuse watchdog-class-platform-mismatch'
		done
		;;
	timeout_gate_removed)
		for target in "$root_reboot" "$source_reboot"; do
			delete_line_once "$target" \
				'[ "$timeout" = "$WATCHDOG_TIMEOUT_SECONDS" ] || refuse watchdog-timeout-mismatch'
		done
		;;
	pretimeout_gate_removed)
		for target in "$root_reboot" "$source_reboot"; do
			replace_once "$target" \
				$'case "$pretimeout" in\n\t0|unavailable) ;;\n\t*) refuse watchdog-pretimeout-mismatch ;;\nesac' \
				': # pretimeout gate removed'
		done
		;;
	trap_removed)
		for target in "$root_reboot" "$source_reboot"; do
			delete_line_once "$target" "trap '' HUP INT QUIT TERM TSTP"
		done
		;;
	magic_close)
		for target in "$root_reboot" "$source_reboot"; do
			replace_once "$target" "printf '.' >&3" "printf 'V' >&3"
		done
		;;
	failure_hold_removed)
		for target in "$root_reboot" "$source_reboot"; do
			replace_once "$target" \
				$'\thold_armed \'manual_reboot=watchdog-expiry-failed boundary_seconds=40 fd3=retained further_pings=none\'' \
				$'\treturn 0'
		done
		;;
	open_failure_refusal_removed)
		for target in "$root_reboot" "$source_reboot"; do
				replace_once "$target" $'\trefuse watchdog0-open-failed' $'\t:'
			done
		;;
	refuse_body_exit_removed)
		for target in "$root_reboot" "$source_reboot"; do
			replace_once "$target" $'\texit 1' $'\treturn 1'
		done
		;;
	refuse_body_marker_removed)
		for target in "$root_reboot" "$source_reboot"; do
			replace_once "$target" \
				$'\t/bin/x-record "manual_reboot=refused reason=$reason watchdog_armed=no"' \
				$'\t:'
		done
		;;
	hold_armed_body_hold_removed)
		for target in "$root_reboot" "$source_reboot"; do
			replace_once "$target" \
				$'\tprintf \'\\nCandidate Z: watchdog reset is overdue; fd3 remains open with no further writes.\\n\' >&2\n\twhile :; do\n\t\t/bin/busybox sleep 3600\n\tdone' \
				$'\tprintf \'\\nCandidate Z: watchdog reset is overdue; fd3 remains open with no further writes.\\n\' >&2\n\treturn 0'
		done
		;;
	hold_after_return_body_hold_removed)
		for target in "$root_reboot" "$source_reboot"; do
			replace_once "$target" \
				$'\tprintf \'\\nCandidate Z: watchdog session returned unexpectedly; fd3 is closed; STATIC HOLD.\\n\' >&2\n\twhile :; do\n\t\t/bin/busybox sleep 3600\n\tdone' \
				$'\tprintf \'\\nCandidate Z: watchdog session returned unexpectedly; fd3 is closed; STATIC HOLD.\\n\' >&2\n\treturn 0'
		done
		;;
	ping_failure_hold_removed)
		for target in "$root_reboot" "$source_reboot"; do
			replace_once "$target" \
				$'\t\thold_armed \'manual_reboot=armed-uncertain watchdog0=handoff-ping-failed fd3=retained further_pings=none\'' \
				$'\t\t:'
		done
		;;
	session_break_added)
		for target in "$root_reboot" "$source_reboot"; do
			insert_after_once "$target" $'\t\t/bin/busybox sleep 1' $'\t\tbreak'
		done
		;;
	session_return_hold_removed)
		for target in "$root_reboot" "$source_reboot"; do
			replace_once "$target" \
				$'\thold_after_session_return \'manual_reboot=watchdog-session-returned status=zero\'' \
				$'\t:'
		done
		;;
	automatic_watchdog)
		for target in "$root_init" "$source_init"; do
			insert_before_once "$target" 'exec /bin/busybox init' \
				'exec 9>/dev/watchdog0'
		done
		;;
	automatic_reboot)
		for target in "$root_init" "$source_init"; do
			insert_before_once "$target" 'exec /bin/busybox init' \
				'/bin/busybox reboot -n -f'
			done
		;;
	automatic_watchdog_local_shell)
		for target in "$root_shell" "$source_shell"; do
			insert_before_once "$target" 'exec /bin/busybox ash -i' \
				'exec 9>/dev/watchdog0'
		done
		;;
	automatic_reboot_local_shell)
		for target in "$root_shell" "$source_shell"; do
			insert_before_once "$target" 'exec /bin/busybox ash -i' \
				'/bin/busybox reboot -n -f'
		done
		;;
	marker_changed)
		for target in "$root_record" "$source_record"; do
			replace_once "$target" 'GEMINI_KEYBOARD_REBOOT_DISPATCH_20260719_Z' \
				'GEMINI_BAD_Z'
		done
		;;
	probe_changed)
		insert_after_once "$fixture/root/bin/x-probe" \
			"/bin/x-record 'probe=complete shell=independent manual_reboot=available'" \
			'# inherited probe mutation'
		;;
	extra_member)
		printf '%s\n' unexpected >"$fixture/root/unexpected"
		;;
	reboot_mode_changed)
		chmod 0700 "$root_reboot"
		;;
	dispatch_mode_changed)
		chmod 0644 "$root_dispatch"
		;;
	*) die "unknown archive mutation: $name" ;;
	esac

	find "$fixture/root" -exec touch -h -d @0 {} +
	pack_fixture "$fixture"
	expect_fail "$name" python3 "$initramfs_validator" --baseline "$y_initramfs" \
		--candidate "$fixture/candidate.img" --source-dir "$fixture/source"
	if grep -Eq 'hash-pinned overlay source changed|archive/source mismatch' \
		"$workdir/$name.err"; then
		die "mutation was masked by the source pin/equality backstop: $name"
	fi
}

# D/W/F/P/T cover dispatch, watchdog ownership/control flow, forbidden
# fallbacks, foreground progress, and background tty isolation respectively.
archive_mutations=(
	dispatch_alias_removed
	dispatch_member_missing
	dispatch_env_retargeted
	dispatch_env_not_exported
	dispatch_late_unalias
	dispatch_alias_busybox_target
	exec_open_regression
	preflight_after_open
	validated_before_final_gate
	second_ping_spaced
	second_ping_variable
	fd3_close_alternate
	bare_busybox_reboot
	command_reboot
	busybox_sync
	sysrq_reboot
	countdown_removed
	countdown_sleep_removed
	countdown_redirected
	recorder_tty1
	background_console
	dispatch_oracle_changed
	dispatch_failure_hold_removed
	request_removed
	irq_gate_removed
	irq_extended_gate_removed
	ramoops_gate_removed
	class_platform_gate_removed
	timeout_gate_removed
	pretimeout_gate_removed
	trap_removed
	magic_close
	failure_hold_removed
	open_failure_refusal_removed
	refuse_body_exit_removed
	refuse_body_marker_removed
	hold_armed_body_hold_removed
	hold_after_return_body_hold_removed
	ping_failure_hold_removed
	session_break_added
	session_return_hold_removed
	automatic_watchdog
	automatic_reboot
	automatic_watchdog_local_shell
	automatic_reboot_local_shell
	marker_changed
	probe_changed
	extra_member
	reboot_mode_changed
	dispatch_mode_changed
)

# Positive controls bind all later mutations to an exact Y-derived Z archive,
# exact-BusyBox dynamic dispatch result, and exact-Y kernel/DT container.
python3 "$y_validator" --baseline "$baseline" >"$workdir/y-baseline-validation.txt"
bash "$initramfs_builder" --baseline "$y_initramfs" \
	--output "$workdir/z-initramfs.img" \
	--dispatch-result "$workdir/ash-dispatch-validation.txt" \
	>"$workdir/initramfs-build.txt"
python3 "$initramfs_validator" --baseline "$y_initramfs" \
	--candidate "$workdir/z-initramfs.img" --source-dir "$experiment_dir/initramfs" \
	>"$workdir/initramfs-validation.txt"
python3 "$dispatch_validator" --initramfs "$workdir/z-initramfs.img" \
	--verify-saved "$workdir/ash-dispatch-validation.txt" \
	>"$workdir/dispatch-positive.txt"
python3 "$boot_builder" --y-boot "$y_boot" --y-initramfs "$y_initramfs" \
	--z-initramfs "$workdir/z-initramfs.img" --output "$workdir/z.boot.img" \
	>"$workdir/boot-build.txt"
python3 "$boot_validator" --y-boot "$y_boot" --y-initramfs "$y_initramfs" \
	--z-boot "$workdir/z.boot.img" --z-initramfs "$workdir/z-initramfs.img" \
	--dtb "$y_dtb" >"$workdir/boot-validation.txt"

for mutation in "${archive_mutations[@]}"; do
	archive_mutation "$mutation"
done

# Source and baseline symlinks must fail independently of archive semantics.
source_reboot_fixture="$workdir/source-reboot-symlink"
mkdir "$source_reboot_fixture"
cp "$experiment_dir/initramfs/"{init,local-shell,x-record,reboot-dispatch.env} \
	"$source_reboot_fixture/"
ln -s "$experiment_dir/initramfs/reboot" "$source_reboot_fixture/reboot"
expect_fail source_reboot_symlink python3 "$initramfs_validator" \
	--baseline "$y_initramfs" --candidate "$workdir/z-initramfs.img" \
	--source-dir "$source_reboot_fixture"

source_dispatch_fixture="$workdir/source-dispatch-symlink"
mkdir "$source_dispatch_fixture"
cp "$experiment_dir/initramfs/"{init,local-shell,reboot,x-record} \
	"$source_dispatch_fixture/"
ln -s "$experiment_dir/initramfs/reboot-dispatch.env" \
	"$source_dispatch_fixture/reboot-dispatch.env"
expect_fail source_dispatch_symlink python3 "$initramfs_validator" \
	--baseline "$y_initramfs" --candidate "$workdir/z-initramfs.img" \
	--source-dir "$source_dispatch_fixture"

baseline_link="$workdir/y-baseline-link"
ln -s "$baseline" "$baseline_link"
expect_fail baseline_symlink python3 "$y_validator" --baseline "$baseline_link"

# Exercise the dynamic validator itself, not only the static initramfs gate.
dispatch_member_fixture="$workdir/dispatch-member-dynamic"
mkdir "$dispatch_member_fixture"
prepare_archive_fixture "$dispatch_member_fixture"
chmod 0644 "$dispatch_member_fixture/root/bin/reboot-dispatch.env"
replace_once "$dispatch_member_fixture/root/bin/reboot-dispatch.env" \
	"alias reboot='/bin/reboot'" "alias reboot='/bin/busybox reboot'"
chmod 0444 "$dispatch_member_fixture/root/bin/reboot-dispatch.env"
find "$dispatch_member_fixture/root" -exec touch -h -d @0 {} +
pack_fixture "$dispatch_member_fixture"
expect_fail dispatch_validator_member_mutated python3 "$dispatch_validator" \
	--initramfs "$dispatch_member_fixture/candidate.img"

dispatch_export_fixture="$workdir/dispatch-export-dynamic"
mkdir "$dispatch_export_fixture"
prepare_archive_fixture "$dispatch_export_fixture"
delete_line_once "$dispatch_export_fixture/root/bin/local-shell" 'export ENV'
find "$dispatch_export_fixture/root" -exec touch -h -d @0 {} +
pack_fixture "$dispatch_export_fixture"
expect_fail dispatch_validator_export_removed python3 "$dispatch_validator" \
	--initramfs "$dispatch_export_fixture/candidate.img"

# Output collision gates are separate from content validation.
existing_boot="$workdir/existing.boot.img"
printf '%s\n' occupied >"$existing_boot"
expect_fail boot_output_overwrite python3 "$boot_builder" --y-boot "$y_boot" \
	--y-initramfs "$y_initramfs" --z-initramfs "$workdir/z-initramfs.img" \
	--output "$existing_boot"

existing_initramfs="$workdir/existing-initramfs.img"
printf '%s\n' occupied >"$existing_initramfs"
expect_fail initramfs_output_overwrite bash "$initramfs_builder" \
	--baseline "$y_initramfs" --output "$existing_initramfs" \
	--dispatch-result "$workdir/nonexistent-dispatch-result.txt"

existing_dispatch="$workdir/existing-dispatch-result.txt"
printf '%s\n' occupied >"$existing_dispatch"
expect_fail initramfs_dispatch_output_overwrite bash "$initramfs_builder" \
	--baseline "$y_initramfs" --output "$workdir/nonexistent-initramfs.img" \
	--dispatch-result "$existing_dispatch"

boot_mutation() {
	local name=$1
	local target="$workdir/$name.boot.img"
	cp "$workdir/z.boot.img" "$target"
	case "$name" in
	kernel_byte)
		python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); d=bytearray(p.read_bytes()); d[4096]^=1; p.write_bytes(d)' "$target"
		;;
	unrelated_header)
		python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); d=bytearray(p.read_bytes()); d[48]^=1; p.write_bytes(d)' "$target"
		;;
	trailing_byte)
		python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_bytes(p.read_bytes()+b"x")' "$target"
		;;
	canonical_id)
		python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); d=bytearray(p.read_bytes()); d[576]^=1; p.write_bytes(d)' "$target"
		;;
	*) die "unknown boot mutation: $name" ;;
	esac
	expect_fail "$name" python3 "$boot_validator" --y-boot "$y_boot" \
		--y-initramfs "$y_initramfs" --z-boot "$target" \
		--z-initramfs "$workdir/z-initramfs.img" --dtb "$y_dtb"
}
for mutation in kernel_byte unrelated_header trailing_byte canonical_id; do
	boot_mutation "$mutation"
done

bad_dtb="$workdir/bad.dtb"
cp "$y_dtb" "$bad_dtb"
python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); d=bytearray(p.read_bytes()); d[-1]^=1; p.write_bytes(d)' "$bad_dtb"
expect_fail dtb_substitution python3 "$boot_validator" --y-boot "$y_boot" \
	--y-initramfs "$y_initramfs" --z-boot "$workdir/z.boot.img" \
	--z-initramfs "$workdir/z-initramfs.img" --dtb "$bad_dtb"

bad_z_initramfs="$workdir/bad-z-initramfs.img"
cp "$workdir/z-initramfs.img" "$bad_z_initramfs"
python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); d=bytearray(p.read_bytes()); d[-1]^=1; p.write_bytes(d)' "$bad_z_initramfs"
expect_fail ramdisk_argument_mismatch python3 "$boot_validator" --y-boot "$y_boot" \
	--y-initramfs "$y_initramfs" --z-boot "$workdir/z.boot.img" \
	--z-initramfs "$bad_z_initramfs" --dtb "$y_dtb"

# A complete final artifact is the positive control for inventory, manifest,
# component rerun, mode, symlink, basename, saved-dispatch, and race mutations.
mkdir "$workdir/final-output"
bash "$top_builder" --baseline "$baseline" --output-parent "$workdir/final-output" \
	>"$workdir/top-builder.out"
final_artifact="$(find "$workdir/final-output" -mindepth 1 -maxdepth 1 \
	-type d -name 'candidate-Z-*' -print -quit)"
[[ -n "$final_artifact" ]] || die 'positive-control final artifact was not produced'
python3 "$final_validator" --artifact "$final_artifact" --baseline "$baseline" \
	>"$workdir/final-positive.txt"

copy_final_fixture() {
	local name=$1
	local parent
	local target
	parent="$workdir/final-$name-parent"
	target="$parent/$(basename -- "$final_artifact")"
	mkdir "$parent"
	cp -a "$final_artifact" "$target"
	printf '%s\n' "$target"
}

rewrite_final_manifest() {
	local artifact=$1
	(
		cd "$artifact"
		find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
	) >"$artifact/SHA256SUMS"
	chmod 0600 "$artifact/SHA256SUMS"
}

final_inventory="$(copy_final_fixture inventory)"
printf '%s\n' unexpected >"$final_inventory/unexpected"
expect_fail final_inventory python3 "$final_validator" \
	--artifact "$final_inventory" --baseline "$baseline"

final_mode="$(copy_final_fixture mode)"
chmod 0644 "$final_mode/input-event-capture"
expect_fail final_mode python3 "$final_validator" \
	--artifact "$final_mode" --baseline "$baseline"

final_symlink="$(copy_final_fixture symlink)"
rm -- "$final_symlink/provenance.txt"
ln -s "$final_artifact/provenance.txt" "$final_symlink/provenance.txt"
expect_fail final_symlink python3 "$final_validator" \
	--artifact "$final_symlink" --baseline "$baseline"

final_manifest="$(copy_final_fixture manifest)"
printf '%s\n' malformed >>"$final_manifest/SHA256SUMS"
expect_fail final_manifest python3 "$final_validator" \
	--artifact "$final_manifest" --baseline "$baseline"

final_saved_dispatch="$(copy_final_fixture saved-dispatch)"
printf '%s\n' tampered >>"$final_saved_dispatch/ash-dispatch-validation.txt"
rewrite_final_manifest "$final_saved_dispatch"
expect_fail final_saved_dispatch python3 "$final_validator" \
	--artifact "$final_saved_dispatch" --baseline "$baseline"

final_source_build="$(copy_final_fixture source-build)"
printf '%s\n' tampered >>"$final_source_build/source-build.json"
rewrite_final_manifest "$final_source_build"
expect_fail final_source_build python3 "$final_validator" \
	--artifact "$final_source_build" --baseline "$baseline"

final_helper="$(copy_final_fixture helper)"
printf x >>"$final_helper/input-event-capture"
rewrite_final_manifest "$final_helper"
expect_fail final_helper python3 "$final_validator" \
	--artifact "$final_helper" --baseline "$baseline"

final_input_tree="$(copy_final_fixture input-tree)"
printf '%s\n' tampered >>"$final_input_tree/input-tree.sha256"
rewrite_final_manifest "$final_input_tree"
expect_fail final_input_tree python3 "$final_validator" \
	--artifact "$final_input_tree" --baseline "$baseline"

final_provenance="$(copy_final_fixture provenance-duplicate)"
printf '%s\n' 'software_reboot_fallback=generic' >>"$final_provenance/provenance.txt"
rewrite_final_manifest "$final_provenance"
expect_fail final_provenance_duplicate python3 "$final_validator" \
	--artifact "$final_provenance" --baseline "$baseline"

final_basename_parent="$workdir/final-basename-parent"
final_basename="$final_basename_parent/candidate-Z-wrong-name"
mkdir "$final_basename_parent"
cp -a "$final_artifact" "$final_basename"
expect_fail final_basename python3 "$final_validator" \
	--artifact "$final_basename" --baseline "$baseline"

expect_fail final_output_race bash "$top_builder" --baseline "$baseline" \
	--output-parent "$workdir/final-output"

((passed == EXPECTED_MUTATIONS)) || \
	die "internal mutation count mismatch: expected $EXPECTED_MUTATIONS, ran $passed"
printf 'validation=candidate-z-validator-mutations\n'
printf 'positive_controls=exact-y-baseline,z-initramfs,dynamic-dispatch,z-boot,final-artifact\n'
printf 'mutation_rejections=%s-of-%s\n' "$passed" "$EXPECTED_MUTATIONS"
printf 'dispatch_matrix=standalone,ENV,alias,oracle,absolute-wrapper\n'
printf 'watchdog_matrix=preflight,function-open,single-ping,held-fd,no-fallback,countdown\n'
printf 'device_contact=none\nhardware_write=none\n'
