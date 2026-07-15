#!/usr/bin/env bash

set -euo pipefail

readonly VENDOR_TREE="${VENDOR_TREE:?set VENDOR_TREE to the immutable Planet source tree}"
readonly LINUX_TREE="${LINUX_TREE:?set LINUX_TREE to the pinned Linux source tree}"
readonly PATCH_FILE="${PATCH_FILE:-patches/v7.1.3/0054-arm64-dts-mediatek-add-disabled-Gemini-AW9523-keyboard-candidate.patch}"
readonly VENDOR_PATH="drivers/misc/mediatek/aw9523/aw9523_key.c"
readonly LINUX_PATH="drivers/input/keyboard/matrix_keypad.c"
readonly BINDING_PATH="Documentation/devicetree/bindings/input/gpio-matrix-keypad.yaml"

for command in git rg sha256sum; do
  command -v "${command}" >/dev/null 2>&1 || {
    echo "error: required command not found: ${command}" >&2
    exit 1
  }
done

[[ -f "${PATCH_FILE}" ]] || {
  echo "error: candidate patch not found: ${PATCH_FILE}" >&2
  exit 1
}
[[ -f "${LINUX_TREE}/${LINUX_PATH}" && -f "${LINUX_TREE}/${BINDING_PATH}" ]] || {
  echo "error: Linux tree is missing matrix-keypad source or binding" >&2
  exit 1
}
git -C "${VENDOR_TREE}" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "error: vendor tree is not a Git worktree: ${VENDOR_TREE}" >&2
  exit 1
}

vendor_source="$(mktemp)"
trap 'rm -f "${vendor_source}"' EXIT
git -C "${VENDOR_TREE}" show "HEAD:${VENDOR_PATH}" > "${vendor_source}"

has_vendor() {
  rg -q -- "$1" "${vendor_source}"
}

has_candidate() {
  rg -q -- "$1" "${PATCH_FILE}"
}

has_linux() {
  rg -q -- "$1" "${LINUX_TREE}/${LINUX_PATH}"
}

has_binding() {
  rg -q -- "$1" "${LINUX_TREE}/${BINDING_PATH}"
}

has_vendor 'i2c_write_reg\(P0_CONFIG, 0xFF\)' || {
  echo "error: vendor P0 input initialization changed" >&2
  exit 1
}
has_vendor 'i2c_write_reg\(P1_CONFIG, 0x00\)' || {
  echo "error: vendor P1 output initialization changed" >&2
  exit 1
}
has_vendor 'P1_KCOL_MASK \| val.*~\(1<<i\)' || {
  echo "error: vendor active-column scan expression changed" >&2
  exit 1
}
has_vendor 'if \(keyst_new\[i\] & \(1<<j\)\)' || {
  echo "error: vendor row state polarity anchor changed" >&2
  exit 1
}
has_linux 'device_property_read_bool\(&pdev->dev, "drive-inactive-cols"\)' || {
  echo "error: Linux matrix driver no longer exposes inactive-column policy" >&2
  exit 1
}
has_linux 'device_property_read_bool\(&pdev->dev, "gpio-activelow"\)' || {
  echo "error: Linux matrix driver no longer exposes active-low policy" >&2
  exit 1
}
has_binding 'gpio-activelow:' || {
  echo "error: matrix binding no longer documents gpio-activelow" >&2
  exit 1
}
has_binding 'drive-inactive-cols:' || {
  echo "error: matrix binding no longer documents drive-inactive-cols" >&2
  exit 1
}

printf 'validation=keyboard-polarity-contract\n'
printf 'vendor_revision=%s\n' "$(git -C "${VENDOR_TREE}" rev-parse HEAD)"
printf 'vendor_aw9523_source_sha256=%s\n' "$(sha256sum "${vendor_source}" | awk '{print $1}')"
printf 'linux_matrix_source_sha256=%s\n' "$(sha256sum "${LINUX_TREE}/${LINUX_PATH}" | awk '{print $1}')"
printf 'linux_matrix_binding_sha256=%s\n' "$(sha256sum "${LINUX_TREE}/${BINDING_PATH}" | awk '{print $1}')"
printf 'candidate_patch=%s\n' "${PATCH_FILE}"
printf 'vendor_p0_mode=input\n'
printf 'vendor_p1_mode=output\n'
printf 'vendor_active_column=physical_low\n'
printf 'vendor_inactive_columns=physical_high\n'
printf 'vendor_pressed_row_state=physical_low\n'
printf 'vendor_released_row_state=physical_high\n'
printf 'generic_active_low_property=gpio-activelow\n'
printf 'generic_inactive_column_property=drive-inactive-cols\n'
printf 'candidate_has_gpio_activelow=%s\n' "$(has_candidate 'gpio-activelow' && echo yes || echo no)"
printf 'candidate_has_drive_inactive_cols=%s\n' "$(has_candidate 'drive-inactive-cols' && echo yes || echo no)"
printf 'candidate_gpio_flags=GPIO_ACTIVE_HIGH\n'
printf 'vendor_scan_rate_hz=100\n'
printf 'vendor_irq_debounce_delay_ms=1\n'
printf 'vendor_irq_trigger_request=IRQ_TYPE_NONE\n'
printf 'candidate_parent_irq=IRQ_TYPE_LEVEL_LOW\n'

printf '\n[decision]\n'
printf '%s\n' \
  'The vendor scan is active-low on columns and rows: the selected P1 column is driven low, inactive columns high, and a low P0 row bit is reported as a key press.' \
  'The generic Linux matrix driver can represent that electrical contract with gpio-activelow and drive-inactive-cols.' \
  'The current disabled Gemini candidate omits both properties and therefore remains a topology/keymap candidate, not an electrically equivalent scan description.' \
  'Do not enable the candidate until the polarity correction and parent EINT/reset behavior are validated on hardware.' \
  'hardware_write=none'
