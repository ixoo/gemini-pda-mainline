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
usage: build-fbcon-text-candidate.sh --package DIR [--output DIR]
       [--source-date-epoch N]

Rebuild exact Candidate F, then create non-flashing Candidate G with the same
Image.gz, DTB, Android-v0 contract and simplefb clock retention. Only the
initramfs changes: it removes the raw marker write and holds visible fbcon text.
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
[[ -n "$package" ]] || die "--package is required; implicit selection is forbidden"
[[ -d "$package" ]] || die "package does not exist: $package"
[[ "$source_date_epoch" =~ ^[0-9]+$ ]] || die "epoch must be a non-negative integer"
[[ "$source_date_epoch" == 0 ]] || die "exact Candidate F requires source-date-epoch zero"
for command in awk cmp find git jq python3 sha256sum sort; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
package_id="$(basename -- "$package")"
if [[ -z "$output" ]]; then
	output="${HOME}/artifacts/boot-candidates/${package_id}-fbcon-text-G"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite $output"

baseline_builder="${repo_root}/experiments/2026-07-16-screen-clock-retention-diagnostic/scripts/build-clock-retention-candidate.sh"
initramfs_builder="${script_dir}/build-initramfs.sh"
initramfs_validator="${script_dir}/validate-initramfs-delta.sh"
boot_validator="${script_dir}/validate-boot-delta.py"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
candidate_builder="${script_dir}/build-fbcon-text-candidate.sh"
init_source="${experiment_dir}/initramfs/init"
for input in "$baseline_builder" "$initramfs_builder" "$initramfs_validator" \
	"$boot_validator" "$serializer" "$analyzer" "$candidate_builder" \
	"$init_source"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

image_gz="${package}/Image.gz"
build_json="${package}/provenance/build.json"
for input in "$image_gz" "$build_json"; do
	[[ -s "$input" ]] || die "required package input is missing: $input"
done

readonly EXPECTED_BASELINE_CANDIDATE_SHA256=14c1fe4116cd04331fa347502929ef9e60aed08cbc859b99621a5010e263df57
readonly EXPECTED_BASELINE_INITRAMFS_SHA256=1c76b34ea58956ffd8b97a640b76788b9f7e1ab92204a9881ad031bd7fe6c72c
readonly EXPECTED_BASELINE_DTB_SHA256=edcc5da98996cf594661c5c6da08996a6b2bf59f1e46bcbf6b89e9e9aac56abb
readonly EXPECTED_IMAGE_GZ_SHA256=3c001a8950939fdf4e15fb5d94f4c8761e461a2e274f103777c4db97da483a3e
[[ "$(sha256sum "$image_gz" | awk '{print $1}')" == "$EXPECTED_IMAGE_GZ_SHA256" ]] || \
	die "package Image.gz is not the exact Candidate F kernel image"

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.fbcon-text-work.XXXXXX")"
staging="$(mktemp -d "$(dirname -- "$output")/.fbcon-text-output.XXXXXX")"
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

baseline_dir="${workdir}/candidate-F"
"$baseline_builder" --package "$package" --output "$baseline_dir" \
	--source-date-epoch "$source_date_epoch" >"${staging}/baseline-build.txt"
normalize_log "${staging}/baseline-build.txt"
(
	cd "$baseline_dir"
	sha256sum --check SHA256SUMS >/dev/null
)

baseline_candidate="${baseline_dir}/gemini-lk-screen-clock.boot.img"
baseline_initramfs="${baseline_dir}/gemini-lk-screen-clock-initramfs.img"
baseline_dtb="${baseline_dir}/mt6797-gemini-pda-lk-screen-clock.dtb"
[[ "$(sha256sum "$baseline_candidate" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_CANDIDATE_SHA256" ]] || die "rebuilt baseline is not exact Candidate F"
[[ "$(sha256sum "$baseline_initramfs" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || die "rebuilt initramfs is not exact Candidate F"
[[ "$(sha256sum "$baseline_dtb" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_DTB_SHA256" ]] || die "rebuilt DTB is not exact Candidate F"

candidate_dtb="${staging}/mt6797-gemini-pda-lk-fbcon-text.dtb"
candidate_initramfs="${staging}/gemini-lk-fbcon-text-initramfs.img"
candidate="${staging}/gemini-lk-fbcon-text.boot.img"
install -m 0600 "$baseline_dtb" "$candidate_dtb"
cmp -s "$baseline_dtb" "$candidate_dtb" || die "candidate DTB differs from exact F"
"$initramfs_builder" --baseline "$baseline_initramfs" \
	--output "$candidate_initramfs" --source-date-epoch "$source_date_epoch" \
	>"${staging}/initramfs-build.txt"
normalize_log "${staging}/initramfs-build.txt"
"$initramfs_validator" --baseline "$baseline_initramfs" \
	--candidate "$candidate_initramfs" >"${staging}/initramfs-delta.txt"
normalize_log "${staging}/initramfs-delta.txt"

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
	--dtb "$candidate_dtb" \
	--baseline-ramdisk "$baseline_initramfs" \
	--candidate-ramdisk "$candidate_initramfs" \
	--expected-baseline-sha256 "$EXPECTED_BASELINE_CANDIDATE_SHA256" \
	--expected-image-gz-sha256 "$EXPECTED_IMAGE_GZ_SHA256" \
	--expected-dtb-sha256 "$EXPECTED_BASELINE_DTB_SHA256" \
	--expected-baseline-ramdisk-sha256 "$EXPECTED_BASELINE_INITRAMFS_SHA256" \
	>"${staging}/boot-delta.txt"
normalize_log "${staging}/boot-delta.txt"

install -m 0600 "$build_json" "${staging}/source-build.json"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
repo_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
repo_status_sha256="$(printf '%s\n' "$repo_status" | sha256sum | awk '{print $1}')"
{
	printf 'experiment=2026-07-16-fbcon-text-diagnostic\n'
	printf 'candidate_label=G\n'
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
	printf 'candidate_dtb_sha256=%s\n' "$(sha256sum "$candidate_dtb" | awk '{print $1}')"
	printf 'candidate_initramfs_sha256=%s\n' "$(sha256sum "$candidate_initramfs" | awk '{print $1}')"
	printf 'candidate_sha256=%s\n' "$(sha256sum "$candidate" | awk '{print $1}')"
	for input in "$baseline_builder" "$initramfs_builder" "$initramfs_validator" \
		"$boot_validator" "$serializer" "$analyzer" "$candidate_builder" \
		"$init_source"; do
		printf 'input_sha256[%s]=%s\n' "${input#"$repo_root"/}" \
			"$(sha256sum "$input" | awk '{print $1}')"
	done
	printf 'single_runtime_delta=replace-raw-frame-marker-with-fbcon-text-hold\n'
	printf 'unchanged_image_gz=yes\n'
	printf 'unchanged_kernel_segment=yes\n'
	printf 'unchanged_dtb=yes\n'
	printf 'unchanged_simplefb_clock_retention=yes\n'
	printf 'fbcon_rotation_compiled=no\n'
	printf 'expected_console_orientation=sideways\n'
	printf 'heartbeat_interval_seconds=30\n'
	printf 'raw_framebuffer_access=none\n'
	printf 'runtime_usb_userspace=disabled\n'
	printf 'runtime_reboot_request=none\n'
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

printf 'validation=fbcon-text-diagnostic-candidate\n'
printf 'candidate_label=G\n'
printf 'package=%s\n' "$package_id"
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-lk-fbcon-text.boot.img\n' "$output"
printf 'candidate_sha256=%s\n' \
	"$(sha256sum "$output/gemini-lk-fbcon-text.boot.img" | awk '{print $1}')"
printf 'unchanged_kernel_segment=yes\n'
printf 'unchanged_dtb=yes\n'
printf 'raw_framebuffer_access=none\n'
printf 'storage_access=none\n'
printf 'build_hardware_write=none\nflash=none\n'
printf 'runtime_result=not-tested\n'
