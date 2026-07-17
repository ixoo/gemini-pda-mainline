#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() {
	echo "error: $*" >&2
	exit 2
}

usage() {
	cat >&2 <<'EOF'
usage: build-lk-handoff-candidate.sh --package DIR [--output DIR]
       [--source-date-epoch N]

Build two non-flashing Android v0 candidates from an explicit handoff-profile
kernel package: mandatory LK handoff DT only, and the same inputs plus optional
simplefb diagnostics. The command never discovers a package implicitly and has
no device, partition, adb, fastboot, mtkclient, or flashing interface.
EOF
}

package=
output=
source_date_epoch=${SOURCE_DATE_EPOCH:-0}
while (($#)); do
	case "$1" in
		--package)
			(($# >= 2)) || die "--package requires DIR"
			package=$2
			shift 2
			;;
		--output)
			(($# >= 2)) || die "--output requires DIR"
			output=$2
			shift 2
			;;
		--source-date-epoch)
			(($# >= 2)) || die "--source-date-epoch requires N"
			source_date_epoch=$2
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			usage
			die "unknown option: $1"
			;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die "run inside the Linux development VM"
[[ "$(uname -m)" == aarch64 ]] || die "expected an aarch64 development VM"
[[ -n "$package" ]] || die "--package is required; implicit newest-package selection is forbidden"
[[ -d "$package" ]] || die "package does not exist: $package"
[[ "$source_date_epoch" =~ ^[0-9]+$ ]] || die "epoch must be a non-negative integer"
for command in awk cmp find git grep jq python3 sha256sum sort; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "${script_dir}/../../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
package_id="$(basename -- "$package")"
if [[ -z "$output" ]]; then
	output="${HOME}/artifacts/boot-candidates/${package_id}-lk-handoff"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite $output"

artifact_validator="${repo_root}/scripts/validate-kernel-artifact"
current_manifest="${repo_root}/kernel/manifest.json"
current_fragment="${repo_root}/configs/gemini-handoff.fragment"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
dtb_builder="${script_dir}/build-lk-compatible-dtb.sh"
initramfs_builder="${script_dir}/build-initramfs.sh"
dtb_validator="${script_dir}/validate-lk-compatible-dtb.py"
candidate_builder="${script_dir}/build-lk-handoff-candidate.sh"
init_source="${script_dir}/../initramfs/init"
mandatory_overlay_source="${script_dir}/../dts/lk-handoff.dtso"
simplefb_overlay_source="${script_dir}/../dts/lk-simplefb.dtso"
busybox=/usr/bin/busybox
for helper in \
	"$artifact_validator" "$serializer" "$analyzer" "$dtb_builder" \
	"$dtb_validator" "$initramfs_builder" "$candidate_builder"; do
	[[ -r "$helper" ]] || die "required helper is missing: $helper"
done
for source_input in \
	"$current_manifest" "$current_fragment" "$init_source" \
	"$mandatory_overlay_source" "$simplefb_overlay_source" "$busybox"; do
	[[ -s "$source_input" ]] || die "required source input is missing: $source_input"
done

image_gz="${package}/Image.gz"
base_dtb="${package}/dtbs/mediatek/mt6797-gemini-pda.dtb"
config="${package}/kernel.config"
build_json="${package}/provenance/build.json"
package_manifest="${package}/provenance/kernel-manifest.json"
package_fragment="${package}/provenance/configs/gemini-handoff.fragment"
package_series="${package}/provenance/series"
for input in "$image_gz" "$base_dtb" "$config" "$build_json"; do
	[[ -s "$input" ]] || die "required package input is missing: $input"
done
[[ -s "$package_manifest" ]] || die "package manifest is missing: $package_manifest"
[[ -s "$package_fragment" ]] || die "package handoff fragment is missing: $package_fragment"
[[ -s "$package_series" ]] || die "package patch series is missing: $package_series"

jq -e '
  .config.profiles.handoff.base == "defconfig" and
  .config.profiles.handoff.fragments == ["configs/gemini-handoff.fragment"]
' "$current_manifest" >/dev/null || die "current manifest handoff profile is not the expected exact profile"
cmp -s "$current_manifest" "$package_manifest" || \
	die "package manifest does not match the current repository manifest"
cmp -s "$current_fragment" "$package_fragment" || \
	die "packaged handoff fragment does not match the current repository fragment"
packaged_config_files="$(find "${package}/provenance/configs" -maxdepth 1 -type f -printf '%f\n' | sort)"
[[ "$packaged_config_files" == gemini-handoff.fragment ]] || \
	die "package provenance does not contain exactly the handoff fragment"

current_series_rel="$(jq -er '.patch_series' "$current_manifest")"
[[ "$current_series_rel" == patches/series ]] || \
	die "current manifest uses an unexpected patch-series path: $current_series_rel"
current_series="${repo_root}/${current_series_rel}"
current_patch_dir="$(dirname -- "$current_series")"
[[ -s "$current_series" ]] || die "current patch series is missing: $current_series"
cmp -s "$current_series" "$package_series" || \
	die "packaged patch series does not match the current repository series"

declare -a current_patch_relatives=()
line_number=0
while IFS= read -r relative || [[ -n "$relative" ]]; do
	line_number=$((line_number + 1))
	[[ -z "$relative" || "$relative" == \#* ]] && continue
	[[ "$relative" != *[[:space:]]* ]] || \
		die "$current_series:$line_number: patch paths may not contain whitespace"
	[[ "$relative" != /* && "$relative" != *..* ]] || \
		die "$current_series:$line_number: patch path must remain below patches/"
	current_patch="${current_patch_dir}/${relative}"
	packaged_patch="${package}/provenance/patches/${relative}"
	[[ -f "$current_patch" ]] || die "current patch is missing: $relative"
	[[ -f "$packaged_patch" ]] || die "packaged patch is missing: $relative"
	cmp -s "$current_patch" "$packaged_patch" || \
		die "packaged patch does not match the current repository patch: $relative"
	current_patch_relatives+=("$relative")
done <"$current_series"
((${#current_patch_relatives[@]} > 0)) || die "current patch series is empty"

current_patch_files="$(printf '%s\n' "${current_patch_relatives[@]}" | sort)"
packaged_patch_files="$(find "${package}/provenance/patches" -type f -printf '%P\n' | sort)"
[[ "$packaged_patch_files" == "$current_patch_files" ]] || \
	die "packaged patch tree does not contain exactly the current patch series"
current_patchset_sha256="$({
	printf '%s  %s\n' "$(sha256sum "$current_series" | awk '{print $1}')" "$current_series_rel"
	for relative in "${current_patch_relatives[@]}"; do
		printf '%s  %s\n' \
			"$(sha256sum "${current_patch_dir}/${relative}" | awk '{print $1}')" \
			"$relative"
	done
} | sha256sum | awk '{print $1}')"
current_source_sha256="$(jq -er '.kernel.sha256' "$current_manifest")"

current_fragment_sha256="$(sha256sum "$current_fragment" | awk '{print $1}')"
expected_config_inputs_sha256="$({
	printf 'profile=handoff\n'
	printf 'base=defconfig\n'
	printf '%s  %s\n' "$current_fragment_sha256" 'configs/gemini-handoff.fragment'
} | sha256sum | awk '{print $1}')"
resolved_config_sha256="$(sha256sum "$config" | awk '{print $1}')"
jq -e \
	--arg config_inputs_sha256 "$expected_config_inputs_sha256" \
	--arg config_sha256 "$resolved_config_sha256" \
	--arg patchset_sha256 "$current_patchset_sha256" \
	--arg source_sha256 "$current_source_sha256" '
  .build_profile == "handoff" and
  .base_config == "defconfig" and
  .config_fragments == ["configs/gemini-handoff.fragment"] and
  .config_inputs_sha256 == $config_inputs_sha256 and
  .config_sha256 == $config_sha256 and
  .patchset_sha256 == $patchset_sha256 and
  .source_sha256 == $source_sha256
' "$build_json" >/dev/null || \
	die "package build provenance is not bound to the current source/patches/handoff inputs/config"
[[ "$(jq -er '.build_profile' "$build_json")" == handoff ]] || \
	die "package provenance build_profile is not handoff"
[[ "$(jq -er '.modules_built // false' "$build_json")" == false ]] || \
	die "handoff package must not contain modules"

require_config_line() {
	grep -Fqx -- "$1" "$config" || die "handoff kernel config is missing: $1"
}
require_config_line 'CONFIG_LOCALVERSION="-gemini-handoff"'
require_config_line 'CONFIG_RELOCATABLE=y'
require_config_line 'CONFIG_CMDLINE_FORCE=y'
require_config_line 'CONFIG_CMDLINE="console=tty0 console=ttyS0,921600n8 earlycon maxcpus=1 nokaslr ignore_loglevel loglevel=8 rdinit=/init panic=0"'
require_config_line 'CONFIG_BLK_DEV_INITRD=y'
require_config_line '# CONFIG_MODULES is not set'

required_builtin=(
	CONFIG_ARCH_MEDIATEK
	CONFIG_ARM64_4K_PAGES
	CONFIG_CPU_LITTLE_ENDIAN
	CONFIG_COMMON_CLK_MEDIATEK
	CONFIG_COMMON_CLK_MT6797
	CONFIG_PINCTRL
	CONFIG_PINCTRL_MT6797
	CONFIG_MTK_TIMER
	CONFIG_MTK_CPUX_TIMER
	CONFIG_SERIAL_EARLYCON
	CONFIG_SERIAL_8250
	CONFIG_SERIAL_8250_CONSOLE
	CONFIG_SERIAL_8250_MT6577
	CONFIG_WATCHDOG
	CONFIG_MEDIATEK_WATCHDOG
	CONFIG_DEVTMPFS
	CONFIG_DEVTMPFS_MOUNT
	CONFIG_VT
	CONFIG_VT_CONSOLE
	CONFIG_DUMMY_CONSOLE
	CONFIG_FB
	CONFIG_FB_SIMPLE
	CONFIG_FRAMEBUFFER_CONSOLE
)
for symbol in "${required_builtin[@]}"; do
	require_config_line "${symbol}=y"
done

# Validate the actual resolved .config, not merely the requested fragment. The
# first handoff candidate must have no probe-capable path from these families.
rejected_enabled_regex='CONFIG_(CPU_BIG_ENDIAN|MTK_PMIC_WRAP|MTK_SCPSYS|MTK_SCPSYS_PM_DOMAINS|MTK_MFG_PM_DOMAIN|REGULATOR|MFD_MT6397|DMADEVICES|MTK_CQDMA|MTK_HSDMA|MTK_UART_APDMA|IOMMU_SUPPORT|MTK_IOMMU|MTK_SMI|MAILBOX|MTK_.*MBOX|REMOTEPROC|MTK_SCP|MTK_CMDQ|MTK_MMSYS|THERMAL|IIO|NVMEM|MMC|USB_SUPPORT|NET|I2C|SPI|DRM|SOUND|MEDIA_SUPPORT)'
if grep -Eq "^${rejected_enabled_regex}=(y|m)$" "$config"; then
	grep -E "^${rejected_enabled_regex}=(y|m)$" "$config" >&2
	die "handoff kernel config enables a rejected probe family"
fi

mkdir -p "$(dirname -- "$output")"
staging="$(mktemp -d "$(dirname -- "$output")/.${package_id}.XXXXXX")"
cleanup() {
	if [[ -d "$staging" ]]; then
		rm -rf "$staging"
	fi
}
trap cleanup EXIT

normalize_log() {
	local log=$1
	local normalized="${log}.normalized"
	local line
	while IFS= read -r line || [[ -n "$line" ]]; do
		line=${line//"$staging"/@OUTPUT@}
		line=${line//"$package"/@PACKAGE@}
		line=${line//"$repo_root"/@REPOSITORY@}
		printf '%s\n' "$line"
	done <"$log" >"$normalized"
	mv "$normalized" "$log"
}

repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
repo_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
if [[ -n "$repo_status" ]]; then
	repo_dirty=yes
else
	repo_dirty=no
fi
repo_status_sha256="$(printf '%s\n' "$repo_status" | sha256sum | awk '{print $1}')"

tool_version() {
	local executable=$1
	local output
	output="$("$executable" --version 2>&1)" || \
		die "cannot obtain packaging tool version: $executable"
	printf '%s' "${output%%$'\n'*}"
}

tool_sha256() {
	local executable=$1
	if [[ -f "$executable" ]]; then
		sha256sum "$executable" | awk '{print $1}'
	else
		printf 'unavailable'
	fi
}

dtc_executable="$(command -v dtc)"
fdtoverlay_executable="$(command -v fdtoverlay)"
cpio_executable="$(command -v cpio)"
gzip_executable="$(command -v gzip)"
python3_executable="$(command -v python3)"
dtc_version="$(tool_version "$dtc_executable")"
fdtoverlay_version="$(tool_version "$fdtoverlay_executable")"
cpio_version="$(tool_version "$cpio_executable")"
gzip_version="$(tool_version "$gzip_executable")"
python3_version="$(tool_version "$python3_executable")"
dtc_executable_sha256="$(tool_sha256 "$dtc_executable")"
fdtoverlay_executable_sha256="$(tool_sha256 "$fdtoverlay_executable")"
cpio_executable_sha256="$(tool_sha256 "$cpio_executable")"
gzip_executable_sha256="$(tool_sha256 "$gzip_executable")"
python3_executable_sha256="$(tool_sha256 "$python3_executable")"

if command -v dpkg-query >/dev/null 2>&1; then
	dpkg_snapshot="$({
		for package_name in busybox-static cpio device-tree-compiler gzip python3-minimal; do
			dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' \
				"$package_name" 2>/dev/null || true
		done
	} | sort)"
	if [[ -n "$dpkg_snapshot" ]]; then
		dpkg_snapshot_sha256="$(printf '%s\n' "$dpkg_snapshot" | sha256sum | awk '{print $1}')"
	else
		dpkg_snapshot_sha256=unavailable
	fi
else
	dpkg_snapshot_sha256=unavailable
fi

validation_log="${staging}/package-validation.txt"
config_validation_log="${staging}/handoff-config-validation.txt"
serial_dtb="${staging}/mt6797-gemini-pda-lk-handoff.dtb"
display_dtb="${staging}/mt6797-gemini-pda-lk-handoff-simplefb.dtb"
initramfs="${staging}/gemini-lk-handoff-initramfs.img"
serial_image="${staging}/gemini-lk-handoff-serial.boot.img"
display_image="${staging}/gemini-lk-handoff-display.boot.img"

"$artifact_validator" "$package" >"$validation_log"
normalize_log "$validation_log"
{
	printf 'validation=handoff-config-probe-closure\n'
	for symbol in "${required_builtin[@]}"; do
		printf 'required_builtin_%s=passed\n' "${symbol#CONFIG_}"
	done
	printf 'rejected_probe_families=absent\n'
	printf 'modules=disabled\n'
	printf 'hardware_write=none\n'
} >"$config_validation_log"
"$dtb_builder" --base "$base_dtb" --output "$serial_dtb" \
	>"${staging}/serial-dtb-validation.txt"
normalize_log "${staging}/serial-dtb-validation.txt"
"$dtb_builder" --base "$base_dtb" --output "$display_dtb" --with-simplefb \
	>"${staging}/display-dtb-validation.txt"
normalize_log "${staging}/display-dtb-validation.txt"
"$initramfs_builder" --output "$initramfs" --busybox "$busybox" \
	--source-date-epoch "$source_date_epoch" \
	>"${staging}/initramfs-build.txt"
normalize_log "${staging}/initramfs-build.txt"

bootopt='bootopt=64S3,32N2,64N2'
build_variant() {
	local variant=$1
	local dtb=$2
	local image=$3
	python3 "$serializer" \
		--kernel "$image_gz" \
		--ramdisk "$initramfs" \
		--dtb "$dtb" \
		--output "$image" \
		--name gemini-lk \
		--cmdline "$bootopt" \
		--kernel-addr 0x40200000 \
		--ramdisk-addr 0x45000000 \
		--second-addr 0x40f00000 \
		--tags-addr 0x44000000 \
		--lk-android8 >"${staging}/${variant}-serializer.txt"
	normalize_log "${staging}/${variant}-serializer.txt"
	python3 "$analyzer" --validate-lk --expected-dtb "$dtb" "$image" \
		>"${staging}/${variant}-analysis.txt"
	normalize_log "${staging}/${variant}-analysis.txt"
}
build_variant serial "$serial_dtb" "$serial_image"
build_variant display "$display_dtb" "$display_image"

install -m 0600 "$build_json" "${staging}/source-build.json"

provenance="${staging}/provenance.txt"
{
	printf 'experiment=2026-07-16-lk-handoff-alignment\n'
	printf 'bsg100_reference_commit=9d1e565a5ba11ae9585340e3e4bf4cacc233d13c\n'
	printf 'package=%s\n' "$package_id"
	printf 'build_profile=handoff\n'
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'repo_dirty=%s\n' "$repo_dirty"
	printf 'repo_status_sha256=%s\n' "$repo_status_sha256"
	printf 'source_date_epoch=%s\n' "$source_date_epoch"
	printf 'kernel_addr=0x40200000\n'
	printf 'ramdisk_addr=0x45000000\n'
	printf 'second_addr=0x40f00000\n'
	printf 'tags_addr=0x44000000\n'
	printf 'header_cmdline=%s\n' "$bootopt"
	printf 'source_sha256=%s\n' "$(jq -er '.source_sha256' "$build_json")"
	printf 'patchset_sha256=%s\n' "$(jq -er '.patchset_sha256' "$build_json")"
	printf 'config_sha256=%s\n' "$(jq -er '.config_sha256' "$build_json")"
	printf 'config_inputs_sha256=%s\n' "$expected_config_inputs_sha256"
	printf 'kernel_manifest_sha256=%s\n' "$(sha256sum "$current_manifest" | awk '{print $1}')"
	printf 'handoff_fragment_sha256=%s\n' "$current_fragment_sha256"
	printf 'source_build_json_sha256=%s\n' "$(sha256sum "$build_json" | awk '{print $1}')"
	printf 'busybox_sha256=%s\n' "$(sha256sum "$busybox" | awk '{print $1}')"
	printf 'init_source_sha256=%s\n' "$(sha256sum "$init_source" | awk '{print $1}')"
	printf 'mandatory_overlay_source_sha256=%s\n' "$(sha256sum "$mandatory_overlay_source" | awk '{print $1}')"
	printf 'simplefb_overlay_source_sha256=%s\n' "$(sha256sum "$simplefb_overlay_source" | awk '{print $1}')"
	printf 'candidate_builder_sha256=%s\n' "$(sha256sum "$candidate_builder" | awk '{print $1}')"
	printf 'artifact_validator_sha256=%s\n' "$(sha256sum "$artifact_validator" | awk '{print $1}')"
	printf 'serializer_sha256=%s\n' "$(sha256sum "$serializer" | awk '{print $1}')"
	printf 'analyzer_sha256=%s\n' "$(sha256sum "$analyzer" | awk '{print $1}')"
	printf 'dtb_builder_sha256=%s\n' "$(sha256sum "$dtb_builder" | awk '{print $1}')"
	printf 'dtb_validator_sha256=%s\n' "$(sha256sum "$dtb_validator" | awk '{print $1}')"
	printf 'initramfs_builder_sha256=%s\n' "$(sha256sum "$initramfs_builder" | awk '{print $1}')"
	printf 'dtc_version=%s\n' "$dtc_version"
	printf 'dtc_executable_sha256=%s\n' "$dtc_executable_sha256"
	printf 'fdtoverlay_version=%s\n' "$fdtoverlay_version"
	printf 'fdtoverlay_executable_sha256=%s\n' "$fdtoverlay_executable_sha256"
	printf 'cpio_version=%s\n' "$cpio_version"
	printf 'cpio_executable_sha256=%s\n' "$cpio_executable_sha256"
	printf 'gzip_version=%s\n' "$gzip_version"
	printf 'gzip_executable_sha256=%s\n' "$gzip_executable_sha256"
	printf 'python3_version=%s\n' "$python3_version"
	printf 'python3_executable_sha256=%s\n' "$python3_executable_sha256"
	printf 'packaging_dpkg_snapshot_sha256=%s\n' "$dpkg_snapshot_sha256"
	printf 'image_gz_sha256=%s\n' "$(sha256sum "$image_gz" | awk '{print $1}')"
	printf 'base_dtb_sha256=%s\n' "$(sha256sum "$base_dtb" | awk '{print $1}')"
	printf 'serial_dtb_sha256=%s\n' "$(sha256sum "$serial_dtb" | awk '{print $1}')"
	printf 'display_dtb_sha256=%s\n' "$(sha256sum "$display_dtb" | awk '{print $1}')"
	printf 'initramfs_sha256=%s\n' "$(sha256sum "$initramfs" | awk '{print $1}')"
	printf 'serial_candidate_sha256=%s\n' "$(sha256sum "$serial_image" | awk '{print $1}')"
	printf 'display_candidate_sha256=%s\n' "$(sha256sum "$display_image" | awk '{print $1}')"
	printf 'hardware_write=none\nflash=none\n'
	printf '\n[serial_parser]\n'
	cat "${staging}/serial-analysis.txt"
	printf '\n[display_parser]\n'
	cat "${staging}/display-analysis.txt"
} >"$provenance"

(
	cd "$staging"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"${staging}/SHA256SUMS"
(
	cd "$staging"
	sha256sum --check SHA256SUMS >/dev/null
)
chmod 0600 "${staging}"/*
mv "$staging" "$output"
staging=
trap - EXIT

printf 'validation=lk-handoff-candidate\n'
printf 'package=%s\n' "$package_id"
printf 'output=%s\n' "$output"
printf 'serial_candidate=%s/gemini-lk-handoff-serial.boot.img\n' "$output"
printf 'display_candidate=%s/gemini-lk-handoff-display.boot.img\n' "$output"
printf 'serial_candidate_sha256=%s\n' "$(sha256sum "$output/gemini-lk-handoff-serial.boot.img" | awk '{print $1}')"
printf 'display_candidate_sha256=%s\n' "$(sha256sum "$output/gemini-lk-handoff-display.boot.img" | awk '{print $1}')"
printf 'hardware_write=none\nflash=none\n'
