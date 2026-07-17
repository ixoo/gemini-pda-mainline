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

Build the deterministic, storage-inert screen-marker initramfs. The output
must not exist. This command has no device or flashing interface.
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
[[ "$source_date_epoch" =~ ^[0-9]+$ ]] || die "epoch must be a non-negative integer"
for command in awk cpio find grep gzip install python3 readelf sha256sum sort touch wc; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done
if readelf -l "$busybox" | grep -q ' INTERP '; then
	die "BusyBox must be statically linked: $busybox"
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
init_source="${experiment_dir}/initramfs/init"
shell_source="${repo_root}/experiments/2026-07-16-usb-gadget-diagnostic/initramfs/usb-shell"
marker_generator="${script_dir}/generate-screen-marker.py"
[[ -r "$init_source" ]] || die "init source is missing: $init_source"
[[ -r "$shell_source" ]] || die "USB shell fixture is missing: $shell_source"
[[ -x "$marker_generator" ]] || die "marker generator is not executable: $marker_generator"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-screen-marker-initramfs.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

mkdir -p "$workdir/bin" "$workdir/dev" "$workdir/proc" "$workdir/run" "$workdir/sys"
chmod 0755 "$workdir" "$workdir/bin" "$workdir/dev" "$workdir/proc" "$workdir/run" "$workdir/sys"
install -m 0755 "$busybox" "$workdir/bin/busybox"
install -m 0755 "$init_source" "$workdir/init"
# Retain the exact tested baseline archive shape except for the allowlisted
# marker, two BusyBox links, and /init. This binary is dormant in this test.
install -m 0755 "$shell_source" "$workdir/bin/usb-shell"
for applet in cat dd dmesg grep ip ls mount nc ps sed sh sleep uname wc; do
	ln -s busybox "$workdir/bin/$applet"
done
python3 "$marker_generator" --output "$workdir/screen-marker.raw" \
	>"$workdir/marker-build.log"
python3 "$marker_generator" --validate "$workdir/screen-marker.raw" \
	>"$workdir/marker-validate.log"
rm "$workdir/marker-build.log" "$workdir/marker-validate.log"
chmod 0644 "$workdir/screen-marker.raw"
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
printf 'marker=GEMINI_SCREEN_MARKER_20260716_E\n'
printf 'framebuffer_name=simple\n'
printf 'framebuffer_virtual_size=1080,2160\n'
printf 'framebuffer_bits_per_pixel=32\n'
printf 'framebuffer_stride=4352\n'
printf 'framebuffer_write_bytes=9400320\n'
printf 'pattern=8-horizontal-bands-opaque-white-dark-gray\n'
printf 'storage_access=none\n'
printf 'build_hardware_write=none\n'
printf 'runtime_framebuffer_write=yes\n'
