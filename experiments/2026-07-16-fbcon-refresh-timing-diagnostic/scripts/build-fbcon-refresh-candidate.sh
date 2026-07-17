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
usage: build-fbcon-refresh-candidate.sh --package DIR [--output DIR]
       [--source-date-epoch N]

Rebuild exact Candidate H, then create non-flashing Candidate I with the same
Image.gz, DTB and Android-v0 contract. Only /init changes: it emits a unique
one-second fbcon timing sequence for 60 seconds, then becomes completely quiet.
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
[[ "$source_date_epoch" == 0 ]] || die "exact Candidate H requires source-date-epoch zero"
for command in awk cmp find git install jq python3 sha256sum sort xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
package_id="$(basename -- "$package")"
if [[ -z "$output" ]]; then
	output="${HOME}/artifacts/boot-candidates/${package_id}-fbcon-refresh-I"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite $output"

baseline_builder="${repo_root}/experiments/2026-07-16-simplefb-mm-root-retention/scripts/build-mm-root-candidate.sh"
initramfs_builder="${script_dir}/build-initramfs.sh"
initramfs_validator="${script_dir}/validate-initramfs-delta.sh"
boot_validator="${script_dir}/validate-boot-delta.py"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
candidate_builder="${script_dir}/build-fbcon-refresh-candidate.sh"
init_source="${experiment_dir}/initramfs/init"
for input in \
	"$baseline_builder" "$initramfs_builder" "$initramfs_validator" \
	"$boot_validator" "$serializer" "$analyzer" "$candidate_builder" \
	"$init_source"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

image_gz="${package}/Image.gz"
build_json="${package}/provenance/build.json"
for input in "$image_gz" "$build_json"; do
	[[ -s "$input" ]] || die "required package input is missing: $input"
done

readonly EXPECTED_H_BOOT_SHA256=594a83d4b48ad33688abb3e0c5ffd1914d6027c680d7799322f9379bef8f4b09
readonly EXPECTED_H_DTB_SHA256=2054f0affec1ed5edff6b6a7de2a5d97102145c35fd335b4c0fd834571918a34
readonly EXPECTED_H_INITRAMFS_SHA256=8dc85151bececf297f99b6f22c87316a54d0fa062e29c2c64ad00334b7ad0956
readonly EXPECTED_IMAGE_GZ_SHA256=3c001a8950939fdf4e15fb5d94f4c8761e461a2e274f103777c4db97da483a3e
readonly EXPECTED_I_INITRAMFS_SHA256=85059d3128e643deaafc3989c745ed21ec94ec5f24f5002839e0d080d13dfe85
readonly EXPECTED_I_BOOT_SHA256=92e1a870dad1086f83c777b048d4a684d601a42603157929996769a6ab47a01a
[[ "$(sha256sum "$image_gz" | awk '{print $1}')" == "$EXPECTED_IMAGE_GZ_SHA256" ]] || \
	die "package Image.gz is not the exact Candidate H kernel image"

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.fbcon-refresh-work.XXXXXX")"
staging="$(mktemp -d "$(dirname -- "$output")/.fbcon-refresh-output.XXXXXX")"
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

baseline_dir="${workdir}/candidate-H"
"$baseline_builder" --package "$package" --output "$baseline_dir" \
	--source-date-epoch "$source_date_epoch" >"${staging}/baseline-build.txt"
normalize_log "${staging}/baseline-build.txt"
(
	cd "$baseline_dir"
	sha256sum --check SHA256SUMS >/dev/null
)

baseline_candidate="${baseline_dir}/gemini-lk-mm-root.boot.img"
baseline_initramfs="${baseline_dir}/gemini-lk-mm-root-initramfs.img"
baseline_dtb="${baseline_dir}/mt6797-gemini-pda-lk-mm-root.dtb"
[[ "$(sha256sum "$baseline_candidate" | awk '{print $1}')" == \
	"$EXPECTED_H_BOOT_SHA256" ]] || die "rebuilt baseline is not exact Candidate H"
[[ "$(sha256sum "$baseline_initramfs" | awk '{print $1}')" == \
	"$EXPECTED_H_INITRAMFS_SHA256" ]] || die "rebuilt initramfs is not exact Candidate H"
[[ "$(sha256sum "$baseline_dtb" | awk '{print $1}')" == \
	"$EXPECTED_H_DTB_SHA256" ]] || die "rebuilt DTB is not exact Candidate H"

candidate_dtb="${staging}/mt6797-gemini-pda-lk-fbcon-refresh.dtb"
candidate_initramfs="${staging}/gemini-lk-fbcon-refresh-initramfs.img"
candidate="${staging}/gemini-lk-fbcon-refresh.boot.img"
install -m 0600 "$baseline_dtb" "$candidate_dtb"
cmp -s "$baseline_dtb" "$candidate_dtb" || die "Candidate H DTB changed"
"$initramfs_builder" \
	--baseline "$baseline_initramfs" \
	--output "$candidate_initramfs" \
	--source-date-epoch "$source_date_epoch" >"${staging}/initramfs-build.txt"
normalize_log "${staging}/initramfs-build.txt"
"$initramfs_validator" \
	--baseline "$baseline_initramfs" \
	--candidate "$candidate_initramfs" >"${staging}/initramfs-delta.txt"
normalize_log "${staging}/initramfs-delta.txt"
[[ "$(sha256sum "$candidate_initramfs" | awk '{print $1}')" == \
	"$EXPECTED_I_INITRAMFS_SHA256" ]] || die "Candidate I initramfs is not pinned"

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
	--expected-baseline-sha256 "$EXPECTED_H_BOOT_SHA256" \
	--expected-image-gz-sha256 "$EXPECTED_IMAGE_GZ_SHA256" \
	--expected-dtb-sha256 "$EXPECTED_H_DTB_SHA256" \
	--expected-baseline-ramdisk-sha256 "$EXPECTED_H_INITRAMFS_SHA256" \
	>"${staging}/boot-delta.txt"
normalize_log "${staging}/boot-delta.txt"
[[ "$(sha256sum "$candidate" | awk '{print $1}')" == \
	"$EXPECTED_I_BOOT_SHA256" ]] || die "Candidate I boot image is not pinned"

install -m 0600 "$build_json" "${staging}/source-build.json"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
repo_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
repo_status_sha256="$(printf '%s\n' "$repo_status" | sha256sum | awk '{print $1}')"
{
	printf 'experiment=2026-07-16-fbcon-refresh-timing-diagnostic\n'
	printf 'candidate_label=I\n'
	printf 'package=%s\n' "$package_id"
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'repo_status_sha256=%s\n' "$repo_status_sha256"
	printf 'source_date_epoch=%s\n' "$source_date_epoch"
	printf 'baseline_candidate_sha256=%s\n' "$EXPECTED_H_BOOT_SHA256"
	printf 'baseline_initramfs_sha256=%s\n' "$EXPECTED_H_INITRAMFS_SHA256"
	printf 'baseline_dtb_sha256=%s\n' "$EXPECTED_H_DTB_SHA256"
	printf 'image_gz_sha256=%s\n' "$EXPECTED_IMAGE_GZ_SHA256"
	printf 'kernel_addr=0x40200000\nramdisk_addr=0x45000000\n'
	printf 'second_addr=0x40f00000\ntags_addr=0x44000000\n'
	printf 'header_name=gemini-usbdiag\nheader_cmdline=%s\n' "$bootopt"
	printf 'candidate_dtb_sha256=%s\n' "$(sha256sum "$candidate_dtb" | awk '{print $1}')"
	printf 'candidate_initramfs_sha256=%s\n' "$(sha256sum "$candidate_initramfs" | awk '{print $1}')"
	printf 'candidate_sha256=%s\n' "$(sha256sum "$candidate" | awk '{print $1}')"
	for input in \
		"$baseline_builder" "$initramfs_builder" "$initramfs_validator" \
		"$boot_validator" "$serializer" "$analyzer" "$candidate_builder" \
		"$init_source"; do
		printf 'input_sha256[%s]=%s\n' \
			"${input#"$repo_root"/}" "$(sha256sum "$input" | awk '{print $1}')"
	done
	printf 'single_runtime_delta=initramfs-init-fbcon-refresh-timing\n'
	printf 'marker=GEMINI_FBCON_REFRESH_20260716_I\n'
	printf 'active_refresh_interval_seconds=1\n'
	printf 'active_refresh_duration_seconds=60\n'
	printf 'static_hold_after_seconds=60\n'
	printf 'unchanged_image_gz=yes\n'
	printf 'unchanged_dtb=yes\n'
	printf 'unchanged_framebuffer_geometry=yes\n'
	printf 'raw_framebuffer_access=none\n'
	printf 'runtime_networking=none\n'
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

printf 'validation=fbcon-refresh-timing-candidate\n'
printf 'candidate_label=I\n'
printf 'package=%s\n' "$package_id"
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-lk-fbcon-refresh.boot.img\n' "$output"
printf 'candidate_sha256=%s\n' \
	"$(sha256sum "$output/gemini-lk-fbcon-refresh.boot.img" | awk '{print $1}')"
printf 'single_runtime_delta=initramfs-init-fbcon-refresh-timing\n'
printf 'unchanged_image_gz=yes\n'
printf 'unchanged_dtb=yes\n'
printf 'storage_access=none\n'
printf 'build_hardware_write=none\nflash=none\n'
printf 'runtime_result=not-tested\n'
