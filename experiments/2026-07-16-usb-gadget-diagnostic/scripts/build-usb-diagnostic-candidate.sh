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
usage: build-usb-diagnostic-candidate.sh --package DIR [--output DIR]
       [--source-date-epoch N]

Build one non-flashing Android v0 candidate from an explicit usbdiag-profile
kernel package. The command never discovers a package implicitly and has no
device, partition, adb, fastboot, mtkclient, or flashing interface.
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
	output="${HOME}/artifacts/boot-candidates/${package_id}-usbdiag"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite $output"

artifact_validator="${repo_root}/scripts/validate-kernel-artifact"
current_manifest="${repo_root}/kernel/manifest.json"
handoff_fragment="${repo_root}/configs/gemini-handoff.fragment"
usbdiag_fragment="${repo_root}/configs/gemini-usbdiag.fragment"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
dtb_builder="${script_dir}/build-usb-diagnostic-dtb.sh"
initramfs_builder="${script_dir}/build-initramfs.sh"
dtb_validator="${repo_root}/experiments/2026-07-16-lk-handoff-alignment/scripts/validate-lk-compatible-dtb.py"
candidate_builder="${script_dir}/build-usb-diagnostic-candidate.sh"
init_source="${script_dir}/../initramfs/init"
shell_source="${script_dir}/../initramfs/usb-shell"
mandatory_overlay="${repo_root}/experiments/2026-07-16-lk-handoff-alignment/dts/lk-handoff.dtso"
usb_overlay="${script_dir}/../dts/usb-gadget.dtso"
busybox=/usr/bin/busybox
for input in \
	"$artifact_validator" "$current_manifest" "$handoff_fragment" \
	"$usbdiag_fragment" "$serializer" "$analyzer" "$dtb_builder" \
	"$initramfs_builder" "$dtb_validator" "$candidate_builder" \
	"$init_source" "$shell_source" "$mandatory_overlay" "$usb_overlay" \
	"$busybox"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

image_gz="${package}/Image.gz"
base_dtb="${package}/dtbs/mediatek/mt6797-gemini-pda.dtb"
config="${package}/kernel.config"
build_json="${package}/provenance/build.json"
package_manifest="${package}/provenance/kernel-manifest.json"
package_series="${package}/provenance/series"
package_handoff_fragment="${package}/provenance/configs/gemini-handoff.fragment"
package_usbdiag_fragment="${package}/provenance/configs/gemini-usbdiag.fragment"
for input in \
	"$image_gz" "$base_dtb" "$config" "$build_json" "$package_manifest" \
	"$package_series" "$package_handoff_fragment" "$package_usbdiag_fragment"; do
	[[ -s "$input" ]] || die "required package input is missing: $input"
done

jq -e '
  .config.profiles.usbdiag.base == "defconfig" and
  .config.profiles.usbdiag.fragments == [
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment"
  ]
' "$current_manifest" >/dev/null || die "current manifest has an unexpected usbdiag profile"
cmp -s "$current_manifest" "$package_manifest" || \
	die "package manifest does not match the current repository manifest"
cmp -s "$handoff_fragment" "$package_handoff_fragment" || \
	die "packaged handoff fragment does not match the repository"
cmp -s "$usbdiag_fragment" "$package_usbdiag_fragment" || \
	die "packaged usbdiag fragment does not match the repository"
packaged_config_files="$(find "${package}/provenance/configs" -maxdepth 1 -type f -printf '%f\n' | sort)"
[[ "$packaged_config_files" == $'gemini-handoff.fragment\ngemini-usbdiag.fragment' ]] || \
	die "package provenance does not contain exactly the usbdiag fragments"

current_series_rel="$(jq -er '.patch_series' "$current_manifest")"
[[ "$current_series_rel" == patches/series ]] || \
	die "current manifest uses an unexpected patch-series path"
current_series="${repo_root}/${current_series_rel}"
current_patch_dir="$(dirname -- "$current_series")"
cmp -s "$current_series" "$package_series" || \
	die "packaged patch series does not match the repository"

declare -a patch_relatives=()
line_number=0
while IFS= read -r relative || [[ -n "$relative" ]]; do
	line_number=$((line_number + 1))
	[[ -z "$relative" || "$relative" == \#* ]] && continue
	[[ "$relative" != *[[:space:]]* ]] || die "$current_series:$line_number: whitespace in patch path"
	[[ "$relative" != /* && "$relative" != *..* ]] || die "$current_series:$line_number: unsafe patch path"
	current_patch="${current_patch_dir}/${relative}"
	packaged_patch="${package}/provenance/patches/${relative}"
	[[ -f "$current_patch" && -f "$packaged_patch" ]] || die "patch is missing: $relative"
	cmp -s "$current_patch" "$packaged_patch" || die "packaged patch differs: $relative"
	patch_relatives+=("$relative")
done <"$current_series"
((${#patch_relatives[@]} > 0)) || die "patch series is empty"
current_patch_files="$(printf '%s\n' "${patch_relatives[@]}" | sort)"
packaged_patch_files="$(find "${package}/provenance/patches" -type f -printf '%P\n' | sort)"
[[ "$packaged_patch_files" == "$current_patch_files" ]] || \
	die "packaged patch tree is not exactly the current series"

patchset_sha256="$({
	printf '%s  %s\n' "$(sha256sum "$current_series" | awk '{print $1}')" "$current_series_rel"
	for relative in "${patch_relatives[@]}"; do
		printf '%s  %s\n' \
			"$(sha256sum "${current_patch_dir}/${relative}" | awk '{print $1}')" \
			"$relative"
	done
} | sha256sum | awk '{print $1}')"
handoff_fragment_sha256="$(sha256sum "$handoff_fragment" | awk '{print $1}')"
usbdiag_fragment_sha256="$(sha256sum "$usbdiag_fragment" | awk '{print $1}')"
config_inputs_sha256="$({
	printf 'profile=usbdiag\n'
	printf 'base=defconfig\n'
	printf '%s  %s\n' "$handoff_fragment_sha256" configs/gemini-handoff.fragment
	printf '%s  %s\n' "$usbdiag_fragment_sha256" configs/gemini-usbdiag.fragment
} | sha256sum | awk '{print $1}')"
resolved_config_sha256="$(sha256sum "$config" | awk '{print $1}')"
source_sha256="$(jq -er '.kernel.sha256' "$current_manifest")"
jq -e \
	--arg patchset "$patchset_sha256" \
	--arg config_inputs "$config_inputs_sha256" \
	--arg config_sha "$resolved_config_sha256" \
	--arg source "$source_sha256" '
  .build_profile == "usbdiag" and
  .base_config == "defconfig" and
  .config_fragments == [
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment"
  ] and
  .patchset_sha256 == $patchset and
  .config_inputs_sha256 == $config_inputs and
  .config_sha256 == $config_sha and
  .source_sha256 == $source and
  (.modules_built // false) == false
' "$build_json" >/dev/null || die "package provenance is not bound to current usbdiag inputs"

require_config() {
	grep -Fqx -- "$1" "$config" || die "usbdiag config is missing: $1"
}
require_config 'CONFIG_LOCALVERSION="-gemini-usbdiag"'
require_config '# CONFIG_MODULES is not set'
require_config '# CONFIG_USB is not set'
require_config '# CONFIG_MMC is not set'
require_config '# CONFIG_DEVMEM is not set'
require_config '# CONFIG_DEVPORT is not set'
required_builtin=(
	CONFIG_ARCH_MEDIATEK
	CONFIG_ARM64_4K_PAGES
	CONFIG_RELOCATABLE
	CONFIG_COMMON_CLK_MT6797
	CONFIG_PINCTRL_MT6797
	CONFIG_MTK_TIMER
	CONFIG_MTK_CPUX_TIMER
	CONFIG_NET
	CONFIG_INET
	CONFIG_USB_SUPPORT
	CONFIG_USB_GADGET
	CONFIG_USB_MTU3
	CONFIG_USB_MTU3_GADGET
	CONFIG_GENERIC_PHY
	CONFIG_PHY_MTK_TPHY
	CONFIG_REGULATOR
	CONFIG_USB_ETH
	CONFIG_USB_ETH_RNDIS
)
for symbol in "${required_builtin[@]}"; do
	require_config "${symbol}=y"
done

rejected_enabled_regex='CONFIG_(CPU_BIG_ENDIAN|DEVMEM|DEVPORT|MTK_PMIC_WRAP|MTK_SCPSYS|MTK_SCPSYS_PM_DOMAINS|MTK_MFG_PM_DOMAIN|MFD_MT6397|REGULATOR_MT|DMADEVICES|IOMMU_SUPPORT|MTK_IOMMU|MTK_SMI|MAILBOX|REMOTEPROC|MTK_SCP|MTK_CMDQ|MTK_MMSYS|THERMAL|IIO|NVMEM|MMC|MTD|SCSI|ATA|I2C|SPI|DRM|SOUND|MEDIA_SUPPORT|WIRELESS|WLAN|WWAN|ETHERNET|NET_CORE|NET_DSA|PHY_CAN_TRANSCEIVER|PHY_CADENCE|USB_MTU3_HOST|USB_MTU3_DUAL_ROLE|USB_XHCI|USB_MUSB|USB_STORAGE|USB_MASS_STORAGE|USB_G_MULTI|USB_CONFIGFS|TYPEC|CHARGER)'
if grep -Eq "^${rejected_enabled_regex}=(y|m)$" "$config"; then
	grep -E "^${rejected_enabled_regex}=(y|m)$" "$config" >&2
	die "usbdiag config enables a rejected family"
fi

mkdir -p "$(dirname -- "$output")"
staging="$(mktemp -d "$(dirname -- "$output")/.${package_id}.XXXXXX")"
cleanup() {
	[[ ! -d "$staging" ]] || rm -rf "$staging"
}
trap cleanup EXIT

normalize_log() {
	local log=$1
	local normalized="${log}.normalized"
	local value
	while IFS= read -r value || [[ -n "$value" ]]; do
		value=${value//"$staging"/@OUTPUT@}
		value=${value//"$package"/@PACKAGE@}
		value=${value//"$repo_root"/@REPOSITORY@}
		printf '%s\n' "$value"
	done <"$log" >"$normalized"
	mv "$normalized" "$log"
}

validation_log="${staging}/package-validation.txt"
config_log="${staging}/usbdiag-config-validation.txt"
dtb="${staging}/mt6797-gemini-pda-lk-usbdiag.dtb"
initramfs="${staging}/gemini-lk-usbdiag-initramfs.img"
candidate="${staging}/gemini-lk-usbdiag.boot.img"

"$artifact_validator" "$package" >"$validation_log"
normalize_log "$validation_log"
{
	printf 'validation=usbdiag-config-probe-closure\n'
	for symbol in "${required_builtin[@]}"; do
		printf 'required_builtin_%s=passed\n' "${symbol#CONFIG_}"
	done
	printf 'rejected_probe_families=absent\n'
	printf 'modules=disabled\n'
	printf 'storage_access=none\n'
	printf 'hardware_write=none\n'
} >"$config_log"
"$dtb_builder" --base "$base_dtb" --output "$dtb" \
	>"${staging}/dtb-validation.txt"
normalize_log "${staging}/dtb-validation.txt"
"$initramfs_builder" --output "$initramfs" --busybox "$busybox" \
	--source-date-epoch "$source_date_epoch" >"${staging}/initramfs-build.txt"
normalize_log "${staging}/initramfs-build.txt"

bootopt='bootopt=64S3,32N2,64N2'
python3 "$serializer" \
	--kernel "$image_gz" \
	--ramdisk "$initramfs" \
	--dtb "$dtb" \
	--output "$candidate" \
	--name gemini-usbdiag \
	--cmdline "$bootopt" \
	--kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 \
	--tags-addr 0x44000000 \
	--lk-android8 >"${staging}/serializer.txt"
normalize_log "${staging}/serializer.txt"
python3 "$analyzer" --validate-lk --expected-dtb "$dtb" "$candidate" \
	>"${staging}/analysis.txt"
normalize_log "${staging}/analysis.txt"
install -m 0600 "$build_json" "${staging}/source-build.json"

repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
repo_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
repo_status_sha256="$(printf '%s\n' "$repo_status" | sha256sum | awk '{print $1}')"
{
	printf 'experiment=2026-07-16-usb-gadget-diagnostic\n'
	printf 'bsg100_reference_main=9d1e565a5ba11ae9585340e3e4bf4cacc233d13c\n'
	printf 'bsg100_gadget_reference=fd5b10277198356d8c9b93478af6054b1c643597\n'
	printf 'bsg100_session_force_reference=76cd816b3da62ab918b2eed1312c5b18f6538c31\n'
	printf 'package=%s\n' "$package_id"
	printf 'build_profile=usbdiag\n'
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'repo_status_sha256=%s\n' "$repo_status_sha256"
	printf 'source_date_epoch=%s\n' "$source_date_epoch"
	printf 'kernel_addr=0x40200000\nramdisk_addr=0x45000000\n'
	printf 'second_addr=0x40f00000\ntags_addr=0x44000000\n'
	printf 'header_cmdline=%s\n' "$bootopt"
	printf 'source_sha256=%s\n' "$source_sha256"
	printf 'patchset_sha256=%s\n' "$patchset_sha256"
	printf 'config_sha256=%s\n' "$resolved_config_sha256"
	printf 'config_inputs_sha256=%s\n' "$config_inputs_sha256"
	printf 'handoff_fragment_sha256=%s\n' "$handoff_fragment_sha256"
	printf 'usbdiag_fragment_sha256=%s\n' "$usbdiag_fragment_sha256"
	for input in \
		"$current_manifest" "$candidate_builder" "$artifact_validator" \
		"$serializer" "$analyzer" "$dtb_builder" "$dtb_validator" \
		"$initramfs_builder" "$mandatory_overlay" "$usb_overlay" \
		"$init_source" "$shell_source" "$busybox"; do
		printf 'input_sha256[%s]=%s\n' \
			"${input#"$repo_root"/}" "$(sha256sum "$input" | awk '{print $1}')"
	done
	printf 'image_gz_sha256=%s\n' "$(sha256sum "$image_gz" | awk '{print $1}')"
	printf 'base_dtb_sha256=%s\n' "$(sha256sum "$base_dtb" | awk '{print $1}')"
	printf 'usbdiag_dtb_sha256=%s\n' "$(sha256sum "$dtb" | awk '{print $1}')"
	printf 'initramfs_sha256=%s\n' "$(sha256sum "$initramfs" | awk '{print $1}')"
	printf 'candidate_sha256=%s\n' "$(sha256sum "$candidate" | awk '{print $1}')"
	printf 'usb_product=Gemini-LK-USB-Diagnostic-B\n'
	printf 'usb_serial=GEMINI_USB_DIAG_20260716_B\n'
	printf 'device_address=10.15.19.82/24\n'
	printf 'tcp_shell_port=2323\n'
	printf 'storage_access=none\nhardware_write=none\nflash=none\n'
	printf '\n[parser]\n'
	cat "${staging}/analysis.txt"
} >"${staging}/provenance.txt"

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

printf 'validation=usb-diagnostic-candidate\n'
printf 'package=%s\n' "$package_id"
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-lk-usbdiag.boot.img\n' "$output"
printf 'candidate_sha256=%s\n' "$(sha256sum "$output/gemini-lk-usbdiag.boot.img" | awk '{print $1}')"
printf 'hardware_write=none\nflash=none\n'
