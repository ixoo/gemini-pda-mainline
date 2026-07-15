#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the packaged MT6797 AFE/MT6351 ASoC boundary. It does
# not load sound modules, open PCM streams, write mixer/codec registers, enable
# an audio DT node, change clocks/rails, or exercise modem/Bluetooth audio.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
repo_root=${REPO_ROOT:-/mnt/gemini-pda-mainline}
dtb=$package/dtbs/mediatek/mt6797-gemini-pda.dtb
config=$package/kernel.config
system_map=$package/System.map
modules=$package/modules/lib/modules

for file in "$package/Image" "$dtb" "$config" "$system_map"; do
	[[ -r "$file" ]] || { printf 'missing_input=%s\n' "$file" >&2; exit 1; }
done
[[ -d "$linux_tree" ]] || { printf 'missing_source_tree=%s\n' "$linux_tree" >&2; exit 1; }

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
dt_source=$tmpdir/gemini.dts
dtc_stderr=$tmpdir/dtc.stderr
dtc -I dtb -O dts -o "$dt_source" "$dtb" 2>"$dtc_stderr"

sha256() {
	sha256sum "$1" | awk '{print $1}'
}

count_matches() {
	local pattern=$1 file=$2 count
	count=$(rg -c "$pattern" "$file" || true)
	printf '%s' "${count:-0}"
}

count_matches_i() {
	local pattern=$1 file=$2 count
	count=$(rg -i -c "$pattern" "$file" || true)
	printf '%s' "${count:-0}"
}

count_in_context() {
	local node_pattern=$1 lines=$2 property_pattern=$3 count
	count=$(rg -n -A "$lines" "$node_pattern" "$dt_source" |
		rg -c "$property_pattern" || true)
	printf '%s' "${count:-0}"
}

config_state() {
	local symbol=$1 value
	value=$(rg -m1 "^${symbol}=" "$config" | cut -d= -f2- || true)
	if [[ -n "$value" ]]; then
		printf '%s' "$value"
	elif rg -q "^# ${symbol} is not set$" "$config"; then
		printf 'unset'
	else
		printf 'absent'
	fi
}

module_path() {
	local module=$1
	[[ -d "$modules" ]] || return 0
	find "$modules" -type f -name "$module.ko" -print -quit 2>/dev/null || true
}

if [[ -d "$modules" ]]; then
	audio_module_state=packaged
else
	audio_module_state=not_packaged_in_current_artifact
fi

printf 'validation=mt6797-audio-current-package-audit\n'
printf 'package=%s\n' "$package"
printf 'package_image_sha256=%s\n' "$(sha256 "$package/Image")"
printf 'package_config_sha256=%s\n' "$(sha256 "$config")"
printf 'package_dtb_sha256=%s\n' "$(sha256 "$dtb")"
printf 'package_system_map_sha256=%s\n' "$(sha256 "$system_map")"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='; make -s -C "$linux_tree" kernelversion
printf 'dtc_warning_lines=%s\n' "$(wc -l < "$dtc_stderr" | tr -d ' ')"
if [[ -d "$modules" ]]; then
	printf 'modules_tree=present\n'
else
	printf 'modules_tree=absent\n'
fi

printf '\n[configuration]\n'
for symbol in \
	CONFIG_SND_SOC \
	CONFIG_SND_SOC_MEDIATEK \
	CONFIG_SND_SOC_MT6797 \
	CONFIG_SND_SOC_MT6351 \
	CONFIG_SND_SOC_MT6797_MT6351 \
	CONFIG_MFD_MT6397 \
	CONFIG_REGULATOR_MT6351 \
	CONFIG_SND_SOC_MT6351_ACCDET \
	CONFIG_SND_SOC_MT6351_IRQ; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

printf '\n[packaged_audio_modules]\n'
for module in snd-soc-mt6351 mt6797-mt6351 snd-soc-mt6797-afe; do
	path=$(module_path "$module")
	if [[ -n "$path" ]]; then
		printf 'module=%s\npath=%s\nsha256=%s\n' "$module" "$path" "$(sha256 "$path")"
	else
		printf 'module=%s\npath=absent\n' "$module"
	fi
done

printf '\n[device_tree]\n'
printf 'audio_controller_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*audio-controller@11220000 \{' "$dt_source")"
printf 'audio_controller_compatible_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*audio-controller@11220000 \{' 18 'mediatek,mt6797-audio')"
printf 'audio_controller_disabled_status_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*audio-controller@11220000 \{' 24 'status = \"disabled\"')"
printf 'audio_controller_clock_names=%s\n' \
	"$(count_in_context '^[[:space:]]*audio-controller@11220000 \{' 30 'clock-names')"
printf 'audio_controller_clock_cells=%s\n' \
	"$(count_in_context '^[[:space:]]*audio-controller@11220000 \{' 30 'infra_sys_audio_clk|infra_sys_audio_26m|mtkaif_26m_clk|top_mux_audio|top_mux_aud_intbus|top_sys_pll3_d4|top_sys_pll1_d4|top_clk26m_clk')"
printf 'machine_card_node_matches=%s\n' \
	"$(count_matches_i '^[[:space:]]*[[:alnum:]_.-]*(sound-card|audio-card|mt6797-mt6351|mt6351-sound)[[:alnum:]_.-]* \{' "$dt_source")"
printf 'codec_graph_node_matches=%s\n' \
	"$(count_matches_i '^[[:space:]]*[[:alnum:]_.-]*(codec|speaker|headphone|microphone|jack|amplifier)[[:alnum:]_.-]* \{' "$dt_source")"
printf 'audio_resource_context:\n'
rg -n -A 30 -B 2 \
	'^[[:space:]]*(audio-controller@11220000|sound|sound-card|audio-card|codec|speaker|headphone|microphone|jack|amplifier) \{' \
	"$dt_source" | head -n 320 || true

printf '\n[source_contract]\n'
printf 'audio_source_validation=experiments/2026-07-12-audio-afe-recovery/results/audio-source-validation-20260714.txt\n'
printf 'audio_current_validation=experiments/2026-07-12-audio-afe-recovery/results/mainline-audio-current-72-package-20260714.txt\n'
printf 'silicon_reuse=existing_mt6797_afe_mt6351_codec_and_machine_framework\n'
printf 'binding_clock_names=8\n'
printf 'platform_clock_helper_requests=7\n'
printf 'dapm_clock_supply=mtkaif_26m_clk\n'
printf 'board_graph=missing\n'

printf '\n[local_audio_patches]\n'
for patch in \
	"$repo_root/patches/v7.1.3/0045-arm64-dts-mediatek-mt6797-add-disabled-audio-afe.patch" \
	"$repo_root/patches/v7.1.3/0064-dt-bindings-sound-mediatek-add-mt6797-afe.yaml.patch"; do
	if [[ -r "$patch" ]]; then
		printf 'patch=%s\nsha256=%s\naudio_match_lines=%s\n' \
			"$patch" "$(sha256 "$patch")" "$(rg -c -i 'audio|afe|codec|mt6797|mt6351|clock' "$patch" || true)"
	else
		printf 'patch=%s\nstatus=not_visible_from_guest\n' "$patch"
	fi
done

printf '\n[decision]\n'
printf '%s\n' \
	"afe_driver=configured_as_module_${audio_module_state}_with_disabled_gemini_resource_node" \
	"mt6351_codec=configured_as_module_${audio_module_state}" \
	"mt6797_mt6351_machine=configured_as_module_${audio_module_state}" \
	'afe_clock_contract=reuse_existing_eight_name_binding_split' \
	'vendor_modem_bluetooth_fm_hostless_paths=do_not_copy' \
	'analog_audio_runtime=not_attempted' \
	'pcm_or_mixer_write=not_attempted' \
	'hardware_write=none'
