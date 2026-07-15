#!/usr/bin/env bash

# Emit a source-level touchscreen contract without copying vendor code into the
# repository. Run this in the development VM; the vendor checkout is evidence
# and remains immutable.

set -euo pipefail
export LC_ALL=C

vendor_tree=${1:-${HOME}/src/reference/planet-mt6797-3.18}
linux_tree=${2:-${HOME}/src/gemini-pda/linux-7.1.3}
vendor_path=drivers/input/touchscreen/mediatek/aeon_nt36xxx
vendor_files=(
	"${vendor_path}/nt36xxx.h"
	"${vendor_path}/nt36xxx.c"
	"${vendor_path}/nt36xxx_fw_update.c"
)
linux_driver=${linux_tree}/drivers/input/touchscreen/novatek-nvt-ts.c
linux_binding=${linux_tree}/Documentation/devicetree/bindings/input/touchscreen/novatek,nvt-ts.yaml

[[ -d "${vendor_tree}/.git" ]] || {
	printf 'vendor tree is not a git checkout: %s\n' "${vendor_tree}" >&2
	exit 1
}
[[ -r "${linux_driver}" && -r "${linux_binding}" ]] || {
	printf 'Linux touchscreen source or binding is missing\n' >&2
	exit 1
}

blob_hash() {
	local path=$1
	git -C "${vendor_tree}" show "HEAD:${path}" | sha256sum | awk '{print $1}'
}

printf 'vendor_tree=%s\n' "${vendor_tree}"
printf 'vendor_commit=%s\n' "$(git -C "${vendor_tree}" rev-parse HEAD)"
printf 'linux_tree=%s\n' "${linux_tree}"
printf 'linux_driver_sha256=%s\n' "$(sha256sum "${linux_driver}" | awk '{print $1}')"
printf 'linux_binding_sha256=%s\n' "$(sha256sum "${linux_binding}" | awk '{print $1}')"

for path in "${vendor_files[@]}"; do
	printf 'vendor_blob_sha256[%s]=%s\n' "${path}" "$(blob_hash "${path}")"
done

printf '\n[vendor transport and maps]\n'
git -C "${vendor_tree}" show "HEAD:${vendor_files[0]}" "HEAD:${vendor_files[1]}" 2>/dev/null |
	grep -nE 'I2C_(BLDR|FW|HW)_Address|EVENT_BUF_ADDR|EVENT_MAP_(FWINFO|PROJECTID|RESET_COMPLETE)|POINT_DATA_LEN' || true

printf '\n[vendor trim table]\n'
git -C "${vendor_tree}" show "HEAD:${vendor_path}/nt36xxx.c" |
	grep -nE '\.id =|\.mask =|NT(36772|36525|36870|36676F)_memory_map' || true

printf '\n[vendor identification path]\n'
git -C "${vendor_tree}" show "HEAD:${vendor_path}/nt36xxx.c" |
	grep -nE 'nvt_ts_check_chip_ver_trim|nvt_bootloader_reset|nvt_sw_reset_idle|0x4E|0x01|0xF6|I2C_HW_Address' | head -n 80 || true

printf '\n[vendor transfer semantics]\n'
git -C "${vendor_tree}" show "HEAD:${vendor_path}/nt36xxx.c" |
	grep -nE 'msgs\[[01]\]\.addr|i2c_(read|write)_bytes_(dma|non_dma)\(client, address|I2C_(HW|BLDR|FW)_Address' |
	head -n 80 || true

printf '\n[Linux 7.1.x match and resources]\n'
grep -nE 'NVT_TS_(PARAMETERS_START|PARAMS_CHIP_ID)|chip_id =|compatible =|regulator|reset_gpio|i2c_transfer|NVT_TS_TOUCH_START' \
	"${linux_driver}" "${linux_binding}" || true

printf '\n[decision]\n'
printf '%s\n' \
	'vendor trim table has no NT36672A entry' \
	'vendor runtime uses an xdata-selected event map and alternate I2C target addresses 0x62/0x01' \
	'vendor CTP_I2C_READ/WRITE assigns the supplied address directly to each i2c_msg; 0x01 is an alternate target address, not a second DT client' \
	'Linux 7.1.x novatek-nvt-ts expects a direct client address and NT11205/NT36672A parameter IDs' \
	'keep the Gemini touch node disabled; design an NT36xxx backend or new driver after a bounded ID/resource test' \
	'mainline_transfer_design=use a bounded helper with a copied i2c_msg address; never register an ordinary 0x01 client or expose firmware update'
