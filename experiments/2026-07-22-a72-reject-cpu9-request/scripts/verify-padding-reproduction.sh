#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s RAW_BOOT_IMAGE\n' "$0" >&2; }

[[ "$#" -eq 1 ]] || { usage; exit 2; }
raw=$1
[[ -f "$raw" && ! -L "$raw" && -s "$raw" ]] || \
	die 'raw boot image is missing, empty, non-regular, or a symlink'

for command in awk chmod cmp dd install mktemp rmdir rm sha256sum tail tr \
	truncate wc; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

readonly target_size=$((16 * 1024 * 1024))
raw_size=$(wc -c <"$raw" | tr -d ' ')
[[ "$raw_size" =~ ^[0-9]+$ ]] || die 'raw boot image size is malformed'
((raw_size > 0 && raw_size < target_size)) || \
	die 'raw boot image does not fit the 16 MiB target'
readonly raw_size
readonly tail_size=$((target_size - raw_size))

workdir=$(mktemp -d /tmp/candidate-ak-padding.XXXXXX)
first=$workdir/truncate.img
second=$workdir/zero-overlay.img
cleanup() {
	rm -f -- "$first" "$second"
	rmdir -- "$workdir"
}
trap cleanup EXIT

# Construction 1: copy the exact raw image, then extend it sparsely with zeros.
install -m 0600 "$raw" "$first"
truncate -s "$target_size" "$first"

# Construction 2: allocate a complete zero image, then overlay the raw prefix.
dd if=/dev/zero of="$second" bs=1048576 count=16 status=none
dd if="$raw" of="$second" bs=1048576 conv=notrunc status=none
chmod 0600 "$second"

for padded in "$first" "$second"; do
	[[ "$(wc -c <"$padded" | tr -d ' ')" == "$target_size" ]] || \
		die 'padded image has the wrong size'
	cmp -n "$raw_size" "$raw" "$padded" >/dev/null || \
		die 'padded image does not retain the exact raw prefix'
	tail -c "$tail_size" "$padded" | \
		cmp -n "$tail_size" - /dev/zero >/dev/null || \
		die 'padded image tail is not entirely zero'
done
cmp -s "$first" "$second" || die 'independent padded constructions differ'

raw_sha256=$(sha256sum "$raw" | awk '{print $1}')
first_sha256=$(sha256sum "$first" | awk '{print $1}')
second_sha256=$(sha256sum "$second" | awk '{print $1}')
[[ "$first_sha256" == "$second_sha256" ]] || \
	die 'independent padded SHA-256 identities differ'

printf 'validation=candidate-ak-padding-reproduction\n'
printf 'raw_sha256=%s\n' "$raw_sha256"
printf 'raw_size=%s\n' "$raw_size"
printf 'target_size=%s\n' "$target_size"
printf 'truncate_construction_sha256=%s\n' "$first_sha256"
printf 'zero_overlay_construction_sha256=%s\n' "$second_sha256"
printf 'raw_prefix=byte-exact-twice\n'
printf 'zero_tail=verified-twice\n'
printf 'temporary_images=removed-on-exit\n'
printf 'device_access=none\n'
