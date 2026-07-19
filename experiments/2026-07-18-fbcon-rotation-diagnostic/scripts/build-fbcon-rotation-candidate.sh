#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() {
	printf 'error: %s\n' "$*" >&2
	exit 2
}

usage() {
	cat >&2 <<'EOF'
usage: build-fbcon-rotation-candidate.sh --baseline-package DIR
       --package DIR --baseline DIR [--output DIR]
       [--source-date-epoch N] [--establish-pins]

Build the non-flashing Candidate P from an exact Candidate O artifact and a
kernel package built with the observability-fbcon-rotation profile. Candidate
P changes only the compiled fbcon rotation option and forced command line. It
reuses O's DTB, initramfs, Android header fields, and runtime sequence exactly.

--establish-pins performs all structural validation and prints the candidate
hashes, but deliberately does not publish an artifact. Use it only once from a
clean committed tree, then review and pin its output in this script.
EOF
}

baseline_package=
package=
baseline=
output=
establish_pins=no
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
		--baseline)
			(($# >= 2)) || die "--baseline requires DIR"
			baseline=$2
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
		--establish-pins)
			establish_pins=yes
			shift
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
	die "--baseline-package must name the exact observability package"
[[ -n "$package" && -d "$package" ]] || \
	die "--package must name the rotation-profile package"
[[ -n "$baseline" && -d "$baseline" ]] || \
	die "--baseline must name the exact Candidate O artifact"
[[ "$source_date_epoch" =~ ^[0-9]+$ && "$source_date_epoch" == 0 ]] || \
	die "Candidate P requires source-date-epoch zero"
for command in awk basename chmod cmp dirname find git install jq mkdir mktemp \
	mv python3 rm sha256sum sort uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
repo_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
[[ -z "$repo_status" ]] || \
	die "Candidate P requires a clean repository so repo_revision identifies every input"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
repo_status_sha256="$(printf '%s' "$repo_status" | sha256sum | awk '{print $1}')"

baseline_package="$(cd -- "$baseline_package" && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
baseline="$(cd -- "$baseline" && pwd -P)"
baseline_package_id="$(basename -- "$baseline_package")"
package_id="$(basename -- "$package")"
baseline_id="$(basename -- "$baseline")"
if [[ -z "$output" ]]; then
	output="${HOME}/artifacts/boot-candidates/candidate-P-fbcon-rotation-${repo_revision:0:8}"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite $output"

artifact_validator="${repo_root}/scripts/validate-kernel-artifact"
package_validator="${script_dir}/validate-package-delta.py"
boot_validator="${script_dir}/validate-boot-delta.py"
candidate_builder="${script_dir}/build-fbcon-rotation-candidate.sh"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
current_manifest="${repo_root}/kernel/manifest.json"
rotation_fragment="${repo_root}/configs/gemini-fbcon-rotation.fragment"
for input in "$artifact_validator" "$package_validator" "$boot_validator" \
	"$candidate_builder" "$serializer" "$analyzer" "$current_manifest" \
	"$rotation_fragment"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

baseline_image="${baseline_package}/Image"
baseline_image_gz="${baseline_package}/Image.gz"
image="${package}/Image"
image_gz="${package}/Image.gz"
candidate_config="${package}/kernel.config"
build_json="${package}/provenance/build.json"
for input in "$baseline_image" "$baseline_image_gz" "$image" "$image_gz" \
	"$candidate_config" "$build_json"; do
	[[ -s "$input" ]] || die "required package input is missing: $input"
done

baseline_manifest="${baseline}/SHA256SUMS"
baseline_boot="${baseline}/gemini-a53-sweep.boot.img"
baseline_dtb="${baseline}/mt6797-gemini-pda-a53-sweep.dtb"
baseline_initramfs="${baseline}/gemini-a53-sweep-initramfs.img"
baseline_provenance="${baseline}/provenance.txt"
baseline_source_build="${baseline}/source-build.json"
for input in "$baseline_manifest" "$baseline_boot" "$baseline_dtb" \
	"$baseline_initramfs" "$baseline_provenance" "$baseline_source_build"; do
	[[ -s "$input" ]] || die "Candidate O baseline input is missing: $input"
done

readonly EXPECTED_BASELINE_PACKAGE=linux-7.1.3-gemini-observability-e1d4f6f3-a73fd870
readonly EXPECTED_PACKAGE=TO_PIN
readonly EXPECTED_O_ARTIFACT=candidate-O-a53-sweep-e35dc9a
readonly EXPECTED_O_MANIFEST_SHA256=d57319532822ee89bd435114e3119a7ebf4cb009553dab4b1682f88c3534be2e
readonly EXPECTED_O_BOOT_SHA256=4376579c3b1a9ddfbec485eb62ba6cfc0af38183527924b5a250246345cb2146
readonly EXPECTED_O_DTB_SHA256=c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379
readonly EXPECTED_O_INITRAMFS_SHA256=3f19afd81632fbe654c024b9f865180b42caf61163bb26ea26211884271a11d8
readonly EXPECTED_O_IMAGE_GZ_SHA256=0c0d0e22c78b5b0d89b7a7363be55850b3f3474d3b4e7f922946747efbe164d3
readonly EXPECTED_BASELINE_IMAGE_SHA256=91f0ba20a161afd379aa483ef5de2b4d66ff495a23614beaaba1530f459ad2a3
readonly EXPECTED_P_IMAGE_SHA256=TO_PIN
readonly EXPECTED_P_IMAGE_GZ_SHA256=TO_PIN
readonly EXPECTED_P_CONFIG_SHA256=TO_PIN
readonly EXPECTED_P_BOOT_SHA256=TO_PIN
readonly EXPECTED_P_SIZE=0
readonly BOOT2_CAPACITY=16777216

[[ "$baseline_package_id" == "$EXPECTED_BASELINE_PACKAGE" ]] || \
	die "baseline package is not the exact Candidate O source package"
[[ "$baseline_id" == "$EXPECTED_O_ARTIFACT" ]] || \
	die "baseline artifact is not exact Candidate O"
if [[ "$establish_pins" == no ]]; then
	[[ "$EXPECTED_PACKAGE" != TO_PIN && "$EXPECTED_P_IMAGE_SHA256" != TO_PIN && \
		"$EXPECTED_P_IMAGE_GZ_SHA256" != TO_PIN && \
		"$EXPECTED_P_CONFIG_SHA256" != TO_PIN && \
		"$EXPECTED_P_BOOT_SHA256" != TO_PIN && "$EXPECTED_P_SIZE" != 0 ]] || \
		die "Candidate P output pins have not been established"
	[[ "$package_id" == "$EXPECTED_PACKAGE" ]] || \
		die "package is not the pinned rotation-profile build"
fi

expected_baseline_files="$(printf '%s\n' analysis.txt baseline-analysis.txt \
	baseline-check.txt boot-delta.txt foundation-validation.txt \
	gemini-a53-sweep-initramfs.img gemini-a53-sweep.boot.img \
	initramfs-build.txt initramfs-delta.txt \
	mt6797-gemini-pda-a53-sweep.dtb provenance.txt serializer.txt \
	SHA256SUMS source-build.json | sort)"
actual_baseline_files="$(find "$baseline" -maxdepth 1 -type f -printf '%f\n' | sort)"
[[ "$actual_baseline_files" == "$expected_baseline_files" ]] || \
	die "Candidate O artifact file set is not exact"
[[ "$(sha256sum "$baseline_manifest" | awk '{print $1}')" == \
	"$EXPECTED_O_MANIFEST_SHA256" ]] || die "Candidate O manifest is not pinned"
[[ "$(sha256sum "$baseline_boot" | awk '{print $1}')" == \
	"$EXPECTED_O_BOOT_SHA256" ]] || die "Candidate O boot image is not pinned"
[[ "$(sha256sum "$baseline_dtb" | awk '{print $1}')" == \
	"$EXPECTED_O_DTB_SHA256" ]] || die "Candidate O DTB is not pinned"
[[ "$(sha256sum "$baseline_initramfs" | awk '{print $1}')" == \
	"$EXPECTED_O_INITRAMFS_SHA256" ]] || die "Candidate O initramfs is not pinned"
(
	cd "$baseline"
	sha256sum --check SHA256SUMS >/dev/null
)

actual_image_sha256="$(sha256sum "$image" | awk '{print $1}')"
actual_image_gz_sha256="$(sha256sum "$image_gz" | awk '{print $1}')"
actual_config_sha256="$(sha256sum "$candidate_config" | awk '{print $1}')"
if [[ "$establish_pins" == yes ]]; then
	expected_image_sha256=$actual_image_sha256
	expected_image_gz_sha256=$actual_image_gz_sha256
	expected_config_sha256=$actual_config_sha256
else
	expected_image_sha256=$EXPECTED_P_IMAGE_SHA256
	expected_image_gz_sha256=$EXPECTED_P_IMAGE_GZ_SHA256
	expected_config_sha256=$EXPECTED_P_CONFIG_SHA256
fi

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.candidate-P-work.XXXXXX")"
staging="$(mktemp -d "$(dirname -- "$output")/.candidate-P-output.XXXXXX")"
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
		value=${value//"$baseline"/@BASELINE@}
		value=${value//"$repo_root"/@REPOSITORY@}
		printf '%s\n' "$value"
	done <"$log" >"$normalized"
	mv "$normalized" "$log"
}

"$artifact_validator" "$baseline_package" >"${staging}/baseline-package-validation.txt"
"$artifact_validator" "$package" >"${staging}/package-validation.txt"
normalize_log "${staging}/baseline-package-validation.txt"
normalize_log "${staging}/package-validation.txt"
python3 "$package_validator" \
	--baseline-package "$baseline_package" \
	--candidate-package "$package" \
	--current-manifest "$current_manifest" \
	--rotation-fragment "$rotation_fragment" \
	--expected-baseline-image-sha256 "$EXPECTED_BASELINE_IMAGE_SHA256" \
	--expected-baseline-image-gz-sha256 "$EXPECTED_O_IMAGE_GZ_SHA256" \
	--expected-candidate-image-sha256 "$expected_image_sha256" \
	--expected-candidate-image-gz-sha256 "$expected_image_gz_sha256" \
	--expected-candidate-config-sha256 "$expected_config_sha256" \
	>"${staging}/package-delta.txt"
normalize_log "${staging}/package-delta.txt"

candidate_dtb="${staging}/mt6797-gemini-pda-fbcon-rotation.dtb"
candidate_initramfs="${staging}/gemini-fbcon-rotation-initramfs.img"
candidate="${staging}/gemini-fbcon-rotation.boot.img"
install -m 0600 "$baseline_dtb" "$candidate_dtb"
install -m 0600 "$baseline_initramfs" "$candidate_initramfs"
cmp -s "$baseline_dtb" "$candidate_dtb" || die "Candidate O DTB changed"
cmp -s "$baseline_initramfs" "$candidate_initramfs" || \
	die "Candidate O initramfs changed"

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
	"$candidate" >"${staging}/analysis.txt"
normalize_log "${staging}/analysis.txt"

candidate_size="$(wc -c <"$candidate")"
candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
[[ "$candidate_size" =~ ^[0-9]+$ && "$candidate_size" -le "$BOOT2_CAPACITY" ]] || \
	die "Candidate P does not fit the known 16 MiB boot2 partition"
if [[ "$establish_pins" == yes ]]; then
	expected_boot_sha256=$candidate_sha256
else
	[[ "$candidate_sha256" == "$EXPECTED_P_BOOT_SHA256" ]] || \
		die "Candidate P boot image is not pinned"
	[[ "$candidate_size" == "$EXPECTED_P_SIZE" ]] || \
		die "Candidate P size is not pinned"
	expected_boot_sha256=$EXPECTED_P_BOOT_SHA256
fi

python3 "$boot_validator" \
	--baseline "$baseline_boot" \
	--candidate "$candidate" \
	--baseline-image-gz "$baseline_image_gz" \
	--candidate-image-gz "$image_gz" \
	--dtb "$candidate_dtb" \
	--initramfs "$candidate_initramfs" \
	--expected-baseline-sha256 "$EXPECTED_O_BOOT_SHA256" \
	--expected-candidate-sha256 "$expected_boot_sha256" \
	--expected-baseline-image-gz-sha256 "$EXPECTED_O_IMAGE_GZ_SHA256" \
	--expected-candidate-image-gz-sha256 "$expected_image_gz_sha256" \
	--expected-dtb-sha256 "$EXPECTED_O_DTB_SHA256" \
	--expected-initramfs-sha256 "$EXPECTED_O_INITRAMFS_SHA256" \
	>"${staging}/boot-delta.txt"
normalize_log "${staging}/boot-delta.txt"

if [[ "$establish_pins" == yes ]]; then
	printf 'EXPECTED_PACKAGE=%s\n' "$package_id"
	printf 'EXPECTED_P_IMAGE_SHA256=%s\n' "$actual_image_sha256"
	printf 'EXPECTED_P_IMAGE_GZ_SHA256=%s\n' "$actual_image_gz_sha256"
	printf 'EXPECTED_P_CONFIG_SHA256=%s\n' "$actual_config_sha256"
	printf 'EXPECTED_P_BOOT_SHA256=%s\n' "$candidate_sha256"
	printf 'EXPECTED_P_SIZE=%s\n' "$candidate_size"
	printf 'publication=refused-until-pins-reviewed-and-committed\n'
	exit 0
fi

install -m 0600 "$build_json" "${staging}/source-build.json"
{
	printf 'experiment=2026-07-18-fbcon-rotation-diagnostic\n'
	printf 'candidate_label=P\n'
	printf 'baseline_artifact=%s\n' "$baseline_id"
	printf 'baseline_manifest_sha256=%s\n' "$EXPECTED_O_MANIFEST_SHA256"
	printf 'baseline_package=%s\n' "$baseline_package_id"
	printf 'package=%s\n' "$package_id"
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'repo_status_sha256=%s\n' "$repo_status_sha256"
	printf 'source_date_epoch=%s\n' "$source_date_epoch"
	printf 'baseline_candidate_sha256=%s\n' "$EXPECTED_O_BOOT_SHA256"
	printf 'baseline_image_gz_sha256=%s\n' "$EXPECTED_O_IMAGE_GZ_SHA256"
	printf 'candidate_image_sha256=%s\n' "$actual_image_sha256"
	printf 'candidate_image_gz_sha256=%s\n' "$actual_image_gz_sha256"
	printf 'candidate_config_sha256=%s\n' "$actual_config_sha256"
	printf 'candidate_dtb_sha256=%s\n' "$EXPECTED_O_DTB_SHA256"
	printf 'candidate_initramfs_sha256=%s\n' "$EXPECTED_O_INITRAMFS_SHA256"
	printf 'candidate_size=%s\n' "$candidate_size"
	printf 'candidate_sha256=%s\n' "$candidate_sha256"
	printf 'boot2_capacity=%s\n' "$BOOT2_CAPACITY"
	printf 'kernel_addr=0x40200000\nramdisk_addr=0x45000000\n'
	printf 'second_addr=0x40f00000\ntags_addr=0x44000000\n'
	printf 'header_name=gemini-obs-L\nheader_cmdline=%s\n' "$bootopt"
	for input in "$artifact_validator" "$package_validator" "$boot_validator" \
		"$candidate_builder" "$serializer" "$analyzer" "$current_manifest" \
		"$rotation_fragment"; do
		printf 'input_sha256[%s]=%s\n' \
			"${input#"$repo_root"/}" "$(sha256sum "$input" | awk '{print $1}')"
	done
	printf 'resolved_config_delta=CONFIG_FRAMEBUFFER_CONSOLE_ROTATION:y;CONFIG_CMDLINE:append-fbcon=rotate:3\n'
	printf 'config_cmdline_force=yes\nfont_8x16_unchanged=yes\n'
	printf 'marker=GEMINI_A53_SWEEP_20260718_O;inherited-exactly\n'
	printf 'inherited_kernel_dtb_config_label=historical-not-P-config-evidence\n'
	printf 'unchanged_header=yes\nunchanged_dtb=yes\nunchanged_initramfs=yes\n'
	printf 'kernel_payload_changed=yes\nstorage_access=none\n'
	printf 'build_hardware_write=none\nflash=none\nruntime_result=not-tested\n'
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

printf 'validation=compiled-fbcon-rotation-candidate\n'
printf 'candidate_label=P\n'
printf 'package=%s\n' "$package_id"
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-fbcon-rotation.boot.img\n' "$output"
printf 'candidate_sha256=%s\n' "$candidate_sha256"
printf 'resolved_config_delta=rotation-support-and-forced-rotate-3-only\n'
printf 'unchanged_header=yes\nunchanged_dtb=yes\nunchanged_initramfs=yes\n'
printf 'build_hardware_write=none\nflash=none\nruntime_result=not-tested\n'
