#!/usr/bin/env bash

set -euo pipefail

# Source-only hall/lid contract audit. It reads Git blobs and the prepared
# Linux tree; it never executes vendor code or touches the device.

VENDOR_TREE=${VENDOR_TREE:-"$HOME/src/reference/planet-mt6797-3.18"}
VENDOR_COMMIT=${VENDOR_COMMIT:-c5b0be85017ad0c599725e8273842efdbecdd88a}
LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}

command -v git >/dev/null 2>&1 || { echo "git is required" >&2; exit 1; }
command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required" >&2; exit 1; }

readonly -a VENDOR_FILES=(
	"drivers/input/hall/hall.c"
	"drivers/input/switch/switch.c"
	"arch/arm64/boot/dts/mt6797.dtsi"
	"arch/arm64/boot/dts/aeon6797_6m_n.dts"
)
readonly -a LINUX_FILES=(
	"drivers/input/keyboard/gpio_keys.c"
	"Documentation/devicetree/bindings/input/gpio-keys.yaml"
	"include/uapi/linux/input-event-codes.h"
)

vendor_blob_sha() {
	local path="$1"
	git -C "$VENDOR_TREE" show "$VENDOR_COMMIT:$path" | sha256sum | awk '{print $1}'
}

vendor_anchors() {
	local path="$1"
	git -C "$VENDOR_TREE" show "$VENDOR_COMMIT:$path" |
		grep -E 'compatible|SW_LID|KEY_F9|KEY_F10|gpio_get_value|gpio_set_debounce|IRQ_TYPE_LEVEL|request_irq|switch_set_state|input_report_(switch|key)|wakeup|pinctrl|debounce|interrupts' |
		head -80 || true
}

linux_sha() {
	sha256sum "$LINUX_TREE/$1" | awk '{print $1}'
}

linux_anchors() {
	local path="$1"
	grep -E 'linux,input-type|SW_LID|debounce-interval|wakeup-source|gpio-keys|input_report_switch|gpiod_get|request_irq' "$LINUX_TREE/$path" |
		head -80 || true
}

printf 'audit=mt6797-hall-lid-switch-contract\n'
printf 'execution=none\n'
printf 'vendor_tree=%s\n' "$VENDOR_TREE"
printf 'vendor_commit=%s\n' "$VENDOR_COMMIT"
printf 'linux_tree=%s\n' "$LINUX_TREE"
printf '\n[vendor_sources]\n'
for path in "${VENDOR_FILES[@]}"; do
	printf 'path=%s\nsha256=%s\n' "$path" "$(vendor_blob_sha "$path")"
	printf 'anchors=%s\n' "$(vendor_anchors "$path" | tr '\n' ';')"
done
printf '\n[linux_sources]\n'
for path in "${LINUX_FILES[@]}"; do
	printf 'path=%s\nsha256=%s\n' "$path" "$(linux_sha "$path")"
	printf 'anchors=%s\n' "$(linux_anchors "$path" | tr '\n' ';')"
done

cat <<'EOF'

[decision]
hall=standard_input_switch_candidate: gpio-keys EV_SW SW_LID can replace the vendor hall input path once GPIO polarity, debounce, and wake policy are verified
toggle=not_a_switch_class_abi: vendor switch driver emits KEY_F9/KEY_F10 pulses and Android switch state; semantic mapping remains hardware/user-policy work
driver_boundary=reuse_gpio_keys_and_standard_input_core; no vendor hall/switch driver or Android switch class should be copied
safety=do_not_stimulate_inputs_or_enable_wakeup_during_static_audit
EOF
