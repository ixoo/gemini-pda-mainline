#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Compare private copies of the vendor Novatek firmware without copying,
# decoding, or modifying the firmware. The emitted metadata is safe to review;
# the firmware itself must remain under the Git-ignored artifacts tree.

set -euo pipefail
export LC_ALL=C

root=${1:-artifacts}
expected_size=118784
[[ -d "$root" ]] || {
	printf 'error=firmware_root_missing:%s\n' "$root" >&2
	exit 1
}

hashes=$(mktemp)
sizes=$(mktemp)
trap 'rm -f "$hashes" "$sizes"' EXIT

copy_count=0
while IFS= read -r -d '' path; do
	copy_count=$((copy_count + 1))
	sha256sum "$path" | awk '{print $1}' >> "$hashes"
	wc -c < "$path" | tr -d ' ' >> "$sizes"
done < <(find "$root" -type f -name novatek_ts_fw.bin -print0)

printf 'validation=novatek-firmware-copy-audit\n'
printf 'root=%s\n' "$root"
printf 'copy_count=%s\n' "$copy_count"
printf 'expected_size=%s\n' "$expected_size"
printf 'unique_sha256=%s\n' "$(sort -u "$hashes" | paste -sd, -)"
printf 'unique_sizes=%s\n' "$(sort -nu "$sizes" | paste -sd, -)"
printf 'all_expected_size=%s\n' "$(awk -v expected="$expected_size" '$1 != expected { bad=1 } END { print bad ? "false" : "true" }' "$sizes")"
printf 'all_copies_byte_identical=%s\n' "$(test "$(sort -u "$hashes" | wc -l | tr -d ' ')" -eq 1 && echo true || echo false)"
printf 'firmware_read=metadata_hash_and_size_only\n'
printf 'firmware_write=none\n'
