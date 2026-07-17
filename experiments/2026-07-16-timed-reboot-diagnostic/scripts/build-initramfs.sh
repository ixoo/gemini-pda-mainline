#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() {
	echo "error: $*" >&2
	exit 2
}

usage() {
	cat >&2 <<'EOF'
usage: build-initramfs.sh --output PATH [--busybox PATH] [--source-date-epoch N]

Build the deterministic USB diagnostic initramfs whose only intentional file
delta is the tracked patch arming a forced reboot after 10 seconds. The command
has no device or flashing interface.
EOF
}

output=
busybox=/usr/bin/busybox
source_date_epoch=${SOURCE_DATE_EPOCH:-0}
while (($#)); do
	case "$1" in
		--output)
			(($# >= 2)) || die "--output requires PATH"
			output=$2
			shift 2
			;;
		--busybox)
			(($# >= 2)) || die "--busybox requires PATH"
			busybox=$2
			shift 2
			;;
		--source-date-epoch)
			(($# >= 2)) || die "--source-date-epoch requires N"
			source_date_epoch=$2
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

[[ "$(uname -s)" == Linux ]] || die "run inside the Linux development VM"
[[ -n "$output" ]] || die "--output is required"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
[[ -x "$busybox" ]] || die "BusyBox is not executable: $busybox"
[[ "$source_date_epoch" =~ ^[0-9]+$ ]] || die "epoch must be a non-negative integer"
for command in awk cpio find grep gzip install patch readelf sha256sum sort touch; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done
if readelf -l "$busybox" | grep -q ' INTERP '; then
	die "BusyBox must be statically linked: $busybox"
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
baseline_init="${repo_root}/experiments/2026-07-16-usb-gadget-diagnostic/initramfs/init"
reboot_patch="${experiment_dir}/initramfs/timed-reboot.patch"
shell_source="${repo_root}/experiments/2026-07-16-usb-gadget-diagnostic/initramfs/usb-shell"
readonly EXPECTED_BASELINE_INIT_SHA256=bd7b2679d4e12f6b17d1b5b963dc160b6bb28f956eaba746e8f4102c7ec9f3d9
[[ -r "$baseline_init" ]] || die "baseline init source is missing: $baseline_init"
[[ -r "$reboot_patch" ]] || die "timed-reboot patch is missing: $reboot_patch"
[[ -r "$shell_source" ]] || die "USB shell source is missing: $shell_source"
[[ "$(sha256sum "$baseline_init" | awk '{print $1}')" == "$EXPECTED_BASELINE_INIT_SHA256" ]] || \
	die "baseline init source does not match the tested USB candidate"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-rebootdiag-initramfs.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

mkdir -p "$workdir/bin" "$workdir/dev" "$workdir/proc" "$workdir/run" "$workdir/sys"
chmod 0755 "$workdir" "$workdir/bin" "$workdir/dev" "$workdir/proc" "$workdir/run" "$workdir/sys"
install -m 0755 "$busybox" "$workdir/bin/busybox"
install -m 0755 "$baseline_init" "$workdir/init"
patch_log="${workdir}/patch.log"
if ! patch --fuzz=0 --no-backup-if-mismatch -d "$workdir" -p0 \
	<"$reboot_patch" >"$patch_log" 2>&1; then
	die "timed-reboot patch did not apply exactly"
fi
if grep -Eqi 'offset|fuzz' "$patch_log"; then
	die "timed-reboot patch required offset or fuzz"
fi
rm "$patch_log"
install -m 0755 "$shell_source" "$workdir/bin/usb-shell"
for applet in cat dmesg grep ip ls mount nc ps sed sh sleep uname; do
	ln -s busybox "$workdir/bin/$applet"
done
find "$workdir" -exec touch -h -d "@$source_date_epoch" {} +

mkdir -p "$(dirname -- "$output")"
(
	cd "$workdir"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$output"
chmod 0600 "$output"

printf 'output=%s\n' "$output"
printf 'size=%s\n' "$(wc -c <"$output")"
printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'source_date_epoch=%s\n' "$source_date_epoch"
printf 'marker=GEMINI_USB_DIAG_20260716_B\n'
printf 'reboot_delay_seconds=10\n'
printf 'reboot_invocation=/bin/busybox reboot -f\n'
printf 'storage_access=none\n'
printf 'hardware_write=none\n'
printf 'intended_runtime_action=forced-reboot-request\n'
printf 'runtime_reboot_observed=not-tested\n'
