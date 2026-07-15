#!/usr/bin/env bash

# Reconstruct and inspect a symbol-bearing ELF from a captured vendor kernel.
# Run in the Linux development VM; never boot or execute the captured image.

set -euo pipefail
export LC_ALL=C

image=${1:?usage: $0 IMAGE.GZ-DTB [WORKDIR]}
[[ -r "${image}" ]] || {
	printf 'not readable: %s\n' "${image}" >&2
	exit 1
}
command -v vmlinux-to-elf >/dev/null 2>&1 || {
	printf 'vmlinux-to-elf is not provisioned\n' >&2
	exit 1
}

workdir=${2:-${HOME}/reverse-engineering/work/gemini-kernel}
mkdir -p "${workdir}"
elf="${workdir}/vmlinux.elf"

printf 'image=%s\n' "${image}"
file "${image}"
sha256sum "${image}"
vmlinux-to-elf "${image}" "${elf}"
printf '\n===== reconstructed ELF =====\n'
file "${elf}"
printf '\n===== sensor symbols =====\n'
nm -n "${elf}" | grep -E \
	'(hwmsen_get_convert|bmi160_(acc|gyro)|stk3x1x_(read_id|get_als_value|write_state|write_flag))' | \
	head -n 220 || true
printf '\n===== orientation helper disassembly =====\n'
objdump -d -C --disassemble=hwmsen_get_convert "${elf}"
printf '\n===== direction conversion table bytes =====\n'
printf '%s\n' 'The reconstructed image places the eight 8-byte records at 0xffffffc00138dc30.'
objdump -s --start-address=0xffffffc00138dc30 --stop-address=0xffffffc00138dc70 "${elf}" || true
printf '\n===== BMI160 conversion paths =====\n'
objdump -d -C --disassemble=bmi160_acc_read_sensor_data.isra.19 "${elf}" || true
objdump -d -C --disassemble=bmg_read_sensor_data.isra.9 "${elf}" || true
printf '\n===== BMI160 probe and identity paths =====\n'
objdump -d -C --start-address=0xffffffc0004d4000 \
	--stop-address=0xffffffc0004d4098 "${elf}" || true
objdump -d -C --disassemble=bmi160_acc_init_client "${elf}" || true
objdump -d -C --disassemble=bmg_init_client "${elf}" || true
objdump -d -C --disassemble=bmi160_acc_i2c_probe "${elf}" || true
objdump -d -C --disassemble=bmi160_gyro_i2c_probe "${elf}" || true
printf '\n===== BMI160 diagnostic sysfs boundary =====\n'
objdump -d -C --disassemble=bmi160_bmi_value_show "${elf}" || true
objdump -d -C --disassemble=bmi160_show_reg_val "${elf}" || true
objdump -d -C --disassemble=bmi160_read_reg "${elf}" || true
objdump -d -C --disassemble=bmi160_write_reg "${elf}" || true
objdump -d -C --disassemble=bmi160_store_reg_val "${elf}" || true
printf '\n===== sensor symbol strings =====\n'
strings -a "${elf}" | grep -E \
	'^(hwmsen_get_convert|bmi160_(acc|gyro)|stk3x1x_)' | \
	head -n 220 || true
printf '\nreconstructed_elf=%s\n' "${elf}"
