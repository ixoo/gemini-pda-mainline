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
usage: build-clk-ignore-unused-candidate.sh --baseline-package DIR
       --package DIR [--output DIR] [--source-date-epoch N]

Rebuild exact Candidate I from the pinned usbdiag package, then create the
non-flashing Candidate J from the usbdiag-clkignore package. Candidate J keeps
I's DTB, initramfs and Android-header command line byte-for-byte. Its kernel is
rebuilt from an otherwise identical resolved config whose sole delta appends
clk_ignore_unused to forced CONFIG_CMDLINE.
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
[[ -n "$baseline_package" ]] || die "--baseline-package is required"
[[ -n "$package" ]] || die "--package is required"
[[ -d "$baseline_package" ]] || die "baseline package does not exist: $baseline_package"
[[ -d "$package" ]] || die "package does not exist: $package"
[[ "$source_date_epoch" =~ ^[0-9]+$ ]] || die "epoch must be a non-negative integer"
[[ "$source_date_epoch" == 0 ]] || die "exact Candidate I requires source-date-epoch zero"
for command in awk cmp find git install jq python3 sha256sum sort xargs; do
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
	output="${HOME}/artifacts/boot-candidates/${package_id}-candidate-J"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite $output"

baseline_builder="${repo_root}/experiments/2026-07-16-fbcon-refresh-timing-diagnostic/scripts/build-fbcon-refresh-candidate.sh"
artifact_validator="${repo_root}/scripts/validate-kernel-artifact"
package_validator="${script_dir}/validate-package-delta.py"
boot_validator="${script_dir}/validate-boot-delta.py"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
candidate_builder="${script_dir}/build-clk-ignore-unused-candidate.sh"
current_manifest="${repo_root}/kernel/manifest.json"
clk_fragment="${repo_root}/configs/gemini-clk-ignore-unused.fragment"
for input in \
	"$baseline_builder" "$artifact_validator" "$package_validator" \
	"$boot_validator" "$serializer" "$analyzer" "$candidate_builder" \
	"$current_manifest" "$clk_fragment"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

baseline_image="${baseline_package}/Image"
baseline_image_gz="${baseline_package}/Image.gz"
image="${package}/Image"
image_gz="${package}/Image.gz"
build_json="${package}/provenance/build.json"
for input in "$baseline_image" "$baseline_image_gz" "$image" "$image_gz" "$build_json"; do
	[[ -s "$input" ]] || die "required package input is missing: $input"
done

readonly EXPECTED_BASELINE_PACKAGE=linux-7.1.3-gemini-usbdiag-3d92a7e9-fdf1d345
readonly EXPECTED_PACKAGE=linux-7.1.3-gemini-usbdiag-clkignore-3d92a7e9-d1224166
readonly EXPECTED_I_BOOT_SHA256=92e1a870dad1086f83c777b048d4a684d601a42603157929996769a6ab47a01a
readonly EXPECTED_I_DTB_SHA256=2054f0affec1ed5edff6b6a7de2a5d97102145c35fd335b4c0fd834571918a34
readonly EXPECTED_I_INITRAMFS_SHA256=85059d3128e643deaafc3989c745ed21ec94ec5f24f5002839e0d080d13dfe85
readonly EXPECTED_BASELINE_IMAGE_SHA256=19592386018c8fd482a5a17fb2483c983d05fc47d65d056211b36beb668512c7
readonly EXPECTED_BASELINE_IMAGE_GZ_SHA256=3c001a8950939fdf4e15fb5d94f4c8761e461a2e274f103777c4db97da483a3e
readonly EXPECTED_J_IMAGE_SHA256=61d571cbc6853fb2587eabcb96c1f778bf8731034feb0c0fad2a8325a383e2aa
readonly EXPECTED_J_IMAGE_GZ_SHA256=fb86a201a4427e71368ea14532213ae4cad104452f28448206fca928d255e318
readonly EXPECTED_J_CONFIG_SHA256=283570babf78d9299948a35c8133dfa906b04a0c35a2d0d2997309326d607f0d
readonly EXPECTED_J_BOOT_SHA256=6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4
readonly REJECTED_HEADER_ONLY_SHA256=3b87a4f604ab0519290987feec9fdca139d4959b4caa1dbfee9889c4c90d2b6d

[[ "$baseline_package_id" == "$EXPECTED_BASELINE_PACKAGE" ]] || \
	die "baseline package is not the exact Candidate I source package"
[[ "$package_id" == "$EXPECTED_PACKAGE" ]] || \
	die "package is not the pinned usbdiag-clkignore build"

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.clk-ignore-unused-work.XXXXXX")"
staging="$(mktemp -d "$(dirname -- "$output")/.clk-ignore-unused-output.XXXXXX")"
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

"$artifact_validator" "$package" >"${staging}/package-validation.txt"
normalize_log "${staging}/package-validation.txt"
python3 "$package_validator" \
	--baseline-package "$baseline_package" \
	--candidate-package "$package" \
	--current-manifest "$current_manifest" \
	--clk-fragment "$clk_fragment" \
	--expected-baseline-image-sha256 "$EXPECTED_BASELINE_IMAGE_SHA256" \
	--expected-baseline-image-gz-sha256 "$EXPECTED_BASELINE_IMAGE_GZ_SHA256" \
	--expected-candidate-image-sha256 "$EXPECTED_J_IMAGE_SHA256" \
	--expected-candidate-image-gz-sha256 "$EXPECTED_J_IMAGE_GZ_SHA256" \
	--expected-candidate-config-sha256 "$EXPECTED_J_CONFIG_SHA256" \
	>"${staging}/package-delta.txt"
normalize_log "${staging}/package-delta.txt"

baseline_dir="${workdir}/candidate-I"
"$baseline_builder" --package "$baseline_package" --output "$baseline_dir" \
	--source-date-epoch "$source_date_epoch" >"${staging}/baseline-build.txt"
normalize_log "${staging}/baseline-build.txt"
(
	cd "$baseline_dir"
	sha256sum --check SHA256SUMS >/dev/null
)

baseline_candidate="${baseline_dir}/gemini-lk-fbcon-refresh.boot.img"
baseline_initramfs="${baseline_dir}/gemini-lk-fbcon-refresh-initramfs.img"
baseline_dtb="${baseline_dir}/mt6797-gemini-pda-lk-fbcon-refresh.dtb"
[[ "$(sha256sum "$baseline_candidate" | awk '{print $1}')" == \
	"$EXPECTED_I_BOOT_SHA256" ]] || die "rebuilt baseline is not exact Candidate I"
[[ "$(sha256sum "$baseline_initramfs" | awk '{print $1}')" == \
	"$EXPECTED_I_INITRAMFS_SHA256" ]] || die "rebuilt initramfs is not exact Candidate I"
[[ "$(sha256sum "$baseline_dtb" | awk '{print $1}')" == \
	"$EXPECTED_I_DTB_SHA256" ]] || die "rebuilt DTB is not exact Candidate I"

candidate_dtb="${staging}/mt6797-gemini-pda-lk-clk-ignore-unused.dtb"
candidate_initramfs="${staging}/gemini-lk-clk-ignore-unused-initramfs.img"
candidate="${staging}/gemini-lk-clk-ignore-unused.boot.img"
install -m 0600 "$baseline_dtb" "$candidate_dtb"
install -m 0600 "$baseline_initramfs" "$candidate_initramfs"
cmp -s "$baseline_dtb" "$candidate_dtb" || die "Candidate I DTB changed"
cmp -s "$baseline_initramfs" "$candidate_initramfs" || \
	die "Candidate I initramfs changed"

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
[[ "$candidate_sha256" != "$REJECTED_HEADER_ONLY_SHA256" ]] || \
	die "refusing rejected header-only no-op Candidate J"
[[ "$candidate_sha256" == "$EXPECTED_J_BOOT_SHA256" ]] || \
	die "Candidate J boot image is not pinned"
python3 "$analyzer" --validate-lk --expected-dtb "$candidate_dtb" "$candidate" \
	>"${staging}/analysis.txt"
normalize_log "${staging}/analysis.txt"
python3 "$boot_validator" \
	--baseline "$baseline_candidate" \
	--candidate "$candidate" \
	--baseline-image-gz "$baseline_image_gz" \
	--candidate-image-gz "$image_gz" \
	--dtb "$candidate_dtb" \
	--initramfs "$candidate_initramfs" \
	--expected-baseline-sha256 "$EXPECTED_I_BOOT_SHA256" \
	--expected-candidate-sha256 "$EXPECTED_J_BOOT_SHA256" \
	--expected-baseline-image-gz-sha256 "$EXPECTED_BASELINE_IMAGE_GZ_SHA256" \
	--expected-candidate-image-gz-sha256 "$EXPECTED_J_IMAGE_GZ_SHA256" \
	--expected-dtb-sha256 "$EXPECTED_I_DTB_SHA256" \
	--expected-initramfs-sha256 "$EXPECTED_I_INITRAMFS_SHA256" \
	>"${staging}/boot-delta.txt"
normalize_log "${staging}/boot-delta.txt"

install -m 0600 "$build_json" "${staging}/source-build.json"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
repo_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
repo_status_sha256="$(printf '%s\n' "$repo_status" | sha256sum | awk '{print $1}')"
{
	printf 'experiment=2026-07-17-clk-ignore-unused-diagnostic\n'
	printf 'candidate_label=J\n'
	printf 'baseline_package=%s\n' "$baseline_package_id"
	printf 'package=%s\n' "$package_id"
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'repo_status_sha256=%s\n' "$repo_status_sha256"
	printf 'source_date_epoch=%s\n' "$source_date_epoch"
	printf 'baseline_candidate_sha256=%s\n' "$EXPECTED_I_BOOT_SHA256"
	printf 'baseline_image_sha256=%s\n' "$EXPECTED_BASELINE_IMAGE_SHA256"
	printf 'baseline_image_gz_sha256=%s\n' "$EXPECTED_BASELINE_IMAGE_GZ_SHA256"
	printf 'candidate_image_sha256=%s\n' "$EXPECTED_J_IMAGE_SHA256"
	printf 'candidate_image_gz_sha256=%s\n' "$EXPECTED_J_IMAGE_GZ_SHA256"
	printf 'candidate_config_sha256=%s\n' "$EXPECTED_J_CONFIG_SHA256"
	printf 'candidate_dtb_sha256=%s\n' "$EXPECTED_I_DTB_SHA256"
	printf 'candidate_initramfs_sha256=%s\n' "$EXPECTED_I_INITRAMFS_SHA256"
	printf 'candidate_sha256=%s\n' "$candidate_sha256"
	printf 'kernel_addr=0x40200000\nramdisk_addr=0x45000000\n'
	printf 'second_addr=0x40f00000\ntags_addr=0x44000000\n'
	printf 'header_name=gemini-usbdiag\nheader_cmdline=%s\n' "$bootopt"
	for input in \
		"$baseline_builder" "$artifact_validator" "$package_validator" \
		"$boot_validator" "$serializer" "$analyzer" "$candidate_builder" \
		"$current_manifest" "$clk_fragment"; do
		printf 'input_sha256[%s]=%s\n' \
			"${input#"$repo_root"/}" "$(sha256sum "$input" | awk '{print $1}')"
	done
	printf 'single_resolved_config_delta=CONFIG_CMDLINE-append-clk_ignore_unused\n'
	printf 'config_cmdline_force=yes\n'
	printf 'marker=GEMINI_FBCON_REFRESH_20260716_I\n'
	printf 'broad_unused_clock_retention=yes\n'
	printf 'unchanged_header_cmdline=yes\n'
	printf 'unchanged_dtb=yes\n'
	printf 'unchanged_initramfs=yes\n'
	printf 'kernel_payload_changed=yes\n'
	printf 'rejected_header_only_sha256=%s\n' "$REJECTED_HEADER_ONLY_SHA256"
	printf 'rejected_header_only_artifact=no-op-never-export\n'
	printf 'storage_access=none\n'
	printf 'persistent_write=none\n'
	printf 'build_hardware_write=none\nflash=none\n'
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

printf 'validation=compiled-clk-ignore-unused-candidate\n'
printf 'candidate_label=J\n'
printf 'package=%s\n' "$package_id"
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-lk-clk-ignore-unused.boot.img\n' "$output"
printf 'candidate_sha256=%s\n' "$candidate_sha256"
printf 'single_resolved_config_delta=CONFIG_CMDLINE-append-clk_ignore_unused\n'
printf 'unchanged_header_cmdline=yes\n'
printf 'unchanged_dtb=yes\n'
printf 'unchanged_initramfs=yes\n'
printf 'storage_access=none\n'
printf 'build_hardware_write=none\nflash=none\n'
printf 'runtime_result=not-tested\n'
