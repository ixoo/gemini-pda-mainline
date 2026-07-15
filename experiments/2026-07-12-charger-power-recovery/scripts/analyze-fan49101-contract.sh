#!/usr/bin/env bash

# Emit a bounded, source-level FAN49101 regulator contract. The vendor
# checkout is immutable evidence; this script records hashes and selected
# register anchors without copying the implementation into the repository.

set -euo pipefail
export LC_ALL=C

vendor_tree=${1:-${HOME}/src/reference/planet-mt6797-3.18}
linux_tree=${2:-${HOME}/src/gemini-pda/linux-7.1.3}
vendor_header=drivers/misc/mediatek/power/mt6797/fan49101.h
vendor_source=drivers/misc/mediatek/power/mt6797/fan49101.c
linux_source=drivers/regulator/fan53555.c

[[ -d "${vendor_tree}/.git" ]] || {
	printf 'vendor tree is not a git checkout: %s\n' "${vendor_tree}" >&2
	exit 1
}
[[ -r "${linux_tree}/${linux_source}" ]] || {
	printf 'Linux regulator source is missing: %s\n' "${linux_tree}/${linux_source}" >&2
	exit 1
}

blob_hash() {
	local path=$1
	git -C "${vendor_tree}" show "HEAD:${path}" | sha256sum | awk '{print $1}'
}

printf 'audit=fan49101-register-contract\n'
printf 'vendor_tree=%s\n' "${vendor_tree}"
printf 'vendor_commit=%s\n' "$(git -C "${vendor_tree}" rev-parse HEAD)"
printf 'linux_tree=%s\n' "${linux_tree}"
printf 'vendor_blob_sha256[%s]=%s\n' "${vendor_header}" "$(blob_hash "${vendor_header}")"
printf 'vendor_blob_sha256[%s]=%s\n' "${vendor_source}" "$(blob_hash "${vendor_source}")"
printf 'linux_file_sha256[%s]=%s\n' "${linux_source}" "$(sha256sum "${linux_tree}/${linux_source}" | awk '{print $1}')"

printf '\n[vendor_register_definitions]\n'
git -C "${vendor_tree}" show "HEAD:${vendor_header}" |
	grep -nE 'FAN49101_(SOFTRESET|VOUT|CONTROL|ID1|ID2)|FAN49101_VENDOR_FAIRCHILD' || true

printf '\n[vendor_identity_and_voltage_anchors]\n'
git -C "${vendor_tree}" show "HEAD:${vendor_source}" |
	grep -nE 'fan49101_(hw_component_detect|hw_init|vosel)|FAN49101_ID[12]|FAN49101_VENDOR_FAIRCHILD|603000|12826|reg_val \| 0x80|0xB2|0x8A|0xA0' || true

printf '\n[linux_nearest_family_anchors]\n'
grep -nE 'FAN53555_VSEL0|VSEL_BUCK_EN|DIE_ID|FAN53555_NVOLTAGES|vsel_min|vsel_step|compatible' \
	"${linux_tree}/${linux_source}" | head -n 100 || true

printf '\n[decision]\n'
printf '%s\n' \
	'FAN49101 is a separate buck-boost protocol with registers 0x00, 0x01, 0x02, 0x40, and 0x41' \
	'vendor identity accepts manufacturer 0x83 at register 0x40 and reads die ID at 0x41' \
	'vendor VOUT uses a 0.603 V base, 12.826 mV step, and enable bit 7 in register 0x01' \
	'vendor control and reset semantics require board-level validation before regulator operations' \
	'Linux fan53555 must not be reused by compatible-string substitution; write a dedicated fan49101 regulator driver and binding'
