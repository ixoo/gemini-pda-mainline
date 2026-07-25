#!/usr/bin/env bash

# Mutation patterns intentionally contain unexpanded shell expressions.
# shellcheck disable=SC2016

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --baseline EXACT_X_ARTIFACT\n' "$0" >&2; }

baseline=
while (($#)); do
	case "$1" in
	--baseline) (($# >= 2)) || die "$1 requires a value"; baseline=$2; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$(uname -s)" == Linux && -d "$baseline" && ! -L "$baseline" ]] || \
	die 'run in Linux with the exact Candidate X artifact'
for command in awk chmod cpio cp find gzip ln mkdir mktemp mv python3 rm sed sort touch; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
x_validator="$script_dir/validate-x-baseline.py"
initramfs_builder="$script_dir/build-initramfs.sh"
initramfs_validator="$script_dir/validate-initramfs.py"
boot_builder="$script_dir/build-boot-from-x.py"
boot_validator="$script_dir/validate-boot.py"
top_builder="$script_dir/build-keyboard-typed-watchdog-reboot-candidate.sh"
final_validator="$script_dir/validate-final-artifact.py"
x_boot="$baseline/gemini-keyboard-manual-reboot.boot.img"
x_initramfs="$baseline/gemini-keyboard-manual-reboot-initramfs.img"
x_dtb="$baseline/mt6797-gemini-pda-keyboard-manual-reboot.dtb"

workdir="$(mktemp -d /tmp/candidate-y-mutations.XXXXXX)"
cleanup() { rm -rf -- "$workdir"; }
trap cleanup EXIT
python3 "$x_validator" --baseline "$baseline" >/dev/null
"$initramfs_builder" --baseline "$x_initramfs" --output "$workdir/y-initramfs.img" >/dev/null
python3 "$initramfs_validator" --baseline "$x_initramfs" \
	--candidate "$workdir/y-initramfs.img" --source-dir "$experiment_dir/initramfs" >/dev/null
python3 "$boot_builder" --x-boot "$x_boot" --x-initramfs "$x_initramfs" \
	--y-initramfs "$workdir/y-initramfs.img" --output "$workdir/y.boot.img" >/dev/null
python3 "$boot_validator" --x-boot "$x_boot" --x-initramfs "$x_initramfs" \
	--y-boot "$workdir/y.boot.img" --y-initramfs "$workdir/y-initramfs.img" \
	--dtb "$x_dtb" >/dev/null

passed=0
expect_fail() {
	local name=$1
	shift
	set +e
	"$@" >"$workdir/$name.out" 2>"$workdir/$name.err"
	local rc=$?
	set -e
	[[ "$rc" == 2 ]] || die "mutation was not rejected with status 2: $name (status $rc)"
	passed=$((passed + 1))
}

pack_fixture() {
	local fixture=$1
	(
		cd "$fixture/root"
		find . -print0 | sort -z | cpio --null --create --format=newc \
			--owner=0:0 --reproducible --quiet
	) | gzip -n -9 >"$fixture/candidate.img"
}

archive_mutation() {
	local name=$1
	local fixture="$workdir/archive-$name"
	mkdir -p "$fixture/root" "$fixture/source"
	gzip -dc "$workdir/y-initramfs.img" | (cd "$fixture/root" && cpio -idmu --quiet)
	# cpio leaves the already-created extraction root at the caller's umask.
	# Restore Y's canonical archived `.` mode so each mutation is rejected for
	# its intended semantic delta rather than an incidental root-mode change.
	chmod 0755 "$fixture/root"
	cp "$experiment_dir/initramfs/"{init,local-shell,reboot,x-record} "$fixture/source/"
	case "$name" in
	request_removed)
		sed -i '/manual_reboot=requested trigger=typed/d' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	trap_removed)
		sed -i "/trap '' HUP INT QUIT TERM TSTP/d" "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	irq_gate_removed)
		sed -i '/LIVE_WATCHDOG\/interrupts/d' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	identity_gate_removed)
		sed -i '/identity.*mtk-wdt.*refuse/d' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	class_platform_gate_removed)
		sed -i '/class_device.*platform_device.*refuse/d' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	timeout_gate_removed)
		sed -i '/timeout.*WATCHDOG_TIMEOUT_SECONDS.*refuse/d' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	pretimeout_gate_removed)
		sed -i '/case "$pretimeout"/,/esac/d' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	ramoops_gate_removed)
		sed -i '/ramoops_driver.*ramoops.*refuse/d' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	validated_marker_removed)
		sed -i '/manual_reboot=validated/d' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	open_order_changed)
		sed -i '/typed reboot received/a\\exec 3>/dev/watchdog0' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	second_ping)
		sed -i "/printf '\\.' >&3/a\\\tprintf '.' >&3" "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	magic_close)
		sed -i "s/printf '\\.' >&3/printf 'V' >\&3/" "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	fd_close)
		sed -i '/hold_armed.*watchdog-expiry-failed/i\\exec 3>\&-' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	software_reboot)
		sed -i '/hold_armed.*watchdog-expiry-failed/i\\/bin/busybox reboot -n -f' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	sync_added)
		sed -i '/hold_armed.*watchdog-expiry-failed/i\\/bin/sync' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	progress_removed)
		sed -i 's/5|10|15|20|25|30|35|40/5|10|15|20|25|30|35/' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	failure_hold_removed)
		sed -i '/manual_reboot=watchdog-expiry-failed boundary_seconds=40/d' "$fixture/root/bin/reboot" "$fixture/source/reboot"
		;;
	marker_changed)
		sed -i 's/GEMINI_KEYBOARD_TYPED_WATCHDOG_REBOOT_20260719_Y/GEMINI_BAD_Y/g' \
			"$fixture/root/init" "$fixture/root/bin/local-shell" "$fixture/root/bin/x-record" \
			"$fixture/source/init" "$fixture/source/local-shell" "$fixture/source/x-record"
		;;
	automatic_watchdog)
		sed -i '/exec \/bin\/busybox init/i\\exec 9>/dev/watchdog0' \
			"$fixture/root/init" "$fixture/source/init"
		;;
	automatic_reboot)
		sed -i '/exec \/bin\/busybox init/i\\/bin/reboot' \
			"$fixture/root/init" "$fixture/source/init"
		;;
	probe_changed)
		printf '\n# mutation\n' >>"$fixture/root/bin/x-probe"
		;;
	extra_member)
		printf 'unexpected\n' >"$fixture/root/unexpected"
		;;
	mode_changed)
		chmod 0700 "$fixture/root/bin/reboot"
		;;
	*) die "unknown archive mutation: $name" ;;
	esac
	find "$fixture/root" -exec touch -h -d @0 {} +
	pack_fixture "$fixture"
	expect_fail "$name" python3 "$initramfs_validator" --baseline "$x_initramfs" \
		--candidate "$fixture/candidate.img" --source-dir "$fixture/source"
}

for mutation in request_removed trap_removed irq_gate_removed identity_gate_removed \
	class_platform_gate_removed timeout_gate_removed pretimeout_gate_removed \
	ramoops_gate_removed validated_marker_removed open_order_changed second_ping \
	magic_close fd_close software_reboot sync_added progress_removed \
	failure_hold_removed marker_changed automatic_watchdog automatic_reboot \
	probe_changed extra_member mode_changed; do
	archive_mutation "$mutation"
done

boot_mutation() {
	local name=$1
	local target="$workdir/$name.boot.img"
	cp "$workdir/y.boot.img" "$target"
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
	expect_fail "$name" python3 "$boot_validator" --x-boot "$x_boot" \
		--x-initramfs "$x_initramfs" --y-boot "$target" \
		--y-initramfs "$workdir/y-initramfs.img" --dtb "$x_dtb"
}
for mutation in kernel_byte unrelated_header trailing_byte canonical_id; do
	boot_mutation "$mutation"
done

bad_dtb="$workdir/bad.dtb"
cp "$x_dtb" "$bad_dtb"
python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); d=bytearray(p.read_bytes()); d[-1]^=1; p.write_bytes(d)' "$bad_dtb"
expect_fail dtb_substitution python3 "$boot_validator" --x-boot "$x_boot" \
	--x-initramfs "$x_initramfs" --y-boot "$workdir/y.boot.img" \
	--y-initramfs "$workdir/y-initramfs.img" --dtb "$bad_dtb"

baseline_link="$workdir/x-baseline-link"
ln -s "$baseline" "$baseline_link"
expect_fail baseline_symlink python3 "$x_validator" --baseline "$baseline_link"

source_link_fixture="$workdir/source-link"
mkdir "$source_link_fixture"
cp "$experiment_dir/initramfs/"{init,local-shell,x-record} "$source_link_fixture/"
ln -s "$experiment_dir/initramfs/reboot" "$source_link_fixture/reboot"
expect_fail source_symlink python3 "$initramfs_validator" --baseline "$x_initramfs" \
	--candidate "$workdir/y-initramfs.img" --source-dir "$source_link_fixture"

existing_output="$workdir/existing.boot.img"
printf 'occupied\n' >"$existing_output"
expect_fail output_overwrite python3 "$boot_builder" --x-boot "$x_boot" \
	--x-initramfs "$x_initramfs" --y-initramfs "$workdir/y-initramfs.img" \
	--output "$existing_output"

mkdir "$workdir/final-output"
"$top_builder" --baseline "$baseline" --output-parent "$workdir/final-output" \
	>"$workdir/top-builder.out"
final_artifact="$(find "$workdir/final-output" -mindepth 1 -maxdepth 1 -type d -name 'candidate-Y-*' -print -quit)"
[[ -n "$final_artifact" ]] || die 'positive-control final artifact was not produced'
python3 "$final_validator" --artifact "$final_artifact" --baseline "$baseline" >/dev/null

mkdir "$workdir/final-inventory-parent"
final_inventory="$workdir/final-inventory-parent/$(basename -- "$final_artifact")"
cp -a "$final_artifact" "$final_inventory"
printf 'unexpected\n' >"$final_inventory/unexpected"
expect_fail final_inventory python3 "$final_validator" --artifact "$final_inventory" --baseline "$baseline"

mkdir "$workdir/final-mode-parent"
final_mode="$workdir/final-mode-parent/$(basename -- "$final_artifact")"
cp -a "$final_artifact" "$final_mode"
chmod 0644 "$final_mode/input-event-capture"
expect_fail final_mode python3 "$final_validator" --artifact "$final_mode" --baseline "$baseline"

mkdir "$workdir/final-symlink-parent"
final_symlink="$workdir/final-symlink-parent/$(basename -- "$final_artifact")"
cp -a "$final_artifact" "$final_symlink"
rm "$final_symlink/provenance.txt"
ln -s "$final_artifact/provenance.txt" "$final_symlink/provenance.txt"
expect_fail final_symlink python3 "$final_validator" --artifact "$final_symlink" --baseline "$baseline"

expect_fail final_output_race "$top_builder" --baseline "$baseline" \
	--output-parent "$workdir/final-output"

printf 'validation=candidate-y-validator-mutations\n'
printf 'positive_controls=exact-x-baseline,y-initramfs,y-boot\n'
printf 'mutation_rejections=%s-of-%s\n' "$passed" "$passed"
printf 'device_contact=none\nhardware_write=none\n'
