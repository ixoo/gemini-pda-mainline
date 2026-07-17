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
usage: build-initramfs.sh --baseline FILE --output PATH
       [--source-date-epoch N]

Derive the deterministic Candidate G initramfs from exact Candidate F. The
raw screen marker and its dd/wc links are removed and /init is replaced with a
storage-inert fbcon text hold. This command has no device or flashing interface.
EOF
}

baseline=
output=
source_date_epoch=${SOURCE_DATE_EPOCH:-0}
while (($#)); do
	case "$1" in
		--baseline)
			(($# >= 2)) || die "--baseline requires FILE"
			baseline=$2
			shift 2
			;;
		--output)
			(($# >= 2)) || die "--output requires PATH"
			output=$2
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
[[ -s "$baseline" ]] || die "exact Candidate F initramfs is required"
[[ -n "$output" ]] || die "--output is required"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
[[ "$source_date_epoch" =~ ^[0-9]+$ ]] || die "epoch must be a non-negative integer"
[[ "$source_date_epoch" == 0 ]] || die "exact Candidate F derivation requires epoch zero"
for command in awk cpio find gzip install readlink rm sha256sum sort touch wc; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

readonly EXPECTED_BASELINE_INITRAMFS_SHA256=1c76b34ea58956ffd8b97a640b76788b9f7e1ab92204a9881ad031bd7fe6c72c
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || \
	die "baseline is not the exact Candidate F initramfs"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
init_source="${experiment_dir}/initramfs/init"
[[ -s "$init_source" ]] || die "tracked Candidate G /init is missing"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-fbcon-text-initramfs.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT
mkdir "$workdir/root"
gzip -dc "$baseline" | (cd "$workdir/root" && cpio -idmu --quiet)

[[ -f "$workdir/root/screen-marker.raw" ]] || die "baseline marker is missing"
[[ "$(readlink "$workdir/root/bin/dd")" == busybox ]] || die "baseline dd link is invalid"
[[ "$(readlink "$workdir/root/bin/wc")" == busybox ]] || die "baseline wc link is invalid"
rm "$workdir/root/screen-marker.raw" "$workdir/root/bin/dd" "$workdir/root/bin/wc"
install -m 0755 "$init_source" "$workdir/root/init"
find "$workdir/root" -exec touch -h -d "@$source_date_epoch" {} +

mkdir -p "$(dirname -- "$output")"
(
	cd "$workdir/root"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$output"
chmod 0600 "$output"

printf 'output=%s\n' "$output"
printf 'size=%s\n' "$(wc -c <"$output")"
printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'source_date_epoch=%s\n' "$source_date_epoch"
printf 'marker=GEMINI_FBCON_TEXT_20260716_G\n'
printf 'baseline_initramfs_sha256=%s\n' "$EXPECTED_BASELINE_INITRAMFS_SHA256"
printf 'removed_regular_files=screen-marker.raw\n'
printf 'removed_symlinks=bin/dd,bin/wc\n'
printf 'changed_regular_files=init\n'
printf 'raw_framebuffer_access=none\n'
printf 'storage_access=none\n'
printf 'runtime_reboot_request=none\n'
printf 'build_hardware_write=none\n'
