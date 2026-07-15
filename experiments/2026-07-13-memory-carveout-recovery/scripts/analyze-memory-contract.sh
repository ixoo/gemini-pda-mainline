#!/usr/bin/env bash

# Compare vendor reserved-memory declarations with the prepared Linux DT and
# local Gemini patch. No firmware or device memory is read by this script.

set -eu
export LC_ALL=C

vendor_tree=${VENDOR_TREE:-/home/julien.guest/src/reference/planet-mt6797-3.18}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
repo_root=${REPO_ROOT:-/mnt/gemini-pda-mainline}

[[ -d "$vendor_tree" ]] || { printf 'missing vendor tree: %s\n' "$vendor_tree" >&2; exit 1; }
[[ -d "$linux_tree" ]] || { printf 'missing Linux tree: %s\n' "$linux_tree" >&2; exit 1; }

printf 'vendor_tree=%s\n' "$vendor_tree"
printf 'vendor_commit=%s\n' "$(git -C "$vendor_tree" rev-parse HEAD 2>/dev/null || printf unknown)"
printf 'linux_tree=%s\n' "$linux_tree"

printf '\n[vendor reserved-memory declarations]\n'
rg -n -C 2 'reserved-memory|consys-reserve|scp_share|spm-reserve|mblock|atf-reserved|ccci' \
	"$vendor_tree/arch/arm64/boot/dts/mt6797.dtsi" | head -n 320 || true

printf '\n[linux MT6797 memory declarations]\n'
rg -n -C 2 'reserved-memory|memory@|device_type = "memory"' \
	"$linux_tree/arch/arm64/boot/dts/mediatek/mt6797.dtsi" \
	"$linux_tree/arch/arm64/boot/dts/mediatek/mt6797-evb.dts" || true

printf '\n[local Gemini reservation patch]\n'
if [ -r "$repo_root/patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch" ]; then
	rg -n 'memory@|reserved-memory|consys|scp|spm|log-store|ccci' \
		"$repo_root/patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch" || true
else
	echo 'local_patch=not_visible_from_guest'
fi

printf '\n[decision]\n'
printf '%s\n' \
	'live_firmware_reservations_are_more_complete_than_the_generic_linux_mt6797_dts' \
	'local_Gemini_memory_map_must_not_be_replaced_by_contiguous_EVB_memory' \
	'dynamic_consys_scp_share_and_spm_reservations_require_bootloader_ownership_review' \
	'keep_firmware_modem_connectivity_framebuffer_and_SCP_regions_reserved_before_runtime_bringup'
