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
usage: build-observability-candidate.sh --package DIR [--output DIR]
       [--source-date-epoch N]

Build non-flashing Candidate L from an explicit observability-profile package.
The package must be bound to the current manifest, patch series, configuration
fragments and resolved config. The command never selects a package implicitly
and has no device, partition, adb, fastboot, mtkclient or flashing interface.
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
[[ "$source_date_epoch" =~ ^[0-9]+$ && "$source_date_epoch" == 0 ]] || \
	die "Candidate L requires source-date-epoch zero"
for command in \
	awk basename cat chmod cmp dirname find git grep install jq mkdir mktemp \
	mv python3 rm sha256sum sort uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
repo_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
[[ -z "$repo_status" ]] || \
	die "Candidate L requires a clean repository so repo_revision identifies every input"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
repo_status_sha256="$(printf '%s' "$repo_status" | sha256sum | awk '{print $1}')"
package="$(cd -- "$package" && pwd -P)"
package_id="$(basename -- "$package")"
if [[ -z "$output" ]]; then
	output="${HOME}/artifacts/boot-candidates/${package_id}-candidate-L"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite $output"

artifact_validator="${repo_root}/scripts/validate-kernel-artifact"
current_manifest="${repo_root}/kernel/manifest.json"
current_series="${repo_root}/patches/series"
dtb_builder="${script_dir}/build-observability-dtb.sh"
dtb_validator="${script_dir}/validate-observability-dtb.py"
initramfs_builder="${script_dir}/build-initramfs.sh"
init_contract_validator="${script_dir}/validate-init-contract.sh"
ramoops_layout_validator="${script_dir}/validate-cross-version-ramoops-layout.py"
ramoops_layout_result="${experiment_dir}/results/cross-version-ramoops-layout-20260717.txt"
ramoops_live_result="${experiment_dir}/results/exact-live-ramoops-binary-audit-20260717.txt"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
candidate_builder="${script_dir}/build-observability-candidate.sh"
init_source="${experiment_dir}/initramfs/init"
report_source="${experiment_dir}/initramfs/usb-report"
busybox=/usr/bin/busybox
fragments=(
	configs/gemini-handoff.fragment
	configs/gemini-usbdiag.fragment
	configs/gemini-clk-ignore-unused.fragment
	configs/gemini-observability.fragment
)
for input in \
	"$artifact_validator" "$current_manifest" "$current_series" \
	"$dtb_builder" "$dtb_validator" "$initramfs_builder" \
	"$init_contract_validator" "$ramoops_layout_validator" \
	"$ramoops_layout_result" "$ramoops_live_result" "$serializer" "$analyzer" \
	"$candidate_builder" "$init_source" "$report_source" "$busybox"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done
readonly EXPECTED_RAMOOPS_VALIDATOR_SHA256=a7de63b42004754afd70caeed60f30697f2fc94b3093f16f205968fa6ade35dc
readonly EXPECTED_RAMOOPS_LAYOUT_RESULT_SHA256=6582bc8f533d323d098e3fd232a5df2c68b8453de220934ef1cd953b1f55923f
readonly EXPECTED_RAMOOPS_LIVE_RESULT_SHA256=ac8d935d3aeaa6eeec84fdf8f4422afd669b8330d3681a96f31484926d784900
[[ "$(sha256sum "$ramoops_layout_validator" | awk '{print $1}')" == \
	"$EXPECTED_RAMOOPS_VALIDATOR_SHA256" ]] || die "cross-version validator is not pinned"
[[ "$(sha256sum "$ramoops_layout_result" | awk '{print $1}')" == \
	"$EXPECTED_RAMOOPS_LAYOUT_RESULT_SHA256" ]] || die "cross-version result is not pinned"
[[ "$(sha256sum "$ramoops_live_result" | awk '{print $1}')" == \
	"$EXPECTED_RAMOOPS_LIVE_RESULT_SHA256" ]] || die "exact-live binary result is not pinned"
grep -Fqx 'result=PASS' "$ramoops_layout_result" || \
	die "cross-version ramoops source/layout audit did not pass"
grep -Fqx 'mainline_console_gemian_file=console-ramoops' \
	"$ramoops_layout_result" || die "cross-version console recovery path is not pinned"
grep -Fqx 'mainline_pmsg_cross_version_recoverable=no-layout-mismatch-header-zapped-frontend-disabled' \
	"$ramoops_layout_result" || die "cross-version pmsg incompatibility is not pinned"
grep -Fqx 'recommended_candidate_layout=mainline-console-on-exact-live-primary-console' \
	"$ramoops_live_result" || die "exact-live ramoops layout decision is not pinned"
for relative in "${fragments[@]}"; do
	[[ -s "${repo_root}/${relative}" ]] || die "missing config fragment: $relative"
done

image="${package}/Image"
image_gz="${package}/Image.gz"
base_dtb="${package}/dtbs/mediatek/mt6797-gemini-pda.dtb"
config="${package}/kernel.config"
build_json="${package}/provenance/build.json"
package_manifest="${package}/provenance/kernel-manifest.json"
package_series="${package}/provenance/series"
for input in \
	"$image" "$image_gz" "$base_dtb" "$config" "$build_json" \
	"$package_manifest" "$package_series"; do
	[[ -s "$input" ]] || die "required package input is missing: $input"
done

readonly EXPECTED_KERNEL_RELEASE=7.1.3-gemini-observability-L
readonly EXPECTED_COMPILER='gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0'
readonly EXPECTED_LINKER='GNU ld (GNU Binutils for Ubuntu) 2.42'

jq -e '
  .schema == 1 and
  .kernel.version == "7.1.3" and
  .architecture == "arm64" and
  .patch_series == "patches/series" and
  .config.profiles.observability == {
    "base": "defconfig",
    "fragments": [
      "configs/gemini-handoff.fragment",
      "configs/gemini-usbdiag.fragment",
      "configs/gemini-clk-ignore-unused.fragment",
      "configs/gemini-observability.fragment"
    ]
  }
' "$current_manifest" >/dev/null || die "current manifest has an unexpected observability profile"
cmp -s "$current_manifest" "$package_manifest" || \
	die "packaged manifest is not byte-identical to the current manifest"
cmp -s "$current_series" "$package_series" || \
	die "packaged patch series is not byte-identical to the current series"

declare -a patch_relatives=()
line_number=0
while IFS= read -r relative || [[ -n "$relative" ]]; do
	line_number=$((line_number + 1))
	[[ -z "$relative" || "$relative" == \#* ]] && continue
	[[ "$relative" != *[[:space:]]* ]] || die "$current_series:$line_number: whitespace in patch path"
	[[ "$relative" != /* && "$relative" != *..* ]] || die "$current_series:$line_number: unsafe patch path"
	current_patch="${repo_root}/patches/${relative}"
	packaged_patch="${package}/provenance/patches/${relative}"
	[[ -f "$current_patch" && -f "$packaged_patch" ]] || die "patch is missing: $relative"
	cmp -s "$current_patch" "$packaged_patch" || die "packaged patch differs: $relative"
	patch_relatives+=("$relative")
done <"$current_series"
((${#patch_relatives[@]} > 0)) || die "patch series is empty"
packaged_patch_files="$(find "${package}/provenance/patches" -type f -printf '%P\n' | sort)"
current_patch_files="$(printf '%s\n' "${patch_relatives[@]}" | sort)"
[[ "$packaged_patch_files" == "$current_patch_files" ]] || \
	die "packaged patch tree is not exactly the current series"
for required_patch in \
	v7.1.3/0079-arm64-dts-mediatek-gemini-fix-UART0-pinmux.patch \
	v7.1.3/0080-arm64-dts-mediatek-gemini-add-ramoops-backend.patch \
	v7.1.3/0081-watchdog-mtk-set-MT6797-auto-restart-mode.patch; do
	printf '%s\n' "${patch_relatives[@]}" | grep -Fqx "$required_patch" || \
		die "observability package lacks required patch: $required_patch"
done

packaged_fragment_files="$(find "${package}/provenance/configs" -type f -printf '%P\n' | sort)"
expected_fragment_files="$(printf '%s\n' "${fragments[@]##*/}" | sort)"
[[ "$packaged_fragment_files" == "$expected_fragment_files" ]] || \
	die "package provenance does not contain exactly the observability fragments"
for relative in "${fragments[@]}"; do
	cmp -s "${repo_root}/${relative}" \
		"${package}/provenance/configs/${relative##*/}" || \
		die "packaged config fragment differs: $relative"
done

patchset_sha256="$({
	printf '%s  %s\n' "$(sha256sum "$current_series" | awk '{print $1}')" patches/series
	for relative in "${patch_relatives[@]}"; do
		printf '%s  %s\n' \
			"$(sha256sum "${repo_root}/patches/${relative}" | awk '{print $1}')" \
			"$relative"
	done
} | sha256sum | awk '{print $1}')"
config_inputs_sha256="$({
	printf 'profile=observability\nbase=defconfig\n'
	for relative in "${fragments[@]}"; do
		printf '%s  %s\n' \
			"$(sha256sum "${repo_root}/${relative}" | awk '{print $1}')" \
			"$relative"
	done
} | sha256sum | awk '{print $1}')"
kernel_version="$(jq -er '.kernel.version' "$current_manifest")"
expected_package_id="linux-${kernel_version}-gemini-observability-${patchset_sha256:0:8}-${config_inputs_sha256:0:8}"
[[ "$package_id" == "$expected_package_id" ]] || \
	die "package name is not the deterministic observability input identity: $expected_package_id"
resolved_config_sha256="$(sha256sum "$config" | awk '{print $1}')"
source_sha256="$(jq -er '.kernel.sha256' "$current_manifest")"
jq -e \
	--arg patchset "$patchset_sha256" \
	--arg config_inputs "$config_inputs_sha256" \
	--arg config_sha "$resolved_config_sha256" \
	--arg source "$source_sha256" \
	--arg kernel_release "$EXPECTED_KERNEL_RELEASE" \
	--arg compiler "$EXPECTED_COMPILER" \
	--arg linker "$EXPECTED_LINKER" '
  .build_profile == "observability" and
  .kernel_release == $kernel_release and
  .base_config == "defconfig" and
  .config_fragments == [
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment"
  ] and
  .patchset_sha256 == $patchset and
  .config_inputs_sha256 == $config_inputs and
  .config_sha256 == $config_sha and
  .source_sha256 == $source and
  .modules_built == false and
  .compiler == $compiler and
  .linker == $linker
' "$build_json" >/dev/null || die "package build provenance is not bound to current observability inputs"

require_config() {
	grep -Fqx -- "$1" "$config" || die "observability config is missing: $1"
}
require_config 'CONFIG_LOCALVERSION="-gemini-observability-L"'
require_config 'CONFIG_INITRAMFS_SOURCE=""'
require_config 'CONFIG_CMDLINE_FORCE=y'
require_config '# CONFIG_MODULES is not set'
require_config '# CONFIG_MMC is not set'
require_config '# CONFIG_MTD is not set'
require_config '# CONFIG_SCSI is not set'
require_config '# CONFIG_ATA is not set'
require_config '# CONFIG_DEVMEM is not set'
require_config '# CONFIG_DEVPORT is not set'
require_config '# CONFIG_DRM is not set'
require_config 'CONFIG_PSTORE=y'
require_config 'CONFIG_PSTORE_RAM=y'
require_config 'CONFIG_PSTORE_CONSOLE=y'
require_config '# CONFIG_PSTORE_PMSG is not set'
require_config '# CONFIG_PSTORE_COMPRESS is not set'
require_config '# CONFIG_PSTORE_BLK is not set'
if grep -Eq '^CONFIG_PSTORE_FTRACE=' "$config"; then
	die 'observability config unexpectedly enables the pstore ftrace frontend'
fi
require_config 'CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y'
require_config 'CONFIG_WATCHDOG_OPEN_TIMEOUT=0'
require_config 'CONFIG_WATCHDOG_SYSFS=y'
require_config '# CONFIG_WATCHDOG_HRTIMER_PRETIMEOUT is not set'
require_config 'CONFIG_MEDIATEK_WATCHDOG=y'
require_config 'CONFIG_SERIAL_8250_MT6577=y'
require_config 'CONFIG_FRAMEBUFFER_CONSOLE=y'
require_config 'CONFIG_FB_SIMPLE=y'
require_config 'CONFIG_USB_MTU3_GADGET=y'
require_config 'CONFIG_USB_ETH_RNDIS=y'
require_config 'CONFIG_CMDLINE="console=tty0 console=ttyS0,921600n8 earlycon maxcpus=1 nokaslr ignore_loglevel loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 g_ether.dev_addr=42:00:15:19:82:01 g_ether.host_addr=42:00:15:19:82:00 g_ether.iManufacturer=gemini-pda-mainline g_ether.iProduct=Gemini-L-Observability g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L clk_ignore_unused"'

readonly EXPECTED_J_IMAGE_SHA256=61d571cbc6853fb2587eabcb96c1f778bf8731034feb0c0fad2a8325a383e2aa
readonly EXPECTED_J_IMAGE_GZ_SHA256=fb86a201a4427e71368ea14532213ae4cad104452f28448206fca928d255e318
readonly EXPECTED_L_IMAGE_SHA256=91f0ba20a161afd379aa483ef5de2b4d66ff495a23614beaaba1530f459ad2a3
readonly EXPECTED_L_IMAGE_GZ_SHA256=0c0d0e22c78b5b0d89b7a7363be55850b3f3474d3b4e7f922946747efbe164d3
readonly EXPECTED_CONFIG_SHA256=5a0c442c67b64cbabd4d030c93d50837bfc93e34d8878b413805457bfcd8e7cd
readonly EXPECTED_BASE_DTB_SHA256=47a29436e85b277b39fc9b85147e78a4882ce68f3fc17e4acf18ba5b75815d8f
readonly EXPECTED_CANDIDATE_DTB_SHA256=73a0c1913beaf41473accfcc6765407ffe11acc56c6ec0ff3a787abc29f00cae
readonly EXPECTED_INITRAMFS_SHA256=52dd9145b3d85d8f73990f5798b494293aab17d86a066f79f33274207986de32
image_gz_sha256="$(sha256sum "$image_gz" | awk '{print $1}')"
image_sha256="$(sha256sum "$image" | awk '{print $1}')"
build_json_sha256="$(sha256sum "$build_json" | awk '{print $1}')"
[[ "$image_sha256" != "$EXPECTED_J_IMAGE_SHA256" ]] || \
	die "observability Image is unchanged from Candidate J"
[[ "$image_gz_sha256" != "$EXPECTED_J_IMAGE_GZ_SHA256" ]] || \
	die "observability Image.gz is unchanged from Candidate J"
[[ "$image_sha256" == "$EXPECTED_L_IMAGE_SHA256" ]] || \
	die "Candidate L Image is not pinned"
[[ "$image_gz_sha256" == "$EXPECTED_L_IMAGE_GZ_SHA256" ]] || \
	die "Candidate L Image.gz is not pinned"
[[ "$resolved_config_sha256" == "$EXPECTED_CONFIG_SHA256" ]] || \
	die "observability resolved config is not pinned"
base_dtb_sha256="$(sha256sum "$base_dtb" | awk '{print $1}')"
[[ "$base_dtb_sha256" == "$EXPECTED_BASE_DTB_SHA256" ]] || \
	die "observability base DTB is not pinned"

mkdir -p "$(dirname -- "$output")"
staging="$(mktemp -d "$(dirname -- "$output")/.${package_id}-candidate-L.XXXXXX")"
cleanup() {
	[[ ! -d "$staging" ]] || rm -rf "$staging"
}
trap cleanup EXIT

snapshot_dir="${staging}/.validated-package-inputs"
mkdir "$snapshot_dir"
install -m 0600 "$image" "${snapshot_dir}/Image"
install -m 0600 "$image_gz" "${snapshot_dir}/Image.gz"
install -m 0600 "$base_dtb" "${snapshot_dir}/mt6797-gemini-pda.dtb"
install -m 0600 "$config" "${snapshot_dir}/kernel.config"
install -m 0600 "$build_json" "${snapshot_dir}/build.json"
[[ "$(sha256sum "${snapshot_dir}/Image" | awk '{print $1}')" == "$image_sha256" ]] || \
	die "validated Image changed while it was being snapshotted"
[[ "$(sha256sum "${snapshot_dir}/Image.gz" | awk '{print $1}')" == "$image_gz_sha256" ]] || \
	die "validated Image.gz changed while it was being snapshotted"
[[ "$(sha256sum "${snapshot_dir}/mt6797-gemini-pda.dtb" | awk '{print $1}')" == \
	"$base_dtb_sha256" ]] || die "validated base DTB changed while it was being snapshotted"
[[ "$(sha256sum "${snapshot_dir}/kernel.config" | awk '{print $1}')" == \
	"$resolved_config_sha256" ]] || die "validated config changed while it was being snapshotted"
[[ "$(sha256sum "${snapshot_dir}/build.json" | awk '{print $1}')" == \
	"$build_json_sha256" ]] || die "validated build provenance changed while it was being snapshotted"
image="${snapshot_dir}/Image"
image_gz="${snapshot_dir}/Image.gz"
base_dtb="${snapshot_dir}/mt6797-gemini-pda.dtb"
config="${snapshot_dir}/kernel.config"
build_json="${snapshot_dir}/build.json"

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

candidate_dtb="${staging}/mt6797-gemini-pda-lk-observability.dtb"
candidate_initramfs="${staging}/gemini-lk-observability-initramfs.img"
candidate="${staging}/gemini-lk-observability.boot.img"
"$artifact_validator" "$package" >"${staging}/package-validation.txt"
normalize_log "${staging}/package-validation.txt"
"$dtb_builder" --base "$base_dtb" --output "$candidate_dtb" \
	>"${staging}/dtb-validation.txt"
normalize_log "${staging}/dtb-validation.txt"
candidate_dtb_sha256="$(sha256sum "$candidate_dtb" | awk '{print $1}')"
[[ "$candidate_dtb_sha256" == "$EXPECTED_CANDIDATE_DTB_SHA256" ]] || \
	die "Candidate L transformed DTB is not pinned"
"$init_contract_validator" --init "$init_source" --usb-report "$report_source" \
	>"${staging}/init-contract.txt"
normalize_log "${staging}/init-contract.txt"
"$initramfs_builder" --output "$candidate_initramfs" --busybox "$busybox" \
	--source-date-epoch "$source_date_epoch" >"${staging}/initramfs-build.txt"
normalize_log "${staging}/initramfs-build.txt"
candidate_initramfs_sha256="$(sha256sum "$candidate_initramfs" | awk '{print $1}')"
[[ "$candidate_initramfs_sha256" == "$EXPECTED_INITRAMFS_SHA256" ]] || \
	die "Candidate L initramfs is not pinned"

bootopt='bootopt=64S3,32N2,64N2'
python3 "$serializer" \
	--kernel "$image_gz" \
	--ramdisk "$candidate_initramfs" \
	--dtb "$candidate_dtb" \
	--output "$candidate" \
	--name gemini-obs-L \
	--cmdline "$bootopt" \
	--kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 \
	--tags-addr 0x44000000 \
	--lk-android8 >"${staging}/serializer.txt"
normalize_log "${staging}/serializer.txt"
python3 "$analyzer" --validate-lk \
	--expected-image-gz "$image_gz" \
	--expected-ramdisk "$candidate_initramfs" \
	--expected-dtb "$candidate_dtb" \
	--expected-name gemini-obs-L \
	--expected-cmdline "$bootopt" \
	"$candidate" \
	>"${staging}/analysis.txt"
normalize_log "${staging}/analysis.txt"

readonly BOOT2_CAPACITY=16777216
readonly EXPECTED_CANDIDATE_SIZE=6522880
readonly EXPECTED_CANDIDATE_SHA256=5291832296106d36bc919671960b6150e530467057540a195bcf59e582ebb4c9
candidate_size="$(wc -c <"$candidate")"
[[ "$candidate_size" =~ ^[0-9]+$ && "$candidate_size" -le "$BOOT2_CAPACITY" ]] || \
	die "Candidate L does not fit the known 16 MiB boot2 partition"
candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
[[ "$candidate_size" == "$EXPECTED_CANDIDATE_SIZE" ]] || \
	die "Candidate L size is not pinned"
[[ "$candidate_sha256" == "$EXPECTED_CANDIDATE_SHA256" ]] || \
	die "Candidate L image is not pinned"
install -m 0600 "$build_json" "${staging}/source-build.json"

{
	printf 'experiment=2026-07-17-uart-pstore-observability\n'
	printf 'candidate_label=L\n'
	printf 'package=%s\n' "$package_id"
	printf 'build_profile=observability\n'
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'repo_status_sha256=%s\n' "$repo_status_sha256"
	printf 'source_date_epoch=%s\n' "$source_date_epoch"
	printf 'source_sha256=%s\n' "$source_sha256"
	printf 'patchset_sha256=%s\n' "$patchset_sha256"
	printf 'config_inputs_sha256=%s\n' "$config_inputs_sha256"
	printf 'config_sha256=%s\n' "$resolved_config_sha256"
	printf 'image_sha256=%s\n' "$image_sha256"
	printf 'image_gz_sha256=%s\n' "$image_gz_sha256"
	printf 'rejected_unchanged_candidate_j_image_sha256=%s\n' "$EXPECTED_J_IMAGE_SHA256"
	printf 'rejected_unchanged_candidate_j_image_gz_sha256=%s\n' "$EXPECTED_J_IMAGE_GZ_SHA256"
	printf 'base_dtb_sha256=%s\n' "$base_dtb_sha256"
	printf 'candidate_dtb_sha256=%s\n' "$candidate_dtb_sha256"
	printf 'candidate_initramfs_sha256=%s\n' "$candidate_initramfs_sha256"
	printf 'candidate_size=%s\n' "$candidate_size"
	printf 'candidate_sha256=%s\n' "$candidate_sha256"
	printf 'boot2_capacity=%s\n' "$BOOT2_CAPACITY"
	printf 'kernel_addr=0x40200000\nramdisk_addr=0x45000000\n'
	printf 'second_addr=0x40f00000\ntags_addr=0x44000000\n'
	printf 'header_name=gemini-obs-L\nheader_cmdline=%s\n' "$bootopt"
	for input in \
		"$current_manifest" "$current_series" "$candidate_builder" \
		"$artifact_validator" "$dtb_builder" "$dtb_validator" \
		"$initramfs_builder" "$init_contract_validator" \
		"$ramoops_layout_validator" "$ramoops_layout_result" \
		"$ramoops_live_result" \
		"$serializer" "$analyzer" "$init_source" "$report_source" "$busybox"; do
		printf 'input_sha256[%s]=%s\n' \
			"${input#"$repo_root"/}" "$(sha256sum "$input" | awk '{print $1}')"
	done
	for relative in "${fragments[@]}"; do
		printf 'input_sha256[%s]=%s\n' \
			"$relative" "$(sha256sum "${repo_root}/${relative}" | awk '{print $1}')"
	done
	printf 'kernel_deltas=UART0-GPIO97-98,ramoops-pstore,MT6797-TOPRGU-auto-restart\n'
	printf 'uart0_expected_pins=GPIO97-RX,GPIO98-TX\n'
	printf 'source_and_live_binary_validated_recovery_hypothesis=kernel-console-to-Gemian-primary-console-ramoops\n'
	printf 'pmsg0=frontend-disabled-no-payload-writes;backend-header-initialized\n'
	printf 'bounded_reset=one-handoff-ping-then-direct-TOPRGU-watchdog-expiry,timeout-31s,failure-boundary-40s\n'
	printf 'simplefb_handoff=retained-with-DISP_PWM-and-MM-root-clocks\n'
	printf 'native_display_driver_test=no\n'
	printf 'usb_gadget=bonus-only\n'
	printf 'storage_access=none\npersistent_write=ramoops-only\n'
	printf 'build_hardware_write=none\nflash=none\n'
	printf 'runtime_result=not-tested\n'
	printf '\n[parser]\n'
	cat "${staging}/analysis.txt"
} >"${staging}/provenance.txt"

rm -rf "$snapshot_dir"

(
	cd "$staging"
	find . -type f ! -path ./SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"${staging}/SHA256SUMS"
(
	cd "$staging"
	sha256sum --check SHA256SUMS >/dev/null
)
chmod 0600 "${staging}"/*
mv "$staging" "$output"
staging=
trap - EXIT

printf 'validation=uart-pstore-observability-candidate\n'
printf 'candidate_label=L\n'
printf 'package=%s\n' "$package_id"
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-lk-observability.boot.img\n' "$output"
printf 'candidate_sha256=%s\n' "$candidate_sha256"
printf 'candidate_size=%s\n' "$candidate_size"
printf 'kernel_payload_changed_from_candidate_J=yes\n'
printf 'kernel_deltas=UART0-GPIO97-98,ramoops-pstore,MT6797-TOPRGU-auto-restart\n'
printf 'storage_access=none\nbuild_hardware_write=none\nflash=none\n'
printf 'runtime_result=not-tested\n'
