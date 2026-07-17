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
usage: build-screen-marker-candidate.sh --package DIR [--output DIR]
       [--source-date-epoch N]

Rebuild exact timed-reboot candidate D, then create a non-flashing Android v0
variant with only an allowlisted simplefb DT delta and a bounded framebuffer
marker initramfs. This command has no device, partition, or flashing interface.
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
[[ "$source_date_epoch" == 0 ]] || \
	die "exact candidate D is reproducible only with source-date-epoch 0"
for command in awk cmp cpio find git gzip jq python3 sha256sum sort; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
package_id="$(basename -- "$package")"
if [[ -z "$output" ]]; then
	output="${HOME}/artifacts/boot-candidates/${package_id}-screen-marker-E"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite $output"

timed_builder="${repo_root}/experiments/2026-07-16-timed-reboot-diagnostic/scripts/build-timed-reboot-candidate.sh"
dtb_builder="${script_dir}/build-screen-marker-dtb.sh"
initramfs_builder="${script_dir}/build-initramfs.sh"
initramfs_validator="${script_dir}/validate-initramfs-delta.sh"
boot_validator="${script_dir}/validate-boot-delta.py"
marker_generator="${script_dir}/generate-screen-marker.py"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
dtb_validator="${repo_root}/experiments/2026-07-16-lk-handoff-alignment/scripts/validate-lk-compatible-dtb.py"
mandatory_overlay="${repo_root}/experiments/2026-07-16-lk-handoff-alignment/dts/lk-handoff.dtso"
usb_overlay="${repo_root}/experiments/2026-07-16-usb-gadget-diagnostic/dts/usb-gadget.dtso"
simplefb_overlay="${repo_root}/experiments/2026-07-16-lk-handoff-alignment/dts/lk-simplefb.dtso"
candidate_builder="${script_dir}/build-screen-marker-candidate.sh"
init_source="${experiment_dir}/initramfs/init"
busybox=/usr/bin/busybox
for input in \
	"$timed_builder" "$dtb_builder" "$initramfs_builder" \
	"$initramfs_validator" "$boot_validator" "$marker_generator" \
	"$serializer" "$analyzer" "$dtb_validator" "$mandatory_overlay" \
	"$usb_overlay" "$simplefb_overlay" "$candidate_builder" "$init_source" \
	"$busybox"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

image_gz="${package}/Image.gz"
base_dtb="${package}/dtbs/mediatek/mt6797-gemini-pda.dtb"
build_json="${package}/provenance/build.json"
for input in "$image_gz" "$base_dtb" "$build_json"; do
	[[ -s "$input" ]] || die "required package input is missing: $input"
done

readonly EXPECTED_BASELINE_CANDIDATE_SHA256=61fb961a8de48a7e0a9acf83447b90cc7012b741a10b0707cb7e73d33e8081c8
readonly EXPECTED_BASELINE_INITRAMFS_SHA256=8a63939caf76473ad8d688e923155d2b9800bf25cd2017c36acafb08a11bb71b
readonly EXPECTED_BASELINE_DTB_SHA256=5717a8c2f3f4f02533fae4dad8c9f9137f0f78cb0986fd6908a74309722e7db4

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.screen-marker-work.XXXXXX")"
staging="$(mktemp -d "$(dirname -- "$output")/.screen-marker-output.XXXXXX")"
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

# Reconstruct the exact hardware-tested payload before deriving this candidate.
baseline_dir="${workdir}/candidate-D"
"$timed_builder" --package "$package" --output "$baseline_dir" \
	--source-date-epoch "$source_date_epoch" >"${staging}/baseline-build.txt"
normalize_log "${staging}/baseline-build.txt"
(
	cd "$baseline_dir"
	sha256sum --check SHA256SUMS >/dev/null
)

baseline_candidate="${baseline_dir}/gemini-lk-rebootdiag.boot.img"
baseline_initramfs="${baseline_dir}/gemini-lk-rebootdiag-initramfs.img"
baseline_dtb="${baseline_dir}/mt6797-gemini-pda-lk-usbdiag.dtb"
[[ "$(sha256sum "$baseline_candidate" | awk '{print $1}')" == "$EXPECTED_BASELINE_CANDIDATE_SHA256" ]] || \
	die "rebuilt baseline candidate is not exact candidate D"
[[ "$(sha256sum "$baseline_initramfs" | awk '{print $1}')" == "$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || \
	die "rebuilt baseline initramfs is not exact candidate D"
[[ "$(sha256sum "$baseline_dtb" | awk '{print $1}')" == "$EXPECTED_BASELINE_DTB_SHA256" ]] || \
	die "rebuilt baseline DTB is not exact candidate D"

candidate_dtb="${staging}/mt6797-gemini-pda-lk-screen-marker.dtb"
candidate_initramfs="${staging}/gemini-lk-screen-marker-initramfs.img"
candidate="${staging}/gemini-lk-screen-marker.boot.img"

"$dtb_builder" --base "$base_dtb" --output "$candidate_dtb" \
	>"${staging}/dtb-validation.txt"
normalize_log "${staging}/dtb-validation.txt"
"$initramfs_builder" --output "$candidate_initramfs" --busybox "$busybox" \
	--source-date-epoch "$source_date_epoch" >"${staging}/initramfs-build.txt"
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
	--baseline-dtb "$baseline_dtb" \
	--candidate-dtb "$candidate_dtb" \
	--baseline-ramdisk "$baseline_initramfs" \
	--candidate-ramdisk "$candidate_initramfs" \
	--expected-baseline-sha256 "$EXPECTED_BASELINE_CANDIDATE_SHA256" \
	>"${staging}/boot-delta.txt"
normalize_log "${staging}/boot-delta.txt"

install -m 0600 "$build_json" "${staging}/source-build.json"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
repo_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
repo_status_sha256="$(printf '%s\n' "$repo_status" | sha256sum | awk '{print $1}')"
{
	printf 'experiment=2026-07-16-screen-marker-diagnostic\n'
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
		"$timed_builder" "$dtb_builder" "$initramfs_builder" \
		"$initramfs_validator" "$boot_validator" "$marker_generator" \
		"$serializer" "$analyzer" "$dtb_validator" "$mandatory_overlay" \
		"$usb_overlay" "$simplefb_overlay" "$candidate_builder" "$init_source" \
		"$busybox"; do
		printf 'input_sha256[%s]=%s\n' \
			"${input#"$repo_root"/}" "$(sha256sum "$input" | awk '{print $1}')"
	done
	for tool in cpio gzip; do
		tool_path="$(command -v "$tool")"
		printf 'tool_sha256[%s]=%s\n' \
			"$tool" "$(sha256sum "$tool_path" | awk '{print $1}')"
	done
	printf 'dt_delta=allowlisted-simple-framebuffer-only-over-candidate-D-dtb\n'
	printf 'initramfs_delta=tracked-init-plus-marker-and-dd-wc-links\n'
	printf 'framebuffer_base=0x7dfb0000\n'
	printf 'framebuffer_reservation_size=0x1f90000\n'
	printf 'framebuffer_write_bytes=0x8f7000\n'
	printf 'framebuffer_format=a8r8g8b8\n'
	printf 'visible_pattern=8-horizontal-bands-opaque-white-dark-gray\n'
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

printf 'validation=screen-marker-diagnostic-candidate\n'
printf 'package=%s\n' "$package_id"
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-lk-screen-marker.boot.img\n' "$output"
printf 'candidate_sha256=%s\n' "$(sha256sum "$output/gemini-lk-screen-marker.boot.img" | awk '{print $1}')"
printf 'framebuffer_write_bytes=9400320\n'
printf 'storage_access=none\n'
printf 'build_hardware_write=none\nflash=none\n'
printf 'runtime_result=not-tested\n'
