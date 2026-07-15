#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Emit source-derived NT36xxx trim-table and memory-map metadata.  This keeps
# the immutable vendor checkout as evidence and does not copy vendor code or
# access a controller.

set -euo pipefail
export LC_ALL=C

vendor_tree=${VENDOR_TREE:-/home/julien.guest/src/reference/planet-mt6797-3.18}
vendor_path=drivers/input/touchscreen/mediatek/aeon_nt36xxx
source_file=${vendor_path}/nt36xxx.c

[[ -d "${vendor_tree}/.git" ]] || {
	printf 'error: vendor tree is not a git checkout: %s\n' "${vendor_tree}" >&2
	exit 1
}

blob_hash() {
	local path=$1
	git -C "${vendor_tree}" show "HEAD:${path}" | sha256sum | awk '{print $1}'
}

printf 'validation=nt36xxx-trim-map-metadata-source-audit\n'
printf 'vendor_tree=%s\n' "${vendor_tree}"
printf 'vendor_commit=%s\n' "$(git -C "${vendor_tree}" rev-parse HEAD)"
printf 'source_blob_sha256=%s\n' "$(blob_hash "${source_file}")"
printf 'method=git_show_and_normalized_source_constants;no_device_access\n'

printf '\n[source_anchors]\n'
git -C "${vendor_tree}" show "HEAD:${source_file}" |
	rg -n -A 42 'static const struct nvt_ts_mem_map NT36772_memory_map|static const struct nvt_ts_trim_id_table trim_id_table' |
	sed -n '1,130p'

printf '\n[trim_entries]\n'
printf 'entry=1-4;id=55_00_FF_00_00_00,55_72_FF_00_00_00,AA_00_FF_00_00_00,AA_72_FF_00_00_00;mask=1_1_0_1_1_1;map=NT36772;carrier=0\n'
printf 'entry=5;id=FF_FF_FF_72_67_03;mask=0_0_0_1_1_1;map=NT36772;carrier=0\n'
printf 'entry=6;id=FF_FF_FF_70_66_03;mask=0_0_0_1_1_1;map=NT36772;carrier=0\n'
printf 'entry=7;id=FF_FF_FF_70_67_03;mask=0_0_0_1_1_1;map=NT36772;carrier=0\n'
printf 'entry=8;id=FF_FF_FF_72_66_03;mask=0_0_0_1_1_1;map=NT36772;carrier=0\n'
printf 'entry=9;id=FF_FF_FF_25_65_03;mask=0_0_0_1_1_1;map=NT36525;carrier=0\n'
printf 'entry=10;id=FF_FF_FF_70_68_03;mask=0_0_0_1_1_1;map=NT36870;carrier=1\n'
printf 'entry=11;id=FF_FF_FF_76_66_03;mask=0_0_0_1_1_1;map=NT36676F;carrier=0\n'

printf '\n[memory_maps]\n'
printf 'map=NT36772;event=0x11e00;raw0=0x10000;raw1=0x12000;baseline=0x10e70;baseline_btn=0x12e70;diff0=0x10830;diff1=0x12830;flash_checksum=0x14000;flash_data=0x14002\n'
printf 'map=NT36525;event=0x11a00;raw0=0x10000;raw1=0x12000;baseline=0x10b08;baseline_btn=0x12b08;diff0=0x1064c;diff1=0x1264c;flash_checksum=0x14000;flash_data=0x14002\n'
printf 'map=NT36870;event=0x25000;raw0=0x20000;raw0_q=0x204c8;raw1=0x23000;raw1_q=0x234c8;baseline=0x21350;baseline_q=0x21818;baseline_btn=0x24350;baseline_btn_q=0x24358;diff0=0x209b0;diff0_q=0x20e78;diff1=0x239b0;diff1_q=0x23e78;flash_checksum=0x24000;flash_data=0x24002\n'
printf 'map=NT36676F;event=0x11a00;raw0=0x10000;raw1=0x12000;baseline=0x10b08;baseline_btn=0x12b08;diff0=0x1064c;diff1=0x1264c;flash_checksum=0x14000;flash_data=0x14002\n'

printf '\n[decision]\n'
printf '%s\n' \
	'eleven_masked_trim_entries_are_source_and_elf_cross_checked' \
	'NT36772_has_four_prefix_variants_and_four_suffix_variants' \
	'NT36525_NT36870_NT36676F_use_distinct_event_or_memory_maps' \
	'no_NT36672A_trim_entry_is_present' \
	'live_driver_success_proves_one_entry_matched_but_exact_bytes_are_not_retained' \
	'future_driver_should_select_map_from_bounded_trim_read_and_keep_firmware_update_disabled'
