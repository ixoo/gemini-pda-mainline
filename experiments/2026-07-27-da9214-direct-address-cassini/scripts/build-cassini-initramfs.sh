#!/usr/bin/env bash

# Add only the validated inert Cassini helper to exact Candidate AO initramfs.
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
export SOURCE_DATE_EPOCH=0
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# -eq 4 ]] ||
	die 'usage: build-cassini-initramfs.sh AO_INITRAMFS PROBE_SOURCE PROBE_BINARY OUTPUT'
baseline=$1
source_file=$2
helper=$3
output=$4
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] ||
	die 'run in the Linux AArch64 recovery VM'
for command in cpio find gzip install mkdir mktemp mv python3 rm sha256sum sort touch; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command missing: $command"
done
for input in "$baseline" "$source_file" "$helper"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "input is missing, empty, or unsafe: $input"
done
[[ ! -e "$output" && ! -L "$output" ]] ||
	die 'refusing to overwrite initramfs output'
output_parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"
[[ -d "$output_parent" && ! -L "$output_parent" ]] ||
	die 'initramfs output parent is unsafe'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
validator="$script_dir/validate-cassini-initramfs.py"
[[ -f "$validator" && ! -L "$validator" && -s "$validator" ]] ||
	die 'initramfs validator is missing or unsafe'

workdir="$(mktemp -d "$output_parent/.cassini-initramfs.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
mkdir "$workdir/root"
chmod 0755 "$workdir/root"
gzip -dc "$baseline" | (cd "$workdir/root" && cpio -idmu --quiet)
[[ ! -e "$workdir/root/bin/cassini-probe" &&
	! -L "$workdir/root/bin/cassini-probe" ]] ||
	die 'baseline unexpectedly contains Cassini helper'
install -m 0755 "$helper" "$workdir/root/bin/cassini-probe"
find "$workdir/root" -exec touch -h -d @0 {} +
(
	cd "$workdir/root"
	find . -print0 | sort -z |
		cpio --null --create --format=newc --owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/output.img"
python3 "$validator" --baseline "$baseline" --candidate "$workdir/output.img" \
	--source "$source_file" --helper "$helper"
candidate_sha256="$(sha256sum "$workdir/output.img" | awk '{print $1}')"
mv --no-clobber --no-target-directory "$workdir/output.img" "$output"
printf 'validation=cassini-initramfs-built\n'
printf 'candidate_sha256=%s\n' "$candidate_sha256"
printf 'added_members=bin/cassini-probe\nchanged_inherited_members=none\n'
printf 'automatic_invocation=none\nmanual_post_usb_invocation=required\n'
