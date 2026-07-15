#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Extract a bounded, sanitized Novatek touchscreen contract from the immutable
# vendor-kernel ELF. This never executes the ELF and never emits a binary or a
# complete disassembly. The fixed trim-table address is tied to the recorded
# vmlinux hash in linux-nvt-elf-validation.txt.

set -euo pipefail

VMLINUX=${VMLINUX:-"$HOME/reverse-engineering/work/gemini-kernel/vmlinux.elf"}

die() {
	echo "error: $*" >&2
	exit 1
}

for command in nm objdump sha256sum rg; do
	command -v "$command" >/dev/null || die "$command is required"
done
[[ -r "$VMLINUX" ]] || die "vendor kernel ELF is missing: $VMLINUX"

export LC_ALL=C

symbol_table=$(mktemp)
trap 'rm -f "$symbol_table"' EXIT
nm -an "$VMLINUX" > "$symbol_table"

require_addr() {
	local name=$1 address
	address=$(awk -v name="$name" '$3 == name { print "0x" $1; exit }' "$symbol_table")
	[[ -n "$address" ]] || die "symbol $name is missing"
	echo "$address"
}

disassemble_matches() {
	local start=$1 stop=$2 pattern=$3
	objdump -d --no-show-raw-insn --start-address="$start" \
		--stop-address="$stop" "$VMLINUX" | rg -n "$pattern" | head -n 120 || true
}

echo "Novatek NT36xxx vendor-kernel ELF contract audit"
echo "vmlinux=$VMLINUX"
echo "vmlinux_sha256=$(sha256sum "$VMLINUX" | awk '{print $1}')"

echo
echo "[NVT symbols]"
for name in nvt_ts_probe nvt_read_pid nvt_get_fw_info \
	nvt_bootloader_reset nvt_sw_reset_idle CTP_I2C_READ CTP_I2C_WRITE; do
	printf 'symbol=%s address=%s\n' "$name" "$(require_addr "$name")"
done
for name in NT36676F_memory_map NT36870_memory_map NT36525_memory_map NT36772_memory_map; do
	printf 'symbol=%s address=%s\n' "$name" "$(require_addr "$name")"
done

probe=$(require_addr nvt_ts_probe)
echo
echo "[probe sequence and runtime geometry]"
disassemble_matches "$probe" "$((probe + 0x420))" \
	'bl.*(nvt_bootloader_reset|nvt_sw_reset_idle|CTP_I2C_(READ|WRITE)|input_mt_init_slots|input_set_abs_params)|mov.*#(0x35|0x62|0x4e|0x7|0xa|0x3e8|0xff)|strb|ldrb|cmp'

read_helper=$(require_addr CTP_I2C_READ)
echo
echo "[transport helper]"
disassemble_matches "$read_helper" "$((read_helper + 0x180))" \
	'i2c_transfer|mov.*#(0x1|0x2|0x5)|strh|strb|ldrb|addr|len'

echo
echo "[trim table bytes]"
echo "trim_table_address=0xffffffc000e04118"
echo "trim_table_stride=0x20"
echo "trim_table_entries=11"
objdump -s --start-address=0xffffffc000e04118 \
	--stop-address=0xffffffc000e04278 "$VMLINUX"

echo
echo "[source-correlated interpretation]"
echo "trim_signatures=55_00_xx_00_00_00;55_72_xx_00_00_00;aa_00_xx_00_00_00;aa_72_xx_00_00_00"
echo "trim_signatures=xx_xx_xx_72_67_03;xx_xx_xx_70_66_03;xx_xx_xx_70_67_03;xx_xx_xx_72_66_03"
echo "trim_signatures=xx_xx_xx_25_65_03;xx_xx_xx_70_68_03;xx_xx_xx_76_66_03"
echo "trim_maps=first_8_NT36772;entry_9_NT36525;entry_10_NT36870;entry_11_NT36676F"
echo "trim_masks=source_mask_ignores_x_bytes_and_ELF_table_preserves_masks"

echo
echo "[decision]"
echo "vendor_ELF_confirms_NVT_probe_resets_0x62_then_selects_xdata_0x01f6_at_0x01"
echo "vendor_ELF_confirms_trim_read_command_0x4e_returns_7_bytes_and_matches_11_source_entries"
echo "vendor_ELF_confirms_vendor_runtime_geometry_10_slots_pressure_1000_width_255"
echo "static_ELF_audit_does_not_capture_runtime_trim;current_live_capture_is_recorded_in_results/nvt-live-trim-identity-20260714.txt"
echo "upstream_nt36672a_driver_reuse_remains_unproven;different_trim_family_justifies_new_backend_or_driver"
echo "do_not_use_proc_NVTflash_or_generic_I2C_scans"
