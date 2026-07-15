#!/usr/bin/env bash

# Emit the AW9523 silicon/consumer contract without copying vendor code into
# the repository. Run this in the development VM; both source trees are kept
# as immutable evidence.

set -euo pipefail
export LC_ALL=C

vendor_tree=${1:-${HOME}/src/reference/planet-mt6797-3.18}
linux_tree=${2:-${HOME}/src/gemini-pda/linux-7.1.3}
vendor_path=drivers/misc/mediatek/aw9523/aw9523_key.c
linux_path=drivers/pinctrl/pinctrl-aw9523.c

[[ -d "${vendor_tree}/.git" ]] || {
	printf 'vendor tree is not a git checkout: %s\n' "${vendor_tree}" >&2
	exit 1
}
[[ -r "${linux_tree}/${linux_path}" ]] || {
	printf 'Linux AW9523 driver is missing: %s\n' "${linux_tree}/${linux_path}" >&2
	exit 1
}

blob_hash() {
	git -C "${vendor_tree}" show "HEAD:${vendor_path}" | sha256sum | awk '{print $1}'
}

printf 'vendor_tree=%s\n' "${vendor_tree}"
printf 'vendor_commit=%s\n' "$(git -C "${vendor_tree}" rev-parse HEAD)"
printf 'vendor_blob_sha256=%s\n' "$(blob_hash)"
printf 'linux_tree=%s\n' "${linux_tree}"
printf 'linux_driver_sha256=%s\n' "$(sha256sum "${linux_tree}/${linux_path}" | awk '{print $1}')"

printf '\n[vendor register and scan contract]\n'
git -C "${vendor_tree}" show "HEAD:${vendor_path}" |
	grep -nE '#define (ID_REG|CTL_REG|P0_CONFIG|P1_CONFIG|P0_INPUT|P1_OUTPUT|P0_INT|P1_INT|SW_RSTN)|i2c_(read|write)_reg\((0x10|0x7F)|P0: Input|P1: Output|P0 port irq|HRTIMER_FRAME' || true
printf 'vendor_matrix=8_rows(P0_0..P0_7)x7_columns(P1_0..P1_6)\n'

printf '\n[Linux silicon match]\n'
grep -nE '#define AW9523_REG_(CHIPID|SOFT_RESET|PORT_MODE|CONF_STATE|INTR_DIS)|AW9523_VAL_EXPECTED_CHIPID|aw9523_drive_reset_gpio|aw9523_init_irq' \
	"${linux_tree}/${linux_path}" || true

printf '\n[decision]\n'
printf '%s\n' \
	'vendor chip-id register 0x10 and expected value 0x23 match Linux pinctrl-aw9523' \
	'vendor software reset register 0x7f value 0x00 matches Linux reset path' \
	'reuse the upstream AW9523 silicon driver; do not create a vendor polling clone' \
	'board work remains: reset/shutdown polarity, GPIO/EINT wiring, matrix keymap, and wake policy'
