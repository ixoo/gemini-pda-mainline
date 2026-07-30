#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
export SOURCE_DATE_EPOCH=0
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# -eq 3 ]] ||
	die 'usage: build-initramfs.sh GATE3_INITRAMFS DA921X_MODULE OUTPUT'
baseline=$1
module=$2
output=$3
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] ||
	die 'run in the Linux AArch64 development VM'
for command in cpio find gzip install mkdir mktemp mv python3 rm sort touch; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command missing: $command"
done
for input in "$baseline" "$module"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "input is missing, empty, or unsafe: $input"
done
[[ ! -e "$output" && ! -L "$output" ]] ||
	die 'refusing to overwrite initramfs output'
output_parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
validator="$script_dir/validate-initramfs.py"

workdir="$(mktemp -d "$output_parent/.da921x-module-initramfs.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
mkdir "$workdir/root"
chmod 0755 "$workdir/root"
gzip -dc "$baseline" | (cd "$workdir/root" && cpio -idmu --quiet)
install -d -m 0755 "$workdir/root/lib"
install -m 0400 "$module" "$workdir/root/lib/da9213-legacy-regulator.ko"
find "$workdir/root" -exec touch -h -d @0 {} +
(
	cd "$workdir/root"
	find . -print0 | sort -z |
		cpio --null --create --format=newc --owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/output.img"
python3 "$validator" --baseline "$baseline" --candidate "$workdir/output.img" \
	--module "$module"
mv --no-clobber --no-target-directory "$workdir/output.img" "$output"
printf 'validation=da921x-module-initramfs-built\n'
printf 'automatic_invocation=none\nmanual_post_serviceability_load=required\n'
