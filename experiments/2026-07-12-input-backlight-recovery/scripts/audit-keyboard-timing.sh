#!/usr/bin/env bash

# Compare the retained AW9523 keyboard timing policy with Linux's generic
# GPIO matrix-keypad consumer.  This is source/DT evidence only; it never
# probes the device or changes the candidate DT.

set -euo pipefail
export LC_ALL=C

readonly VENDOR_TREE="${VENDOR_TREE:-${HOME}/src/reference/planet-mt6797-3.18}"
readonly LINUX_TREE="${LINUX_TREE:-${HOME}/src/gemini-pda/linux-7.1.3}"
readonly CANDIDATE_DTS="${CANDIDATE_DTS:-${LINUX_TREE}/arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts}"
readonly VENDOR_SOURCE_PATH="drivers/misc/mediatek/aw9523/aw9523_key.c"
readonly VENDOR_DT_PATH="arch/arm64/boot/dts/mt6797.dtsi"
readonly LINUX_MATRIX_PATH="drivers/input/keyboard/matrix_keypad.c"
readonly LINUX_MATRIX_BINDING="Documentation/devicetree/bindings/input/gpio-matrix-keypad.yaml"
readonly LINUX_AW9523_PATH="drivers/pinctrl/pinctrl-aw9523.c"

for command in git rg sha256sum awk grep mktemp; do
	command -v "${command}" >/dev/null 2>&1 || {
		printf 'error: required command not found: %s\n' "${command}" >&2
		exit 1
	}
done

git -C "${VENDOR_TREE}" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
	printf 'error: vendor tree is not a Git worktree: %s\n' "${VENDOR_TREE}" >&2
	exit 1
}

for path in "${LINUX_TREE}/${LINUX_MATRIX_PATH}" \
	"${LINUX_TREE}/${LINUX_MATRIX_BINDING}" \
	"${LINUX_TREE}/${LINUX_AW9523_PATH}" "${CANDIDATE_DTS}"; do
	[[ -r "${path}" ]] || {
		printf 'error: required Linux evidence file is missing: %s\n' "${path}" >&2
		exit 1
	}
done

vendor_source="$(mktemp)"
vendor_dt="$(mktemp)"
trap 'rm -f "${vendor_source}" "${vendor_dt}"' EXIT
git -C "${VENDOR_TREE}" show "HEAD:${VENDOR_SOURCE_PATH}" > "${vendor_source}"
git -C "${VENDOR_TREE}" show "HEAD:${VENDOR_DT_PATH}" > "${vendor_dt}"

has_vendor() {
	rg -q -- "$1" "${vendor_source}"
}

has_linux_matrix() {
	rg -q -- "$1" "${LINUX_TREE}/${LINUX_MATRIX_PATH}"
}

has_linux_binding() {
	rg -q -- "$1" "${LINUX_TREE}/${LINUX_MATRIX_BINDING}"
}

has_candidate() {
	rg -q -- "$1" "${CANDIDATE_DTS}"
}

require_vendor() {
	has_vendor "$1" || {
		printf 'error: vendor timing anchor changed: %s\n' "$1" >&2
		exit 1
	}
}

require_linux_matrix() {
	has_linux_matrix "$1" || {
		printf 'error: Linux matrix timing anchor changed: %s\n' "$1" >&2
		exit 1
	}
}

require_linux_binding() {
	has_linux_binding "$1" || {
		printf 'error: Linux matrix binding anchor changed: %s\n' "$1" >&2
		exit 1
	}
}

require_vendor '#define HRTIMER_FRAME[[:space:]]+100'
require_vendor 'schedule_delayed_work\(&aw9523_key->work, msecs_to_jiffies\(1\)\)'
require_vendor '1000/\(HRTIMER_FRAME\*10\)'
require_vendor '1000/HRTIMER_FRAME'
require_vendor 'forceCycles = 100'
require_vendor 'skipCycles = 50'
require_vendor 'pinctrl_select_state\(aw9523_pin, shdn_low\)'
require_vendor 'pinctrl_select_state\(aw9523_pin, shdn_high\)'
require_vendor 'of_property_read_u32_array\(aw9523_key->irq_node, "debounce", ints, ARRAY_SIZE\(ints\)\)'
require_vendor 'gpio_set_debounce\(ints\[0\], ints\[1\]\)'

require_linux_matrix 'device_property_read_u32\(&pdev->dev, "debounce-delay-ms"'
require_linux_matrix 'device_property_read_u32\(&pdev->dev, "col-scan-delay-us"'
require_linux_matrix 'device_property_read_u32\(&pdev->dev, "all-cols-on-delay-us"'
require_linux_matrix 'schedule_delayed_work\(&keypad->work,'
require_linux_matrix 'msecs_to_jiffies\(keypad->debounce_ms\)'
require_linux_matrix 'if \(on && keypad->col_scan_delay_us\)'
require_linux_matrix 'if \(on && keypad->all_cols_on_delay_us\)'
require_linux_binding 'debounce-delay-ms:'
require_linux_binding 'col-scan-delay-us:'
require_linux_binding 'all-cols-on-delay-us:'

# The retained vendor DT node is a pseudo-node consumed by
# of_find_compatible_node().  Extract its small block so an unrelated
# debounce tuple elsewhere in the vendor tree cannot be mistaken for the
# AW9523 interrupt setting.
vendor_aw_node="$(awk '
  /compatible[[:space:]]*=[[:space:]]*"mediatek,aw9523-eint"/ { in_node = 1 }
  in_node { print }
  in_node && /};/ { exit }
' "${vendor_dt}")"
[[ -n "${vendor_aw_node}" ]] || {
	printf 'error: retained vendor AW9523 EINT node is missing\n' >&2
	exit 1
}

if printf '%s\n' "${vendor_aw_node}" | rg -q 'debounce'; then
	vendor_dt_debounce_property=present
else
	vendor_dt_debounce_property=absent
fi

printf 'validation=keyboard-timing-contract\n'
printf 'vendor_tree=%s\n' "${VENDOR_TREE}"
printf 'vendor_commit=%s\n' "$(git -C "${VENDOR_TREE}" rev-parse HEAD)"
printf 'vendor_source_sha256=%s\n' "$(sha256sum "${vendor_source}" | awk '{print $1}')"
printf 'vendor_dt_sha256=%s\n' "$(sha256sum "${vendor_dt}" | awk '{print $1}')"
printf 'linux_tree=%s\n' "${LINUX_TREE}"
printf 'linux_revision=%s\n' "$(sed -n 's/^VERSION = //p; s/^PATCHLEVEL = /./p; s/^SUBLEVEL = /./p' "${LINUX_TREE}/Makefile" | tr -d '\n')"
printf 'linux_matrix_source_sha256=%s\n' "$(sha256sum "${LINUX_TREE}/${LINUX_MATRIX_PATH}" | awk '{print $1}')"
printf 'linux_matrix_binding_sha256=%s\n' "$(sha256sum "${LINUX_TREE}/${LINUX_MATRIX_BINDING}" | awk '{print $1}')"
printf 'linux_aw9523_source_sha256=%s\n' "$(sha256sum "${LINUX_TREE}/${LINUX_AW9523_PATH}" | awk '{print $1}')"
printf 'candidate_dts=%s\n' "${CANDIDATE_DTS}"
printf 'candidate_dts_sha256=%s\n' "$(sha256sum "${CANDIDATE_DTS}" | awk '{print $1}')"

printf '\n[vendor timing contract]\n'
printf 'vendor_timer_frame_hz=100\n'
printf 'vendor_irq_delayed_work_ms=1\n'
printf 'vendor_first_scan_delay_ms=1\n'
printf 'vendor_steady_rescan_ms=10\n'
printf 'vendor_force_rescan_cycles=100\n'
printf 'vendor_force_rescan_window_ms=1000\n'
printf 'vendor_ghost_suppression_skip_cycles=50\n'
printf 'vendor_ghost_suppression_window_ms=500\n'
printf 'vendor_reset_low_ms=5\n'
printf 'vendor_reset_high_ms=5\n'
printf 'vendor_chip_id_retry_delay_ms=10\n'
printf 'vendor_eint_debounce_property=aw9523_eint_debounce_tuple\n'
printf 'vendor_dt_debounce_property=%s\n' "${vendor_dt_debounce_property}"
printf 'vendor_dt_debounce_fallback=source_initializes_tuple_to_0_0_and_ignores_read_error\n'

printf '\n[Linux 7.1.3 consumer timing contract]\n'
printf 'mainline_scan_model=row_irq_to_delayed_work_then_full_matrix_scan\n'
printf 'mainline_debounce_property=debounce-delay-ms_optional\n'
printf 'mainline_debounce_default_ms=0\n'
printf 'mainline_col_scan_delay_property=col-scan-delay-us_optional\n'
printf 'mainline_col_scan_delay_default_us=0\n'
printf 'mainline_all_cols_on_delay_property=all-cols-on-delay-us_optional\n'
printf 'mainline_all_cols_on_delay_default_us=0\n'
printf 'mainline_periodic_rescan=none\n'
printf 'mainline_candidate_gpio_activelow=%s\n' "$(has_candidate 'gpio-activelow' && echo present || echo absent)"
printf 'mainline_candidate_drive_inactive_cols=%s\n' "$(has_candidate 'drive-inactive-cols' && echo present || echo absent)"
printf 'mainline_candidate_timing_properties=%s\n' "$(has_candidate 'debounce-delay-ms|col-scan-delay-us|all-cols-on-delay-us' && echo present || echo absent)"
printf 'mainline_aw9523_hard_reset_pulse_us=50\n'
printf 'mainline_aw9523_reset_recovery_us=20\n'
printf 'mainline_aw9523_nested_irq_default=EDGE_BOTH\n'

printf '\n[decision]\n'
printf '%s\n' \
	'The vendor timing values are policy, not a direct equivalent of matrix-keypad debounce or scan-delay properties.' \
	'The retained vendor DT supplies no debounce property inside the AW9523 EINT pseudo-node; the source nevertheless passes an initialized 0,0 tuple to gpio_set_debounce after ignoring the read error.' \
	'Linux matrix-keypad currently has zero debounce/settling delays and no periodic rescan because the candidate omits all three optional timing properties.' \
	'Do not add debounce-delay-ms, col-scan-delay-us, or all-cols-on-delay-us until an owner-assisted mainline event trace measures bounce, settling, and key-release behavior.' \
	'The Linux AW9523 reset path is materially shorter than the vendor GPIO reset sequence and must be validated with GPIO58 state and chip-ID readback.' \
	'consumer_timing_decision=keep_disabled_pending_runtime_trace' \
	'hardware_write=none'
