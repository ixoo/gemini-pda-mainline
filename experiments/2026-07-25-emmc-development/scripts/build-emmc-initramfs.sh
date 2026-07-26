#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly BASELINE_SHA256=166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3
readonly BUSYBOX_SHA256=52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || die 'run in the Linux AArch64 recovery VM'
[[ $# -eq 3 ]] || die 'usage: build-emmc-initramfs.sh BASELINE OUTPUT SOURCE_DIR'
baseline=$1
output=$2
source_dir=$3
[[ -f "$baseline" && ! -L "$baseline" ]] || die 'unsafe baseline'
[[ -d "$source_dir" && ! -L "$source_dir" ]] || die 'unsafe source directory'
for command in cpio find grep gzip install ln mkdir mktemp mv rm sha256sum sort touch awk; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == "$BASELINE_SHA256" ]] ||
	die 'baseline is not exact Candidate AO initramfs'
[[ -s "$source_dir/emmc-flash-boot2" && ! -L "$source_dir/emmc-flash-boot2" ]] ||
	die 'missing eMMC helper source'
parent=$(cd -- "$(dirname -- "$output")" && pwd -P)
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite initramfs'
work=$(mktemp -d "$parent/.candidate-emmc-initramfs.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
mkdir "$work/root"
gzip -dc "$baseline" | (cd "$work/root" && cpio -idmu --quiet)
chmod 0755 "$work/root"
busybox="$work/root/bin/busybox"
[[ -f "$busybox" && ! -L "$busybox" && -x "$busybox" ]] || die 'BusyBox missing'
[[ "$(sha256sum "$busybox" | awk '{print $1}')" == "$BUSYBOX_SHA256" ]] ||
	die 'exact BusyBox bytes changed'
"$busybox" --list >"$work/busybox-applets" || die 'BusyBox applet listing failed'
grep -Fxq dd "$work/busybox-applets" || die 'exact BusyBox lacks dd applet'
[[ ! -e "$work/root/bin/dd" && ! -L "$work/root/bin/dd" ]] ||
	die 'refusing to replace inherited dd member'
ln -s busybox "$work/root/bin/dd"
install -m 0755 "$source_dir/emmc-flash-boot2" "$work/root/bin/emmc-flash-boot2"
find "$work/root" -exec touch -h -d @0 {} +
(
	cd "$work/root"
	find . -print0 | sort -z | cpio --null --create --format=newc --owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$work/output.img"
python3 "$source_dir/../scripts/validate-emmc-initramfs.py" \
	--baseline "$baseline" --candidate "$work/output.img" --source-dir "$source_dir"
mv --no-clobber --no-target-directory "$work/output.img" "$output"
printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'baseline_sha256=%s\n' "$BASELINE_SHA256"
printf 'busybox_sha256=%s\n' "$BUSYBOX_SHA256"
printf 'added_members=bin/dd,bin/emmc-flash-boot2\n'
printf 'storage_access=explicit-confirmation-only\n'
