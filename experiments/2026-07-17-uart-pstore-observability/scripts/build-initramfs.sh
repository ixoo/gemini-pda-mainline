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
usage: build-initramfs.sh --output PATH [--busybox PATH]
       [--source-date-epoch N]

Build Candidate L's deterministic, storage-inert observability initramfs.
The output must not exist. This command has no device or flashing interface.
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
[[ "$(uname -m)" == aarch64 ]] || die "expected an aarch64 development VM"
[[ -n "$output" ]] || die "--output is required"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
[[ -x "$busybox" ]] || die "BusyBox is not executable: $busybox"
[[ "$source_date_epoch" =~ ^[0-9]+$ && "$source_date_epoch" == 0 ]] || \
	die "Candidate L requires source-date-epoch zero"
for command in cpio find gzip install readelf sha256sum sort touch; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done
if readelf -l "$busybox" | grep -q ' INTERP '; then
	die "BusyBox must be statically linked: $busybox"
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
init_source="${experiment_dir}/initramfs/init"
report_source="${experiment_dir}/initramfs/usb-report"
[[ -s "$init_source" ]] || die "init source is missing: $init_source"
[[ -s "$report_source" ]] || die "USB report source is missing: $report_source"

readonly EXPECTED_BUSYBOX_SHA256=52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933
[[ "$(sha256sum "$busybox" | awk '{print $1}')" == \
	"$EXPECTED_BUSYBOX_SHA256" ]] || die "BusyBox does not match the pinned static binary"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-observability-initramfs.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

mkdir -p "$workdir/bin" "$workdir/dev" "$workdir/proc" "$workdir/run" "$workdir/sys"
chmod 0755 "$workdir" "$workdir/bin" "$workdir/dev" "$workdir/proc" "$workdir/run" "$workdir/sys"
install -m 0755 "$busybox" "$workdir/bin/busybox"
install -m 0755 "$init_source" "$workdir/init"
install -m 0755 "$report_source" "$workdir/bin/usb-report"
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

expected_members="$(printf '%s\n' \
	. bin bin/busybox bin/cat bin/dmesg bin/grep bin/ip bin/ls bin/mount \
	bin/nc bin/ps bin/sed bin/sh bin/sleep bin/uname bin/usb-report \
	dev init proc run sys)"
archive_members="$(gzip -cd "$output" | cpio -it --quiet | sort)"
[[ "$archive_members" == "$expected_members" ]] || \
	die "generated initramfs does not match the exact member allowlist"

printf 'output=%s\n' "$output"
printf 'size=%s\n' "$(wc -c <"$output")"
printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'source_date_epoch=%s\n' "$source_date_epoch"
printf 'marker=GEMINI_OBSERVABILITY_20260717_L\n'
printf 'recovery_hypothesis=kernel-console-to-Gemian-primary-console-ramoops\n'
printf 'pmsg_frontend=disabled-alignment-zone-no-payload-writes\n'
printf 'uart_expected_pins=GPIO97-RX,GPIO98-TX\n'
printf 'watchdog_return=one-handoff-ping-then-direct-TOPRGU-expiry,timeout-31s,failure-boundary-40s\n'
printf 'usb_bonus=read-only-report-at-10.15.19.82:2323\n'
printf 'archive_inventory=exact-storage-inert-allowlist\n'
printf 'storage_access=none\n'
printf 'build_hardware_write=none\nflash=none\n'
