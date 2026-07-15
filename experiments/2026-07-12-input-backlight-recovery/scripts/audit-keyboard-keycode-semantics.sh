#!/usr/bin/env bash
set -euo pipefail

# Verify the Linux 7.1.x behavior of omitted and explicit matrix keycodes.
# This is a source audit only; it does not read or write a device.

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
vendor_tree=${VENDOR_TREE:-/home/julien.guest/src/reference/planet-mt6797-3.18}
patch_file=${PATCH_FILE:-$repo_root/patches/v7.1.3/0054-arm64-dts-mediatek-add-disabled-Gemini-AW9523-keyboard-candidate.patch}
keymap_file=${KEYMAP_FILE:-$repo_root/experiments/2026-07-12-input-backlight-recovery/results/keyboard-keymap.txt}

matrix_keymap_source=$linux_tree/drivers/input/matrix-keymap.c
matrix_keypad_source=$linux_tree/drivers/input/keyboard/matrix_keypad.c
input_source=$linux_tree/drivers/input/input.c
input_codes_header=$linux_tree/include/uapi/linux/input-event-codes.h
vendor_key_source=drivers/misc/mediatek/aw9523/aw9523_key.c

for required in "$matrix_keymap_source" "$matrix_keypad_source" \
    "$input_source" "$input_codes_header" "$patch_file" "$keymap_file"; do
	if [[ ! -f $required ]]; then
		echo "missing required input: $required" >&2
		exit 1
	fi
done

line_of() {
	local file=$1
	local needle=$2
	awk -v needle="$needle" 'index($0, needle) { print NR; exit }' "$file"
}

require_anchor() {
	local label=$1
	local file=$2
	local needle=$3
	local line
	line=$(line_of "$file" "$needle")
	if [[ -z $line ]]; then
		echo "missing source anchor: $label: $needle" >&2
		exit 1
	fi
	printf '%s=%s:%s\n' "$label" "${file#"$linux_tree"/}" "$line"
}

matrix_positions=$(awk '$1 ~ /^[0-9]+$/ { count++ } END { print count + 0 }' "$keymap_file")
unknown_positions=$(awk '$3 == "KEY_UNKNOWN" { count++ } END { print count + 0 }' "$keymap_file")
assigned_positions=$((matrix_positions - unknown_positions))
candidate_positions=$(awk '/MATRIX_KEY\(/ { count++ } END { print count + 0 }' "$patch_file")
unknown_coordinates=$(awk '$3 == "KEY_UNKNOWN" { printf "(%s,%s) ", $1, $2 }' "$keymap_file" | sed 's/ *$//')

if [[ $candidate_positions -ne $assigned_positions ]]; then
	echo "candidate/keymap position count mismatch: candidate=$candidate_positions assigned=$assigned_positions" >&2
	exit 1
fi

if ! git -C "$vendor_tree" cat-file -e "HEAD:$vendor_key_source"; then
	echo "vendor source object is unavailable: $vendor_key_source" >&2
	exit 1
fi

if git -C "$linux_tree" rev-parse --verify HEAD >/dev/null 2>&1; then
	linux_revision=$(git -C "$linux_tree" rev-parse HEAD)
else
	linux_revision=${LINUX_REVISION:-managed-source-tree}
fi
vendor_revision=$(git -C "$vendor_tree" rev-parse HEAD)
vendor_blob_sha1=$(git -C "$vendor_tree" rev-parse "HEAD:$vendor_key_source")
linux_matrix_keymap_sha256=$(sha256sum "$matrix_keymap_source" | awk '{ print $1 }')
linux_matrix_keypad_sha256=$(sha256sum "$matrix_keypad_source" | awk '{ print $1 }')
linux_input_sha256=$(sha256sum "$input_source" | awk '{ print $1 }')
linux_header_sha256=$(sha256sum "$input_codes_header" | awk '{ print $1 }')

key_reserved=$(awk '/^[[:space:]]*#define[[:space:]]+KEY_RESERVED[[:space:]]/ { print $3; exit }' "$input_codes_header")
key_unknown=$(awk '/^[[:space:]]*#define[[:space:]]+KEY_UNKNOWN[[:space:]]/ { print $3; exit }' "$input_codes_header")
if [[ $key_reserved != 0 || $key_unknown != 240 ]]; then
	echo "unexpected keycode definitions: KEY_RESERVED=$key_reserved KEY_UNKNOWN=$key_unknown" >&2
	exit 1
fi

generated_utc=${GENERATED_UTC:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}
cat <<EOF
validation=gemini-keyboard-keycode-semantics
generated_utc=$generated_utc
linux_revision=$linux_revision
vendor_revision=$vendor_revision
vendor_key_source=$vendor_key_source
vendor_key_source_blob_sha1=$vendor_blob_sha1
linux_matrix_keymap_sha256=$linux_matrix_keymap_sha256
linux_matrix_keypad_sha256=$linux_matrix_keypad_sha256
linux_input_sha256=$linux_input_sha256
linux_input_codes_header_sha256=$linux_header_sha256
key_reserved=$key_reserved
key_unknown=$key_unknown
matrix_positions=$matrix_positions
assigned_positions=$assigned_positions
unknown_positions=$unknown_positions
unknown_coordinates=$unknown_coordinates
candidate_positions=$candidate_positions
keymap_file_sha256=$(sha256sum "$keymap_file" | awk '{ print $1 }')
candidate_patch_sha256=$(sha256sum "$patch_file" | awk '{ print $1 }')
EOF

require_anchor matrix_map_zero_initialization "$matrix_keymap_source" "keymap = devm_kcalloc"
require_anchor matrix_map_explicit_assignment "$matrix_keymap_source" "keymap[MATRIX_SCAN_CODE"
require_anchor matrix_map_advertises_code "$matrix_keymap_source" "__set_bit(code, input_dev->keybit)"
require_anchor matrix_map_clears_reserved "$matrix_keymap_source" "__clear_bit(KEY_RESERVED, input_dev->keybit)"
require_anchor matrix_scan_emits_scan_code "$matrix_keypad_source" "input_event(input_dev, EV_MSC, MSC_SCAN, code);"
require_anchor matrix_scan_looks_up_keycode "$matrix_keypad_source" "keycodes[code]"
require_anchor matrix_scan_reports_key "$matrix_keypad_source" "input_report_key(input_dev,"
require_anchor matrix_scan_advertises_msc "$matrix_keypad_source" "input_set_capability(input_dev, EV_MSC, MSC_SCAN)"
require_anchor input_key_requires_capability "$input_source" "if (is_event_supported(code, dev->keybit, KEY_MAX))"
require_anchor input_reserved_not_transmitted "$input_source" "KEY_RESERVED is not supposed to be transmitted to userspace."

cat <<'EOF'
semantic_conclusion=omitted_matrix_entries_are_zero_initialized_KEY_RESERVED_and_the_input_core_drops_their_EV_KEY_events
semantic_conclusion_explicit_KEY_UNKNOWN_is_a_real_supported_EV_KEY_code_240
semantic_conclusion_all_changed_coordinates_still_emit_MSC_SCAN_scan_codes
candidate_policy=omit_the_four_vendor_KEY_UNKNOWN_positions_until_hardware_proves_they_are_populated
hardware_write=none
EOF
