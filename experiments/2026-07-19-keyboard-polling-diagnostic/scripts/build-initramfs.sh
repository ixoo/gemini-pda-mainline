#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --baseline P_INITRAMFS --helper FILE --output FILE\n' "$0" >&2; }

baseline=
helper=
output=
while (($#)); do
	case "$1" in
		--baseline) baseline=$2; shift 2 ;;
		--helper) helper=$2; shift 2 ;;
		--output) output=$2; shift 2 ;;
		*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || \
	die "run inside the AArch64 Linux development VM"
[[ -s "$baseline" && -x "$helper" && -n "$output" ]] || die "missing required input"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
mkdir -p "$(dirname -- "$output")"

readonly P_INITRAMFS_SHA256=3f19afd81632fbe654c024b9f865180b42caf61163bb26ea26211884271a11d8
readonly P_BUSYBOX_SHA256=52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == "$P_INITRAMFS_SHA256" ]] || \
	die "baseline is not exact Candidate P initramfs"
readelf -lW "$helper" | grep -q ' INTERP ' && die "helper contains PT_INTERP"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_dir="${script_dir}/../initramfs"
workdir="$(mktemp -d "$(dirname -- "$output")/.u-initramfs.XXXXXX")"
trap 'rm -rf "$workdir"' EXIT
mkdir -p "$workdir/p" "$workdir/root/bin" "$workdir/root/etc" \
	"$workdir/root/dev" "$workdir/root/proc" "$workdir/root/run" "$workdir/root/sys"
chmod 0755 "$workdir/root" "$workdir/root/bin" "$workdir/root/etc" \
	"$workdir/root/dev" "$workdir/root/proc" "$workdir/root/run" "$workdir/root/sys"
gzip -dc "$baseline" | (cd "$workdir/p" && cpio -idmu --quiet bin/busybox)
busybox="$workdir/p/bin/busybox"
[[ "$(sha256sum "$busybox" | awk '{print $1}')" == "$P_BUSYBOX_SHA256" ]] || \
	die "Candidate P BusyBox bytes do not match the pin"

applets='ash cat dmesg grep init ls mount ps readlink reboot sed sh sleep stty tail true uname'
available="$($busybox --list)"
for applet in $applets; do
	grep -Fxq "$applet" <<<"$available" || die "BusyBox applet missing: $applet"
done
install -m 0755 "$busybox" "$workdir/root/bin/busybox"
install -m 0755 "$helper" "$workdir/root/bin/input-event-capture"
install -m 0755 "$source_dir/init" "$workdir/root/init"
install -m 0755 "$source_dir/local-shell" "$workdir/root/bin/local-shell"
install -m 0755 "$source_dir/u-probe" "$workdir/root/bin/u-probe"
install -m 0755 "$source_dir/u-pass" "$workdir/root/bin/u-pass"
install -m 0644 "$source_dir/inittab" "$workdir/root/etc/inittab"
for applet in $applets; do ln -s busybox "$workdir/root/bin/$applet"; done
find "$workdir/root" -exec touch -h -d @0 {} +
(
	cd "$workdir/root"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/initramfs.img"
chmod 0600 "$workdir/initramfs.img"

members="$(gzip -dc "$workdir/initramfs.img" | cpio -it --quiet | sort)"
expected="$(
	printf '%s\n' . bin dev etc proc run sys init \
		bin/busybox bin/input-event-capture bin/local-shell bin/u-probe bin/u-pass \
		etc/inittab
	for applet in $applets; do printf 'bin/%s\n' "$applet"; done
)"
[[ "$members" == "$(printf '%s\n' "$expected" | sort)" ]] || die "archive allowlist mismatch"
mv "$workdir/initramfs.img" "$output"
printf 'output=%s\nsha256=%s\nbusybox_sha256=%s\nmarker=GEMINI_KEYBOARD_POLLING_20260719_U\n' \
	"$output" "$(sha256sum "$output" | awk '{print $1}')" "$P_BUSYBOX_SHA256"
printf 'event_window_seconds=60\ntty1_supervision=respawn\nprobe_supervision=once-independent\n'
printf 'automatic_reboot=no\nnetwork_action=none\nstorage_access=none\n'
