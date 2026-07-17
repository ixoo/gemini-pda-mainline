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

Build the deterministic, storage-inert LK handoff initramfs. The output must
not already exist. This command has no device or flashing interface.
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
for command in cpio find gzip install readelf sha256sum sort touch; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done
if readelf -l "$busybox" | grep -q ' INTERP '; then
	die "BusyBox must be statically linked: $busybox"
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
init_source="${script_dir}/../initramfs/init"
[[ -r "$init_source" ]] || die "init source is missing: $init_source"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-lk-initramfs.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

mkdir -p "$workdir/bin" "$workdir/dev" "$workdir/proc" "$workdir/sys"
chmod 0755 "$workdir" "$workdir/bin" "$workdir/dev" "$workdir/proc" "$workdir/sys"
install -m 0755 "$busybox" "$workdir/bin/busybox"
install -m 0755 "$init_source" "$workdir/init"
for applet in ash cat echo grep mount sh sleep uname; do
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
printf 'marker=GEMINI_LK_HANDOFF_20260716_A\n'
printf 'hardware_write=none\n'
