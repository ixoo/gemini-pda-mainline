#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --baseline V_INITRAMFS --helper FILE --output FILE\n' "$0" >&2; }

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
for command in awk chmod cmp cpio dirname find grep gzip install ln mkdir mktemp \
	mv readelf rm sed sha256sum sort touch; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
mkdir -p "$(dirname -- "$output")"

readonly V_INITRAMFS_SHA256=9382288385b50fed67b47ae494609f4ee9d314cfac0257c738e33e86094508b6
readonly V_BUSYBOX_SHA256=52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933
readonly V_HELPER_SHA256=b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == "$V_INITRAMFS_SHA256" ]] || \
	die "baseline is not exact Candidate V initramfs"
[[ "$(sha256sum "$helper" | awk '{print $1}')" == "$V_HELPER_SHA256" ]] || \
	die "helper is not the exact Candidate V input-event-capture"
readelf -lW "$helper" | grep -q ' INTERP ' && die "helper contains PT_INTERP"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_dir="${script_dir}/../initramfs"
workdir="$(mktemp -d "$(dirname -- "$output")/.w-initramfs.XXXXXX")"
trap 'rm -rf "$workdir"' EXIT
mkdir -p "$workdir/v" "$workdir/root/bin" "$workdir/root/etc" \
	"$workdir/root/dev" "$workdir/root/proc" "$workdir/root/run" "$workdir/root/sys"
chmod 0755 "$workdir/root" "$workdir/root/bin" "$workdir/root/etc" \
	"$workdir/root/dev" "$workdir/root/proc" "$workdir/root/run" "$workdir/root/sys"
gzip -dc "$baseline" | \
	(cd "$workdir/v" && \
		cpio -idmu --quiet bin/busybox bin/input-event-capture bin/v-watchdog)
busybox="$workdir/v/bin/busybox"
[[ "$(sha256sum "$busybox" | awk '{print $1}')" == "$V_BUSYBOX_SHA256" ]] || \
	die "Candidate V BusyBox bytes do not match the pin"
cmp -s "$workdir/v/bin/input-event-capture" "$helper" || \
	die "Candidate V archive helper differs from the exact helper input"
sed 's#/bin/v-record#/bin/w-record#g' "$workdir/v/bin/v-watchdog" \
	>"$workdir/v/w-watchdog.expected"
cmp -s "$source_dir/w-watchdog" "$workdir/v/w-watchdog.expected" || \
	die "Candidate W watchdog is not exact V behavior with only the recorder renamed"

applets='ash cat chvt clear init mount readlink sh sleep stty true'
available="$($busybox --list)"
for applet in $applets; do
	grep -Fxq "$applet" <<<"$available" || die "BusyBox applet missing: $applet"
done
install -m 0755 "$busybox" "$workdir/root/bin/busybox"
install -m 0755 "$helper" "$workdir/root/bin/input-event-capture"
install -m 0755 "$source_dir/init" "$workdir/root/init"
for program in local-shell pass w-probe w-record w-watchdog; do
	install -m 0755 "$source_dir/$program" "$workdir/root/bin/$program"
done
install -m 0644 "$source_dir/inittab" "$workdir/root/etc/inittab"
for applet in $applets; do ln -s busybox "$workdir/root/bin/$applet"; done
find "$workdir/root" -exec touch -h -d @0 {} +
(
	cd "$workdir/root"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/initramfs.img"
chmod 0600 "$workdir/initramfs.img"

"$script_dir/validate-initramfs.sh" --baseline "$baseline" \
	--candidate "$workdir/initramfs.img" --helper "$helper" >/dev/null
mv "$workdir/initramfs.img" "$output"
printf 'sha256=%s\nbusybox_sha256=%s\nhelper_sha256=%s\nmarker=GEMINI_KEYBOARD_WRRD_20260719_W\n' \
	"$(sha256sum "$output" | awk '{print $1}')" "$V_BUSYBOX_SHA256" "$V_HELPER_SHA256"
printf 'baseline=candidate-v-exact\nevent_discovery_seconds=5\nevent_capture_seconds=15\n'
printf 'tty1_supervision=respawn\ntty1_foreground=chvt-1\ntty1_background_marker_fanout=none\n'
printf 'kernel_console=external-fixed-tty2\ninput_success_token=pass\nrequired_keys=P,A,S,ENTER\n'
printf 'probe_dependency=none\nwatchdog_dependency=none\n'
printf 'watchdog_source=exact-candidate-v-behavior-with-recorder-rename-only\n'
printf 'watchdog_return=one-handoff-ping-then-no-irq-TOPRGU-expiry\n'
printf 'runtime_networking=none\nstorage_access=none\nbuild_hardware_write=none\nflash=none\n'
