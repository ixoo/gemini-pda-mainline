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
usage: build-clock-retention-candidate.sh --package DIR [--output DIR]
       [--source-date-epoch N]

Rebuild exact Candidate E, then create non-flashing Candidate F with the same
Image.gz, initramfs, marker, framebuffer geometry, and Android-v0 contract.
The sole runtime payload delta is one simplefb CLK_INFRA_DISP_PWM reference.
This command has no device, partition, or flashing interface.
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
[[ -n "$package" ]] || die "--package is required; implicit package selection is forbidden"
[[ -d "$package" ]] || die "package does not exist: $package"
[[ "$source_date_epoch" =~ ^[0-9]+$ ]] || die "epoch must be a non-negative integer"
[[ "$source_date_epoch" == 0 ]] || die "exact Candidate E requires source-date-epoch 0"
for command in awk cmp find git jq python3 sha256sum sort; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
package_id="$(basename -- "$package")"
if [[ -z "$output" ]]; then
	output="${HOME}/artifacts/boot-candidates/${package_id}-screen-clock-retention-F"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite $output"

baseline_builder="${repo_root}/experiments/2026-07-16-screen-marker-diagnostic/scripts/build-screen-marker-candidate.sh"
dtb_builder="${script_dir}/build-clock-retention-dtb.sh"
dtb_validator="${script_dir}/validate-simplefb-clock-delta.py"
boot_validator="${repo_root}/experiments/2026-07-16-screen-marker-diagnostic/scripts/validate-boot-delta.py"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
candidate_builder="${script_dir}/build-clock-retention-candidate.sh"
for input in \
	"$baseline_builder" "$dtb_builder" "$dtb_validator" "$boot_validator" \
	"$serializer" "$analyzer" "$candidate_builder"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

image_gz="${package}/Image.gz"
base_dtb="${package}/dtbs/mediatek/mt6797-gemini-pda.dtb"
build_json="${package}/provenance/build.json"
for input in "$image_gz" "$base_dtb" "$build_json"; do
	[[ -s "$input" ]] || die "required package input is missing: $input"
done

readonly EXPECTED_BASELINE_CANDIDATE_SHA256=08845b5c3985a8bcba569d3009889bbfe210f942d1cef23b798f5fff5c2cb253
readonly EXPECTED_BASELINE_INITRAMFS_SHA256=1c76b34ea58956ffd8b97a640b76788b9f7e1ab92204a9881ad031bd7fe6c72c
readonly EXPECTED_BASELINE_DTB_SHA256=cd41adc3f38b2f94b69ca69a27f61ab2b3ff5dcbcf7094de2f250a341c726389

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.screen-clock-work.XXXXXX")"
staging="$(mktemp -d "$(dirname -- "$output")/.screen-clock-output.XXXXXX")"
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
		value=${value//"$package"/@PACKAGE@}
		value=${value//"$repo_root"/@REPOSITORY@}
		printf '%s\n' "$value"
	done <"$log" >"$normalized"
	mv "$normalized" "$log"
}

baseline_dir="${workdir}/candidate-E"
"$baseline_builder" --package "$package" --output "$baseline_dir" \
	--source-date-epoch "$source_date_epoch" >"${staging}/baseline-build.txt"
normalize_log "${staging}/baseline-build.txt"
(
	cd "$baseline_dir"
	sha256sum --check SHA256SUMS >/dev/null
)

baseline_candidate="${baseline_dir}/gemini-lk-screen-marker.boot.img"
baseline_initramfs="${baseline_dir}/gemini-lk-screen-marker-initramfs.img"
baseline_dtb="${baseline_dir}/mt6797-gemini-pda-lk-screen-marker.dtb"
[[ "$(sha256sum "$baseline_candidate" | awk '{print $1}')" == "$EXPECTED_BASELINE_CANDIDATE_SHA256" ]] || \
	die "rebuilt baseline candidate is not exact Candidate E"
[[ "$(sha256sum "$baseline_initramfs" | awk '{print $1}')" == "$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || \
	die "rebuilt baseline initramfs is not exact Candidate E"
[[ "$(sha256sum "$baseline_dtb" | awk '{print $1}')" == "$EXPECTED_BASELINE_DTB_SHA256" ]] || \
	die "rebuilt baseline DTB is not exact Candidate E"

candidate_dtb="${staging}/mt6797-gemini-pda-lk-screen-clock.dtb"
candidate_initramfs="${staging}/gemini-lk-screen-clock-initramfs.img"
candidate="${staging}/gemini-lk-screen-clock.boot.img"

"$dtb_builder" --baseline "$baseline_dtb" --output "$candidate_dtb" \
	>"${staging}/dtb-validation.txt"
normalize_log "${staging}/dtb-validation.txt"
install -m 0600 "$baseline_initramfs" "$candidate_initramfs"
cmp -s "$baseline_initramfs" "$candidate_initramfs" || \
	die "candidate initramfs differs from exact Candidate E"

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
python3 "$analyzer" --validate-lk --expected-dtb "$candidate_dtb" "$candidate" \
	>"${staging}/analysis.txt"
normalize_log "${staging}/analysis.txt"
python3 "$boot_validator" \
	--baseline "$baseline_candidate" \
	--candidate "$candidate" \
	--image-gz "$image_gz" \
	--baseline-dtb "$baseline_dtb" \
	--candidate-dtb "$candidate_dtb" \
	--baseline-ramdisk "$baseline_initramfs" \
	--candidate-ramdisk "$candidate_initramfs" \
	--expected-baseline-sha256 "$EXPECTED_BASELINE_CANDIDATE_SHA256" \
	--same-ramdisk >"${staging}/boot-delta.txt"
normalize_log "${staging}/boot-delta.txt"

install -m 0600 "$build_json" "${staging}/source-build.json"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
repo_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
repo_status_sha256="$(printf '%s\n' "$repo_status" | sha256sum | awk '{print $1}')"
{
	printf 'experiment=2026-07-16-screen-clock-retention-diagnostic\n'
	printf 'candidate_label=F\n'
	printf 'package=%s\n' "$package_id"
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'repo_status_sha256=%s\n' "$repo_status_sha256"
	printf 'source_date_epoch=%s\n' "$source_date_epoch"
	printf 'baseline_candidate_sha256=%s\n' "$EXPECTED_BASELINE_CANDIDATE_SHA256"
	printf 'baseline_initramfs_sha256=%s\n' "$EXPECTED_BASELINE_INITRAMFS_SHA256"
	printf 'baseline_dtb_sha256=%s\n' "$EXPECTED_BASELINE_DTB_SHA256"
	printf 'kernel_addr=0x40200000\nramdisk_addr=0x45000000\n'
	printf 'second_addr=0x40f00000\ntags_addr=0x44000000\n'
	printf 'header_name=gemini-usbdiag\nheader_cmdline=%s\n' "$bootopt"
	printf 'image_gz_sha256=%s\n' "$(sha256sum "$image_gz" | awk '{print $1}')"
	printf 'base_dtb_sha256=%s\n' "$(sha256sum "$base_dtb" | awk '{print $1}')"
	printf 'candidate_dtb_sha256=%s\n' "$(sha256sum "$candidate_dtb" | awk '{print $1}')"
	printf 'candidate_initramfs_sha256=%s\n' "$(sha256sum "$candidate_initramfs" | awk '{print $1}')"
	printf 'candidate_sha256=%s\n' "$(sha256sum "$candidate" | awk '{print $1}')"
	for input in \
		"$baseline_builder" "$dtb_builder" "$dtb_validator" "$boot_validator" \
		"$serializer" "$analyzer" "$candidate_builder"; do
		printf 'input_sha256[%s]=%s\n' \
			"${input#"$repo_root"/}" "$(sha256sum "$input" | awk '{print $1}')"
	done
	for tool in fdtget fdtput; do
		tool_path="$(command -v "$tool")"
		printf 'tool_sha256[%s]=%s\n' \
			"$tool" "$(sha256sum "$tool_path" | awk '{print $1}')"
	done
	printf 'single_runtime_delta=simplefb-clocks-CLK_INFRA_DISP_PWM\n'
	printf 'clock_provider_path=/syscon@10001000\n'
	printf 'clock_provider_resolution=path-derived-phandle-not-hard-coded\n'
	printf 'clock_symbol=CLK_INFRA_DISP_PWM\nclock_id=45\n'
	printf 'unchanged_image_gz=yes\n'
	printf 'unchanged_initramfs=yes\n'
	printf 'unchanged_framebuffer_geometry=yes\n'
	printf 'unchanged_marker=yes\n'
	printf 'framebuffer_base=0x7dfb0000\n'
	printf 'framebuffer_write_bytes=0x8f7000\n'
	printf 'runtime_usb_userspace=disabled\n'
	printf 'runtime_reboot_request=none\n'
	printf 'storage_access=none\n'
	printf 'persistent_write=none\n'
	printf 'runtime_framebuffer_write=yes\n'
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

printf 'validation=screen-clock-retention-diagnostic-candidate\n'
printf 'package=%s\n' "$package_id"
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-lk-screen-clock.boot.img\n' "$output"
printf 'candidate_sha256=%s\n' "$(sha256sum "$output/gemini-lk-screen-clock.boot.img" | awk '{print $1}')"
printf 'single_runtime_delta=simplefb-clocks-CLK_INFRA_DISP_PWM\n'
printf 'storage_access=none\n'
printf 'build_hardware_write=none\nflash=none\n'
printf 'runtime_result=not-tested\n'
