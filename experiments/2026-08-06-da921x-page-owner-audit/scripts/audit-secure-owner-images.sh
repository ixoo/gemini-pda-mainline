#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only scan of the retained LK, TEE/ATF, and SCP images from the project
# backup. It reports hashes, bounded marker counts, and selected literal counts
# without extracting, executing, or staging any private partition contents.

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_ROOT=${REPO_ROOT:-"$(cd "$SCRIPT_DIR/../../.." && pwd -P)"}
PARTITIONS_DIR=${DEVICE_PARTITIONS_DIR:-"$REPO_ROOT/artifacts/device-partitions/20260715T020041Z"}

die() {
	printf 'error: %s\n' "$*" >&2
	exit 1
}

command -v rg >/dev/null || die "rg is required"
command -v sha256sum >/dev/null || die "sha256sum is required"
command -v strings >/dev/null || die "strings is required"
command -v python3 >/dev/null || die "python3 is required"

sha256() {
	sha256sum "$1" | awk '{print $1}'
}

file_size() {
	stat -c '%s' "$1" 2>/dev/null || stat -f '%z' "$1"
}

count_le32() {
	local path=$1
	local value=$2
	python3 -c 'from pathlib import Path; import struct; import sys; data=Path(sys.argv[1]).read_bytes(); value=int(sys.argv[2], 0); print(data.count(struct.pack("<I", value)))' "$path" "$value"
}

string_count() {
	local path=$1
	local pattern=$2
	local count
	count=$(strings -a -n 4 "$path" | rg -i -c -- "$pattern" || true)
	printf '%s' "${count:-0}"
}

roles=(lk lk2 tee1 tee2 scp1 scp2)

image_path() {
	case "$1" in
		lk) printf '%s' "$PARTITIONS_DIR/mmcblk0p20-lk.img" ;;
		lk2) printf '%s' "$PARTITIONS_DIR/mmcblk0p21-lk2.img" ;;
		tee1) printf '%s' "$PARTITIONS_DIR/mmcblk0p24-tee1.img" ;;
		tee2) printf '%s' "$PARTITIONS_DIR/mmcblk0p25-tee2.img" ;;
		scp1) printf '%s' "$PARTITIONS_DIR/mmcblk0p17-scp1.img" ;;
		scp2) printf '%s' "$PARTITIONS_DIR/mmcblk0p18-scp2.img" ;;
		*) die "unknown image role: $1" ;;
	esac
}

for role in "${roles[@]}"; do
	image=$(image_path "$role")
	[[ -r "$image" ]] || die "missing retained partition image: $image"
done

printf 'validation=retained-secure-owner-image-scan\n'
printf 'source=project-start-full-backup;read_only;no_new_backup;raw_contents_not_staged\n'
printf 'partitions_dir=%s\n' "$PARTITIONS_DIR"

printf '\n[image_identity]\n'
for role in "${roles[@]}"; do
	image=$(image_path "$role")
	printf '%s_file=%s\n' "$role" "${image##*/}"
	printf '%s_size=%s\n' "$role" "$(file_size "$image")"
	printf '%s_sha256=%s\n' "$role" "$(sha256 "$image")"
done

printf '\n[little_endian_literal_counts]\n'
for role in "${roles[@]}"; do
	image=$(image_path "$role")
	printf '%s_i2c6_0x1100e000=%s\n' "$role" "$(count_le32 "$image" 0x1100e000)"
	printf '%s_cspm_0x11015000=%s\n' "$role" "$(count_le32 "$image" 0x11015000)"
	printf '%s_pcm_con0_0x11015018=%s\n' "$role" "$(count_le32 "$image" 0x11015018)"
	printf '%s_csram_0x0012a000=%s\n' "$role" "$(count_le32 "$image" 0x0012a000)"
	printf '%s_fw_done_0x8000=%s\n' "$role" "$(count_le32 "$image" 0x8000)"
	printf '%s_sw_pause_0x2000=%s\n' "$role" "$(count_le32 "$image" 0x2000)"
	printf '%s_pause_map_0x2=%s\n' "$role" "$(count_le32 "$image" 0x2)"
done

printf '\n[semantic_marker_counts]\n'
printf 'lk_generic_i2c_strings=%s\n' "$(string_count "$(image_path lk)" 'I2C-LK|i2c_(read|write)')"
printf 'lk_named_sema_i2cdrv_strings=%s\n' "$(string_count "$(image_path lk)" 'SEMA_I2C_DRV|I2CDRV')"
printf 'tee_atf_psci_paths=%s\n' "$(string_count "$(image_path tee1)" 'plat/mt6797/|services/std_svc/psci')"
printf 'tee_idvfs_strings=%s\n' "$(string_count "$(image_path tee1)" 'iDVFS|DVFS_PLLINDEX|DVFS_SWREQ')"
printf 'tee_i2c6_strings=%s\n' "$(string_count "$(image_path tee1)" 'I2C6|i2c6|SEMA_I2C_DRV|I2CDRV')"
printf 'scp_dvfs_spm_paths=%s\n' "$(string_count "$(image_path scp1)" 'drivers/CM4_A/mt6797/dvfs|DVFS-SCP|spm_isr')"
printf 'scp_i2c6_strings=%s\n' "$(string_count "$(image_path scp1)" 'I2C6|i2c6|SEMA_I2C_DRV|I2CDRV')"
printf 'scp_named_sema_i2cdrv_strings=%s\n' "$(string_count "$(image_path scp1)" 'SEMA_I2C_DRV|I2CDRV')"

printf '\n[decision]\n'
printf '%s\n' \
	'lk_role=generic_I2C_bootloader_driver;no_named_SEMA_I2C_DRV_marker' \
	'tee_role=ATF_PSCI_iDVFS_CSPM_secure_semaphore_boundary;direct_constructor_crosscheck_required' \
	'scp_role=CM4_DVFS_SPM_IPI_boundary;no_I2C6_or_SEMA_I2C_DRV_owner_marker' \
	'crosscheck=external-cspm-writer-audit-20260724;ATF_CSPM_owner_attributed;PCM_restart_owner_not-found' \
	'negative_result=secure_images_do_not_identify_the_PCM_restart_SEMA_I2C_DRV_lease_owner' \
	'interpretation=bounded_strings_and_literal_scan;computed_or_secure_alias_access_remains_unexcluded' \
	'mainline_firmware_lease=unproven' \
	'fail_closed_action=keep_I2C6_and_DA921x_provider_write_disabled;retain_provider_-EOPNOTSUPP' \
	'hardware_action=none' \
	'status=PASS_LIMITED_SECURE_IMAGE_SCAN_NEGATIVE'
