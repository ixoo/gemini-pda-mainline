#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --baseline W_INITRAMFS --helper FILE --output FILE\n' "$0" >&2; }

baseline=
helper=
output=
while (($#)); do
	case "$1" in
		--baseline) (($# >= 2)) || die "$1 requires a value"; baseline=$2; shift 2 ;;
		--helper) (($# >= 2)) || die "$1 requires a value"; helper=$2; shift 2 ;;
		--output) (($# >= 2)) || die "$1 requires a value"; output=$2; shift 2 ;;
		-h|--help) usage; exit 0 ;;
		*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || \
	die "run inside the AArch64 Linux development VM"
[[ -s "$baseline" && ! -L "$baseline" && -x "$helper" && ! -L "$helper" && -n "$output" ]] || \
	die "exact Candidate W initramfs, helper, and output are required"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
for command in awk chmod cmp cpio dirname find grep gzip install ln mkdir mktemp \
	mv readelf rm sha256sum sort touch uname; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -d "$(dirname -- "$output")" ]] || die "output parent must already exist"
output_parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"
output_name="$(basename -- "$output")"
[[ "$output_name" != . && "$output_name" != .. ]] || die "unsafe output name"
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"

readonly W_INITRAMFS_SHA256=3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6
readonly W_BUSYBOX_SHA256=52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933
readonly W_HELPER_SHA256=b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == "$W_INITRAMFS_SHA256" ]] || \
	die "baseline is not exact Candidate W initramfs"
[[ "$(sha256sum "$helper" | awk '{print $1}')" == "$W_HELPER_SHA256" ]] || \
	die "helper is not exact Candidate W input-event-capture"
readelf -lW "$helper" | grep -q ' INTERP ' && die "helper contains PT_INTERP"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_dir="${script_dir}/../initramfs"
source_paths=(init inittab local-shell reboot x-probe x-record)
hash_sources() {
	local source
	for source in "${source_paths[@]}"; do
		[[ -s "$source_dir/$source" && ! -L "$source_dir/$source" ]] || \
			die "tracked initramfs source is missing, empty, or a symlink: $source"
		sha256sum "$source_dir/$source"
	done
}
source_tree_at_start="$(hash_sources)"
workdir="$(mktemp -d "$output_parent/.x-initramfs.XXXXXX")"
cleanup() { [[ ! -d "$workdir" ]] || rm -rf "$workdir"; }
trap cleanup EXIT
mkdir -p "$workdir/inputs" "$workdir/sources" "$workdir/w" \
	"$workdir/root/bin" "$workdir/root/etc" \
	"$workdir/root/dev" "$workdir/root/proc" "$workdir/root/run" "$workdir/root/sys"
install -m 0600 "$baseline" "$workdir/inputs/candidate-w-initramfs.img"
install -m 0700 "$helper" "$workdir/inputs/input-event-capture"
for source in "${source_paths[@]}"; do
	mode=0755
	[[ "$source" != inittab ]] || mode=0644
	install -m "$mode" "$source_dir/$source" "$workdir/sources/$source"
done
[[ "$(sha256sum "$workdir/inputs/candidate-w-initramfs.img" | awk '{print $1}')" == \
	"$W_INITRAMFS_SHA256" ]] || die "baseline changed during immutable snapshot"
[[ "$(sha256sum "$workdir/inputs/input-event-capture" | awk '{print $1}')" == \
	"$W_HELPER_SHA256" ]] || die "helper changed during immutable snapshot"
chmod 0755 "$workdir/root" "$workdir/root/bin" "$workdir/root/etc" \
	"$workdir/root/dev" "$workdir/root/proc" "$workdir/root/run" "$workdir/root/sys"
gzip -dc "$workdir/inputs/candidate-w-initramfs.img" | \
	(cd "$workdir/w" && cpio -idmu --quiet bin/busybox bin/input-event-capture)
busybox="$workdir/w/bin/busybox"
[[ "$(sha256sum "$busybox" | awk '{print $1}')" == "$W_BUSYBOX_SHA256" ]] || \
	die "Candidate W BusyBox bytes do not match the pin"
cmp -s "$workdir/w/bin/input-event-capture" "$workdir/inputs/input-event-capture" || \
	die "Candidate W archive helper differs from the exact helper input"

linked_applets='ash cat chvt clear init mount readlink sh sleep stty true'
required_applets="$linked_applets reboot"
available="$($busybox --list)"
for applet in $required_applets; do
	grep -Fxq "$applet" <<<"$available" || die "BusyBox applet missing: $applet"
done
install -m 0755 "$busybox" "$workdir/root/bin/busybox"
install -m 0755 "$workdir/inputs/input-event-capture" "$workdir/root/bin/input-event-capture"
install -m 0755 "$workdir/sources/init" "$workdir/root/init"
for program in local-shell reboot x-probe x-record; do
	install -m 0755 "$workdir/sources/$program" "$workdir/root/bin/$program"
done
install -m 0644 "$workdir/sources/inittab" "$workdir/root/etc/inittab"
for applet in $linked_applets; do
	ln -s busybox "$workdir/root/bin/$applet"
done
find "$workdir/root" -exec touch -h -d @0 {} +
(
	cd "$workdir/root"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/initramfs.img"
chmod 0600 "$workdir/initramfs.img"

[[ "$(hash_sources)" == "$source_tree_at_start" ]] || \
	die "tracked initramfs sources changed during construction"
"$script_dir/validate-initramfs.sh" \
	--baseline "$workdir/inputs/candidate-w-initramfs.img" \
	--candidate "$workdir/initramfs.img" \
	--helper "$workdir/inputs/input-event-capture" >/dev/null
mv --no-clobber --no-target-directory -- "$workdir/initramfs.img" "$output"
[[ ! -e "$workdir/initramfs.img" && -f "$output" && ! -L "$output" ]] || \
	die "initramfs destination appeared during atomic handoff"
printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'busybox_sha256=%s\nhelper_sha256=%s\n' "$W_BUSYBOX_SHA256" "$W_HELPER_SHA256"
printf 'marker=GEMINI_KEYBOARD_MANUAL_REBOOT_20260719_X\n'
printf 'baseline=candidate-w-exact\nprobe_dependency=none\ntty1_supervision=respawn\n'
printf 'kernel_virtual_console=none\nserial_console=ttyS0\n'
printf 'watchdog_userspace=start-none,open-none,ping-none\n'
printf 'manual_reboot=explicit-busybox-reboot-no-sync-force\nmanual_reboot_storage_access=none\n'
printf 'runtime_networking=none\nstorage_access=none\nbuild_hardware_write=none\nflash=none\n'
