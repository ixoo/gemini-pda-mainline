#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C

usage() {
	cat >&2 <<'EOF'
usage: build-minimal-initramfs.sh --output PATH [--busybox PATH]

Build a private, static ARM64 initramfs for a UART-only bring-up image.
EOF
}

die() {
	echo "error: $*" >&2
	exit 2
}

output=
busybox=/usr/bin/busybox
source_date_epoch=${SOURCE_DATE_EPOCH:-0}
while (($#)); do
	case "$1" in
		--output)
			(($# >= 2)) || die "--output needs a path"
			output=$2
			shift 2
			;;
		--busybox)
			(($# >= 2)) || die "--busybox needs a path"
			busybox=$2
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			usage
			die "unknown argument: $1"
			;;
	esac
done

[[ -n "$output" ]] || die "--output is required"
[[ -x "$busybox" ]] || die "BusyBox is not executable: $busybox"
[[ -f "$(dirname "$0")/../initramfs/init" ]] || die "initramfs/init is missing"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
[[ "$source_date_epoch" =~ ^[0-9]+$ ]] || \
	die "SOURCE_DATE_EPOCH must be a non-negative integer"

workdir=$(mktemp -d "${TMPDIR:-/tmp}/gemini-initramfs.XXXXXX")
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

mkdir -p "$workdir/bin" "$workdir/dev" "$workdir/etc" "$workdir/proc" "$workdir/sys"
# Make directory modes independent of the caller's umask. Keep the archive
# root private while retaining conventional access modes below it.
chmod 0755 "$workdir/bin" "$workdir/dev" "$workdir/etc" "$workdir/proc" "$workdir/sys"
install -m 0755 "$busybox" "$workdir/bin/busybox"
install -m 0755 "$(dirname "$0")/../initramfs/init" "$workdir/init"

for applet in ash cat dmesg echo grep hexdump mount poweroff reboot sh sleep switch_root tty uname; do
	ln -s busybox "$workdir/bin/$applet"
done

# cpio stores file metadata. Normalize it so repeated builds from the same
# BusyBox and init script produce identical bytes, independent of wall clock.
find "$workdir" -exec touch -h -d "@$source_date_epoch" {} +

mkdir -p "$(dirname "$output")"
(
	cd "$workdir"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 > "$output"

size=$(wc -c < "$output")
sha256=$(sha256sum "$output" | awk '{print $1}')
printf 'output=%s\nsize=%s\nsha256=%s\nbusybox=%s\nhardware_write=none\n' \
	"$output" "$size" "$sha256" "$busybox"
