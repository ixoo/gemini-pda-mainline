#!/usr/bin/env bash

# Reproduce the exact runtime-proven DTB from its retained LK container.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=ebaddc69660a824de4ff0f2f59eafb9073a7b100ae3f737caf0f9b50f59cf98a
readonly DTB_SHA256=90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d
readonly DTB_OFFSET=4808457
readonly DTB_SIZE=27636

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 2 ]] || die "usage: $0 SOURCE_BOOT_IMAGE OUTPUT_DTB"
source_image=$1
output=$2
for command in dd dirname mkdir mv sha256sum stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -f "$source_image" && ! -L "$source_image" ]] || die 'source image is missing or unsafe'
[[ "$(sha256sum "$source_image" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'runtime-proven source image changed'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output'
parent=$(dirname -- "$output")
mkdir -p -- "$parent"
partial="$output.partial"
trap 'rm -f -- "$partial"' EXIT HUP INT TERM
dd if="$source_image" of="$partial" bs=1 skip="$DTB_OFFSET" count="$DTB_SIZE" status=none
[[ "$(stat -f '%z' "$partial" 2>/dev/null || stat -c '%s' "$partial")" == "$DTB_SIZE" ]] ||
	die 'extracted DTB size changed'
[[ "$(sha256sum "$partial" | awk '{print $1}')" == "$DTB_SHA256" ]] ||
	die 'extracted DTB identity changed'
mv -- "$partial" "$output"
trap - EXIT HUP INT TERM
printf 'control_dtb_sha256=%s\ncontrol_dtb_size=%s\nresult=pass\n' "$DTB_SHA256" "$DTB_SIZE"
