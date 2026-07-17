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
usage: build-fbcon-newline-boundary-candidate.sh --baseline-package DIR
       --package DIR [--output DIR] [--source-date-epoch N]

Reconstruct exact Candidate J, then create non-flashing Candidate K with its
Image.gz and appended DTB byte-for-byte unchanged. Only initramfs /init changes.
EOF
}

baseline_package=
package=
output=
source_date_epoch=${SOURCE_DATE_EPOCH:-0}
while (($#)); do
	case "$1" in
		--baseline-package)
			(($# >= 2)) || die "--baseline-package requires DIR"
			baseline_package=$2
			shift 2
			;;
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
[[ -n "$baseline_package" && -d "$baseline_package" ]] || \
	die "--baseline-package must name the exact usbdiag package"
[[ -n "$package" && -d "$package" ]] || \
	die "--package must name the exact usbdiag-clkignore package"
[[ "$source_date_epoch" =~ ^[0-9]+$ && "$source_date_epoch" == 0 ]] || \
	die "exact Candidate J reconstruction requires source-date-epoch zero"
for command in awk cmp find git install python3 sha256sum sort xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
baseline_package="$(cd -- "$baseline_package" && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
baseline_package_id="$(basename -- "$baseline_package")"
package_id="$(basename -- "$package")"
if [[ -z "$output" ]]; then
	output="${HOME}/artifacts/boot-candidates/${package_id}-candidate-K"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite $output"

j_builder="${repo_root}/experiments/2026-07-17-clk-ignore-unused-diagnostic/scripts/build-clk-ignore-unused-candidate.sh"
initramfs_builder="${script_dir}/build-initramfs.sh"
initramfs_validator="${script_dir}/validate-initramfs-delta.sh"
contract_validator="${script_dir}/validate-init-contract.sh"
boot_validator="${script_dir}/validate-boot-delta.py"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
candidate_builder="${script_dir}/build-fbcon-newline-boundary-candidate.sh"
init_source="${experiment_dir}/initramfs/init"
for input in \
	"$j_builder" "$initramfs_builder" "$initramfs_validator" \
	"$contract_validator" "$boot_validator" "$serializer" "$analyzer" \
	"$candidate_builder" "$init_source"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

readonly EXPECTED_BASELINE_PACKAGE=linux-7.1.3-gemini-usbdiag-3d92a7e9-fdf1d345
readonly EXPECTED_PACKAGE=linux-7.1.3-gemini-usbdiag-clkignore-3d92a7e9-d1224166
readonly EXPECTED_J_BOOT_SHA256=6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4
readonly EXPECTED_J_IMAGE_GZ_SHA256=fb86a201a4427e71368ea14532213ae4cad104452f28448206fca928d255e318
readonly EXPECTED_J_DTB_SHA256=2054f0affec1ed5edff6b6a7de2a5d97102145c35fd335b4c0fd834571918a34
readonly EXPECTED_J_INITRAMFS_SHA256=85059d3128e643deaafc3989c745ed21ec94ec5f24f5002839e0d080d13dfe85
readonly EXPECTED_K_INITRAMFS_SHA256=c6356f895579b8d0cac516f3a6618ab70d7d4bc33c8c15cc052a71445607dda8
readonly EXPECTED_K_BOOT_SHA256=83704cde0e3e4ed897990b230a817a1c7618201a6b8a33a86a2e19c8e07a07cb
[[ "$baseline_package_id" == "$EXPECTED_BASELINE_PACKAGE" ]] || \
	die "baseline package is not the pinned Candidate J baseline input"
[[ "$package_id" == "$EXPECTED_PACKAGE" ]] || \
	die "package is not the pinned Candidate J kernel package"

image_gz="${package}/Image.gz"
build_json="${package}/provenance/build.json"
for input in "$image_gz" "$build_json"; do
	[[ -s "$input" ]] || die "required package input is missing: $input"
done
[[ "$(sha256sum "$image_gz" | awk '{print $1}')" == \
	"$EXPECTED_J_IMAGE_GZ_SHA256" ]] || die "package Image.gz is not exact Candidate J"

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.candidate-k-work.XXXXXX")"
staging="$(mktemp -d "$(dirname -- "$output")/.candidate-k-output.XXXXXX")"
cleanup() {
	[[ ! -d "$workdir" ]] || rm -rf "$workdir"
	[[ ! -d "$staging" ]] || rm -rf "$staging"
}
trap cleanup EXIT

normalize_log() {
	local log=$1
	local normalized="${log}.normalized"
	local value
	while IFS= read -r value || [[ -n "$value" ]]; do
		value=${value//"$workdir"/@WORK@}
		value=${value//"$staging"/@OUTPUT@}
		value=${value//"$baseline_package"/@BASELINE_PACKAGE@}
		value=${value//"$package"/@PACKAGE@}
		value=${value//"$repo_root"/@REPOSITORY@}
		printf '%s\n' "$value"
	done <"$log" >"$normalized"
	mv "$normalized" "$log"
}

j_dir="${workdir}/candidate-J"
"$j_builder" \
	--baseline-package "$baseline_package" \
	--package "$package" \
	--output "$j_dir" \
	--source-date-epoch "$source_date_epoch" >"${staging}/baseline-build.txt"
normalize_log "${staging}/baseline-build.txt"
(
	cd "$j_dir"
	sha256sum --check SHA256SUMS >/dev/null
)

j_candidate="${j_dir}/gemini-lk-clk-ignore-unused.boot.img"
j_initramfs="${j_dir}/gemini-lk-clk-ignore-unused-initramfs.img"
j_dtb="${j_dir}/mt6797-gemini-pda-lk-clk-ignore-unused.dtb"
[[ "$(sha256sum "$j_candidate" | awk '{print $1}')" == \
	"$EXPECTED_J_BOOT_SHA256" ]] || die "reconstructed baseline is not exact Candidate J"
[[ "$(sha256sum "$j_initramfs" | awk '{print $1}')" == \
	"$EXPECTED_J_INITRAMFS_SHA256" ]] || die "reconstructed J initramfs is not pinned"
[[ "$(sha256sum "$j_dtb" | awk '{print $1}')" == \
	"$EXPECTED_J_DTB_SHA256" ]] || die "reconstructed J DTB is not pinned"

candidate_dtb="${staging}/mt6797-gemini-pda-lk-newline-boundary.dtb"
candidate_initramfs="${staging}/gemini-lk-newline-boundary-initramfs.img"
candidate="${staging}/gemini-lk-newline-boundary.boot.img"
install -m 0600 "$j_dtb" "$candidate_dtb"
cmp -s "$j_dtb" "$candidate_dtb" || die "Candidate J appended DTB changed"
"$initramfs_builder" \
	--baseline "$j_initramfs" \
	--output "$candidate_initramfs" \
	--source-date-epoch "$source_date_epoch" >"${staging}/initramfs-build.txt"
normalize_log "${staging}/initramfs-build.txt"
"$initramfs_validator" \
	--baseline "$j_initramfs" \
	--candidate "$candidate_initramfs" >"${staging}/initramfs-delta.txt"
normalize_log "${staging}/initramfs-delta.txt"
candidate_initramfs_sha256="$(sha256sum "$candidate_initramfs" | awk '{print $1}')"
[[ "$candidate_initramfs_sha256" == "$EXPECTED_K_INITRAMFS_SHA256" ]] || \
	die "Candidate K initramfs is not pinned"

bootopt='bootopt=64S3,32N2,64N2'
python3 "$serializer" \
	--kernel "$image_gz" \
	--ramdisk "$candidate_initramfs" \
	--dtb "$candidate_dtb" \
	--output "$candidate" \
	--name gemini-usbdiag \
	--cmdline "$bootopt" \
	--kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 \
	--tags-addr 0x44000000 \
	--lk-android8 >"${staging}/serializer.txt"
normalize_log "${staging}/serializer.txt"
candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
[[ "$candidate_sha256" == "$EXPECTED_K_BOOT_SHA256" ]] || \
	die "Candidate K boot image is not pinned"
python3 "$analyzer" --validate-lk --expected-dtb "$candidate_dtb" "$candidate" \
	>"${staging}/analysis.txt"
normalize_log "${staging}/analysis.txt"
python3 "$boot_validator" \
	--baseline "$j_candidate" \
	--candidate "$candidate" \
	--image-gz "$image_gz" \
	--dtb "$candidate_dtb" \
	--baseline-ramdisk "$j_initramfs" \
	--candidate-ramdisk "$candidate_initramfs" \
	--expected-baseline-sha256 "$EXPECTED_J_BOOT_SHA256" \
	--expected-candidate-sha256 "$EXPECTED_K_BOOT_SHA256" \
	--expected-image-gz-sha256 "$EXPECTED_J_IMAGE_GZ_SHA256" \
	--expected-dtb-sha256 "$EXPECTED_J_DTB_SHA256" \
	--expected-baseline-ramdisk-sha256 "$EXPECTED_J_INITRAMFS_SHA256" \
	--expected-candidate-ramdisk-sha256 "$EXPECTED_K_INITRAMFS_SHA256" \
	>"${staging}/boot-delta.txt"
normalize_log "${staging}/boot-delta.txt"

install -m 0600 "$build_json" "${staging}/source-build.json"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
repo_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
repo_status_sha256="$(printf '%s\n' "$repo_status" | sha256sum | awk '{print $1}')"
{
	printf 'experiment=2026-07-17-fbcon-newline-boundary-diagnostic\n'
	printf 'candidate_label=K\n'
	printf 'baseline_package=%s\n' "$baseline_package_id"
	printf 'package=%s\n' "$package_id"
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'repo_status_sha256=%s\n' "$repo_status_sha256"
	printf 'source_date_epoch=%s\n' "$source_date_epoch"
	printf 'baseline_candidate_sha256=%s\n' "$EXPECTED_J_BOOT_SHA256"
	printf 'image_gz_sha256=%s\n' "$EXPECTED_J_IMAGE_GZ_SHA256"
	printf 'candidate_dtb_sha256=%s\n' "$(sha256sum "$candidate_dtb" | awk '{print $1}')"
	printf 'baseline_initramfs_sha256=%s\n' "$EXPECTED_J_INITRAMFS_SHA256"
	printf 'candidate_initramfs_sha256=%s\n' "$candidate_initramfs_sha256"
	printf 'candidate_sha256=%s\n' "$candidate_sha256"
	printf 'kernel_addr=0x40200000\nramdisk_addr=0x45000000\n'
	printf 'second_addr=0x40f00000\ntags_addr=0x44000000\n'
	printf 'header_name=gemini-usbdiag\nheader_cmdline=%s\n' "$bootopt"
	for input in \
		"$j_builder" "$initramfs_builder" "$initramfs_validator" \
		"$contract_validator" "$boot_validator" "$serializer" "$analyzer" \
		"$candidate_builder" "$init_source"; do
		printf 'input_sha256[%s]=%s\n' \
			"${input#"$repo_root"/}" "$(sha256sum "$input" | awk '{print $1}')"
	done
	printf 'single_runtime_delta=initramfs-init-newline-boundary\n'
	printf 'marker=GEMINI_FBCON_BOUNDARY_20260717_K\n'
	printf 'phase1=20x-one-second-fixed-width-leading-cr-no-newline\n'
	printf 'phase2=transition-plus-12x-one-second-newline-terminated\n'
	printf 'final_state=static-hold-no-further-console-writes\n'
	printf 'unchanged_image_gz=yes\nunchanged_appended_dtb=yes\n'
	printf 'unchanged_header_cmdline=yes\nunchanged_framebuffer_geometry=yes\n'
	printf 'tracked_init_forbidden_storage_fbdev_raw_memory_mmio_i2c_reset_watchdog_network_usb_control_access=none\n'
	printf 'tracked_init_persistent_write=none\nbuild_hardware_write=none\nflash=none\n'
	printf 'runtime_result=not-tested\n'
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
rm -rf "$workdir"
workdir=
trap - EXIT

printf 'validation=fbcon-newline-boundary-candidate\n'
printf 'candidate_label=K\n'
printf 'package=%s\n' "$package_id"
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-lk-newline-boundary.boot.img\n' "$output"
printf 'candidate_sha256=%s\n' "$candidate_sha256"
printf 'candidate_initramfs_sha256=%s\n' "$candidate_initramfs_sha256"
printf 'single_runtime_delta=initramfs-init-newline-boundary\n'
printf 'unchanged_image_gz=yes\nunchanged_appended_dtb=yes\n'
printf 'build_raw_block_device_access=none\nbuild_hardware_write=none\nflash=none\n'
printf 'runtime_result=not-tested\n'
