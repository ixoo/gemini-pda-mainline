#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || die 'run in the Linux AArch64 recovery VM'
[[ $# -eq 3 ]] || die 'usage: build-initramfs.sh BASELINE OUTPUT SOURCE_DIR'
baseline=$1; output=$2; source_dir=$3
[[ -f "$baseline" && ! -L "$baseline" ]] || die 'unsafe baseline'
[[ -d "$source_dir" && ! -L "$source_dir" ]] || die 'unsafe source directory'
for command in cpio find gzip install mkdir mktemp mv rm sha256sum sort touch awk; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == \
	166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3 ]] ||
	die 'baseline is not exact Candidate AO initramfs'
for name in init aq-record clk-observe; do
	[[ -s "$source_dir/$name" && ! -L "$source_dir/$name" ]] || die "missing source: $name"
done
parent=$(cd -- "$(dirname -- "$output")" && pwd -P)
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite initramfs'
work=$(mktemp -d "$parent/.candidate-aq-initramfs.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
mkdir "$work/root"
gzip -dc "$baseline" | (cd "$work/root" && cpio -idmu --quiet)
chmod 0755 "$work/root"
install -m 0755 "$source_dir/init" "$work/root/init"
install -m 0755 "$source_dir/aq-record" "$work/root/bin/aq-record"
install -m 0755 "$source_dir/clk-observe" "$work/root/bin/clk-observe"
find "$work/root" -exec touch -h -d @0 {} +
(
	cd "$work/root"
	find . -print0 | sort -z | cpio --null --create --format=newc --owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$work/output.img"
mv --no-clobber --no-target-directory "$work/output.img" "$output"
printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
