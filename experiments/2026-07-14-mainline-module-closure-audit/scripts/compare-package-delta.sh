#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only comparison of two packaged Gemini kernels.  This is used to prove
# that a focused patch revision did not silently invalidate unrelated package
# evidence.

set -euo pipefail
export LC_ALL=C

old=${OLD_PACKAGE:?set OLD_PACKAGE to the earlier packaged kernel}
new=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to the package being checked}

for package in "$old" "$new"; do
	for file in Image Image.gz System.map kernel.config \
		dtbs/mediatek/mt6797-gemini-pda.dtb; do
		[[ -r "$package/$file" ]] || {
			printf 'missing_input=%s/%s\n' "$package" "$file" >&2
			exit 1
		}
	done
	done

module_hashes() {
	local package=$1 path
	while IFS= read -r path; do
		printf '%s  %s\n' "$(sha256sum "$package/modules/$path" | awk '{print $1}')" "$path"
	done < <(cd "$package/modules" && find . -type f -name '*.ko' -print | sort)
}

printf 'validation=gemini-package-delta\n'
printf 'old_package=%s\n' "$old"
printf 'new_package=%s\n' "$new"
printf 'old_patchset_token=%s\n' "$(basename "$old" | sed 's/^linux-7.1.3-gemini-//')"
printf 'new_patchset_token=%s\n' "$(basename "$new" | sed 's/^linux-7.1.3-gemini-//')"

for file in Image Image.gz System.map kernel.config \
	dtbs/mediatek/mt6797-gemini-pda.dtb; do
	old_hash=$(sha256sum "$old/$file" | awk '{print $1}')
	new_hash=$(sha256sum "$new/$file" | awk '{print $1}')
	printf 'file=%s\nold_sha256=%s\nnew_sha256=%s\nsame=%s\n' \
		"$file" "$old_hash" "$new_hash" "$([[ "$old_hash" == "$new_hash" ]] && printf true || printf false)"
done

old_module_count=$(find "$old/modules" -type f -name '*.ko' | wc -l | tr -d ' ')
new_module_count=$(find "$new/modules" -type f -name '*.ko' | wc -l | tr -d ' ')
printf 'old_module_count=%s\nnew_module_count=%s\n' "$old_module_count" "$new_module_count"

module_diff_count=$(
	{
		diff -u <(module_hashes "$old") <(module_hashes "$new") || true
	} | awk '/^[+-][0-9a-f]/ { count++ } END { print count + 0 }'
)
printf 'module_hash_diff_lines=%s\n' "$module_diff_count"

panel=drivers/gpu/drm/panel/panel-novatek-nt36672e.ko
printf 'panel_module=%s\npanel_old_sha256=%s\npanel_new_sha256=%s\n' \
	"$panel" \
	"$(sha256sum "$old/modules/lib/modules/7.1.3-gemini/kernel/$panel" | awk '{print $1}')" \
	"$(sha256sum "$new/modules/lib/modules/7.1.3-gemini/kernel/$panel" | awk '{print $1}')"

printf 'unrelated_module_changes=%s\n' "$([[ "$module_diff_count" == 2 ]] && printf none || printf investigate)"
printf 'runtime_mainline_boot=not_attempted\n'
printf 'hardware_write=none\n'
