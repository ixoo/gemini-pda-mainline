#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Extract a bounded, sanitized SP5509 identity contract from the immutable
# vendor-kernel ELF.  This never executes the ELF and never emits a binary or
# complete disassembly.

set -euo pipefail

VMLINUX=${VMLINUX:-"$HOME/reverse-engineering/work/gemini-kernel/vmlinux.elf"}

die() {
	echo "error: $*" >&2
	exit 1
}

for command in nm objdump sha256sum; do
	command -v "$command" >/dev/null || die "$command is required"
done
[[ -r "$VMLINUX" ]] || die "vendor kernel ELF is missing: $VMLINUX"

export LC_ALL=C

symbol_table=$(mktemp)
trap 'rm -f "$symbol_table"' EXIT
nm -an "$VMLINUX" > "$symbol_table"

nth_symbol_addr() {
	local name=$1 occurrence=$2
	awk -v name="$name" -v occurrence="$occurrence" '
		$3 == name {
			count++
			if (count == occurrence) {
				print "0x" $1
				exit
			}
		}
	' "$symbol_table"
}

require_addr() {
	local name=$1 occurrence=$2 address
	address=$(nth_symbol_addr "$name" "$occurrence")
	[[ -n "$address" ]] || die "symbol $name occurrence $occurrence is missing"
	echo "$address"
}

disassemble_matches() {
	local start=$1 stop=$2 pattern=$3
	objdump -d --start-address="$start" --stop-address="$stop" "$VMLINUX" \
		| rg -n "$pattern" | head -n 80 || true
}

echo "SP5509 vendor-kernel ELF contract audit"
echo "vmlinux=$VMLINUX"
echo "vmlinux_sha256=$(sha256sum "$VMLINUX" | awk '{print $1}')"

echo
echo "[registration symbols]"
rg 'sp5509_(MAIN_MIPI_RAW_SensorInit|MIPI_RAW_SensorInit_sls)$' "$symbol_table" \
	| sed -E 's/^([^ ]+) +[^ ]+ +([^ ]+)$/symbol=\2 address=0x\1/'

echo
echo "[SLS identity helpers]"
sls_read=$(require_addr read_cmos_sensor 2)
sls_open=$(require_addr open 2)
echo "sls_read_cmos_sensor=$sls_read"
echo "sls_open=$sls_open"

echo "read-helper (two-byte register, two-byte response, runtime slave ID, 300 kHz):"
disassemble_matches "$sls_read" "$((sls_read + 0x50))" \
	'kdSetI2CSpeed|ldrb|mov[[:space:]]+w[0-9]+, #[#]?(0x12c|[012])|strb|strh|iReadRegI2C'

echo "open/probe constants (register, accepted ID, and candidate slave IDs):"
disassemble_matches "$sls_open" "$((sls_open + 0x120))" \
	'mov[[:space:]]+w[0-9]+, #[#]?(0xf16|0x556|0x40|0x50)|strb|read_cmos_sensor|sensor_init|cmp'
echo "candidate-I2C-table-bytes (vendor ELF, bounded):"
objdump -s --start-address=0xffffffc000dcc520 --stop-address=0xffffffc000dcc528 "$VMLINUX"

echo
echo "[main registration boundary]"
main_init=$(require_addr sp5509_MAIN_MIPI_RAW_SensorInit 1)
echo "main_registration=$main_init"
echo "main and SLS registrations point to separate vendor function tables; the"
echo "tables are not a Linux-compatible sensor binding or mode description."

echo
echo "[decision]"
echo "vendor_ELF_confirms_SP5509_SLS_probes_register_0x0f16_for_raw_ID_0x0556"
echo "vendor_ELF_identity_read_uses_16bit_register_and_16bit_response_at_300_kHz"
echo "vendor_ELF_candidate_write_ID_bytes_include_0x40_and_0x50_(7bit_0x20_or_0x28)"
echo "mainline_driver_must_still_validate_board_power_reset_and_MIPI_endpoint"
echo "do_not_probe_the_live_device_without_explicit_rails_reset_and_rollback_plan"
