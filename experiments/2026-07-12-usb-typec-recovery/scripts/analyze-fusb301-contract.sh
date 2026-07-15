#!/usr/bin/env bash

# Emit a source-level FUSB301 contract without copying the vendor
# implementation into the repository. Run this in the development VM; the
# vendor checkout remains immutable evidence.

set -euo pipefail
export LC_ALL=C

vendor_tree=${1:-${HOME}/src/reference/planet-mt6797-3.18}
linux_tree=${2:-${HOME}/src/gemini-pda/linux-7.1.3}
vendor_dir=drivers/misc/mediatek/usb_c/fusb301
vendor_files=("${vendor_dir}/fusb301.h" "${vendor_dir}/usb_typec.c")
linux_typec_dir=${linux_tree}/drivers/usb/typec

[[ -d "${vendor_tree}/.git" ]] || {
	printf 'vendor tree is not a git checkout: %s\n' "${vendor_tree}" >&2
	exit 1
}
[[ -d "${linux_typec_dir}" ]] || {
	printf 'Linux Type-C tree is missing: %s\n' "${linux_typec_dir}" >&2
	exit 1
}

blob_hash() {
	local path=$1
	git -C "${vendor_tree}" show "HEAD:${path}" | sha256sum | awk '{print $1}'
}

printf 'vendor_tree=%s\n' "${vendor_tree}"
printf 'vendor_commit=%s\n' "$(git -C "${vendor_tree}" rev-parse HEAD)"
for path in "${vendor_files[@]}"; do
	printf 'vendor_blob_sha256[%s]=%s\n' "${path}" "$(blob_hash "${path}")"
done
printf 'linux_tree=%s\n' "${linux_tree}"
linux_matches="$(find "${linux_typec_dir}" -type f -print | grep -i 'fusb301' || true)"
[[ -n "${linux_matches}" ]] || linux_matches=none
printf 'linux_fusb301_matches=%s\n' "${linux_matches}"

printf '\n[vendor register map]\n'
git -C "${vendor_tree}" show "HEAD:${vendor_files[0]}" |
	grep -nE '#define[[:space:]]+reg(DeviceID|Mode|Control|Manual|Reset|Mask|Status|Type|Interrupt)|unsigned (ATTACH|VBUSOK|ORIENT|BC_LVL)' || true

printf '\n[vendor initialization and IRQ path]\n'
git -C "${vendor_tree}" show "HEAD:${vendor_files[1]}" |
	grep -nE 'InitializeFUSB301|regDeviceID|regMode|0x01|fusb301_eint_work|fusb301_eint_isr|fusb301_eint_init|request_irq|schedule_delayed_work|register_typec0_switch_callback|of_match|compatible' | head -n 160 || true

printf '\n[Linux framework anchors]\n'
rg -n 'typec_register_port|typec_register_partner|typec_set_orientation|usb_role_switch|tcpm_register_port|tcpci_register_port' \
	"${linux_typec_dir}" | head -n 100 || true

printf '\n[decision]\n'
printf '%s\n' \
	'Linux 7.1.x has no FUSB301 driver or binding' \
	'vendor probe reads device ID and writes mode 0x01, but its interrupt work is empty and callback registration is a no-op' \
	'write a generic FUSB301 Type-C driver only after validating register semantics and IRQ behavior' \
	'keep Gemini redriver/VBUS GPIO policy in separate board glue; do not copy vendor private callbacks'
