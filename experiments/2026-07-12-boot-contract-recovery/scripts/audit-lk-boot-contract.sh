#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the public Planet Gemini Android 8 LK boot contract.
# It never flashes, writes partitions, or executes a vendor binary.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_ROOT=${REPO_ROOT:-"$(cd "$SCRIPT_DIR/../../.." && pwd -P)"}
LK_TREE=${LK_TREE:-"$HOME/src/reference/dguidipc-gemini-lk-android8"}
LK_COMMIT=${LK_COMMIT:-HEAD}
VENDOR_IMAGE=${VENDOR_IMAGE:-"$REPO_ROOT/artifacts/vendor-kernel/gemian-2019/boot.img"}
CURRENT_PACKAGE=${CURRENT_PACKAGE:-"$HOME/artifacts/gemini-pda/linux-7.1.3-gemini-86145c09fc00"}

die() {
	echo "error: $*" >&2
	exit 1
}

command -v git >/dev/null || die "git is required"
command -v sha256sum >/dev/null || die "sha256sum is required"
command -v python3 >/dev/null || die "python3 is required"
[[ -d "$LK_TREE/.git" ]] || die "LK Git tree is missing: $LK_TREE"
[[ -f "$VENDOR_IMAGE" ]] || die "vendor Android boot image is missing: $VENDOR_IMAGE"

LK_COMMIT=$(git -C "$LK_TREE" rev-parse "$LK_COMMIT")
readonly LK_COMMIT
LK_FILES=(
	lk/app/aboot/bootimg.h
	lk/app/mt_boot/decompressor.c
	lk/app/mt_boot/mt_boot.c
	lk/platform/mt6797/rules.mk
)

hash_git_file() {
	git -C "$LK_TREE" show "$LK_COMMIT:$1" | sha256sum | awk '{print $1}'
}

source_contains() {
	local file="$1"
	local text="$2"
	git -C "$LK_TREE" show "$LK_COMMIT:$file" | grep -Fq -- "$text" || \
		die "LK source contract changed: $file does not contain: $text"
}

for file in "${LK_FILES[@]}"; do
	git -C "$LK_TREE" cat-file -e "$LK_COMMIT:$file" || die "missing LK source: $file"
done

source_contains lk/app/mt_boot/mt_boot.c 'bootopt_str[i + 0x12]'
source_contains lk/app/mt_boot/mt_boot.c 'g_is_64bit_kernel = 1'
source_contains lk/app/mt_boot/mt_boot.c 'g_boot_hdr->kernel_addr & 0x7FFFF'
source_contains lk/app/mt_boot/mt_boot.c 'FDT_MAGIC'
source_contains lk/app/mt_boot/mt_boot.c 'zimage_size = (g_boot_hdr->kernel_sz)'
source_contains lk/app/mt_boot/mt_boot.c 'decompress_outbuf_size = KERNEL_DECOMPRESS_SIZE'
source_contains lk/app/mt_boot/decompressor.c 'ret = gunzip(in, &lenp, out, outlen)'
source_contains lk/platform/mt6797/rules.mk 'KERNEL_DECOMPRESS_SIZE := 0x03200000'

echo "validation=planet-gemini-lk-android8-boot-contract"
printf 'lk_tree=%s\n' "$LK_TREE"
printf 'lk_commit=%s\n' "$LK_COMMIT"
printf 'boot_image=%s\n' "$VENDOR_IMAGE"
printf 'boot_image_sha256=%s\n' "$(sha256sum "$VENDOR_IMAGE" | awk '{print $1}')"
for file in "${LK_FILES[@]}"; do
	printf 'lk_%s_sha256=%s\n' "${file//\//_}" "$(hash_git_file "$file")"
done

echo
echo "[source_contract]"
echo "boot_magic=ANDROID!"
echo "android_v0_page_header=yes"
echo "bootopt_64_selects_gzip_path=yes"
echo "kernel_addr_alignment_mask=0x7ffff"
echo "generic_decompress_output_limit=0x1c00000"
echo "mt6797_platform_decompress_output_limit=0x03200000"
echo "dtb_source=appended_kernel_payload_scan"
echo "header_dt_size_used_by_64bit_path=no"
echo "hardware_write=none"

echo
echo "[vendor_image]"
python3 "$SCRIPT_DIR/analyze-lk-boot-image.py" "$VENDOR_IMAGE"

if [[ -f "$CURRENT_PACKAGE/Image" ]]; then
	echo
	echo "[current_package]"
	printf 'package=%s\n' "$CURRENT_PACKAGE"
	for file in Image Image.gz; do
		if [[ -f "$CURRENT_PACKAGE/$file" ]]; then
			printf '%s_size=%s\n' "$file" "$(stat -c '%s' "$CURRENT_PACKAGE/$file")"
			printf '%s_sha256=%s\n' "$file" "$(sha256sum "$CURRENT_PACKAGE/$file" | awk '{print $1}')"
		else
			printf '%s=absent\n' "$file"
		fi
	done
fi

echo
echo "[decision]"
echo "retained_planet_lk_requires_gzip_for_64bit_kernel=yes"
echo "retained_planet_lk_requires_appended_dtb=yes"
echo "raw_uncompressed_Image_is_not_a_valid_64bit_LK_payload=yes"
echo "header_dt_field_candidate_is_not_sufficient_for_this_LK=yes"
echo "kernel_addr_0x40080000_is_512KiB_aligned=yes"
if [[ -f "$CURRENT_PACKAGE/Image" ]]; then
	image_size=$(stat -c '%s' "$CURRENT_PACKAGE/Image")
	if (( image_size > 0x03200000 )); then
		echo "current_raw_Image_exceeds_mt6797_decompress_limit=yes"
	else
		echo "current_raw_Image_exceeds_mt6797_decompress_limit=no"
	fi
fi
echo "mainline_candidate_boot_acceptance=not_attempted"
echo "hardware_write=none"
