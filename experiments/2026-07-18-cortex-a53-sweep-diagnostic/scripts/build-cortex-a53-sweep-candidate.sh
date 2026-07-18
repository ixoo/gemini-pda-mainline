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
usage: build-cortex-a53-sweep-candidate.sh --baseline DIR
       [--output DIR] [--source-date-epoch N]

Build non-flashing Candidate O from an explicit exact Candidate N artifact.
The Linux Image.gz, appended DTB, kernel configuration, Android-v0 addresses,
name, and command line remain byte-identical. Only /init changes. This command
has no device, partition, adb, fastboot, mtkclient, or flashing interface.
EOF
}

baseline=
output=
source_date_epoch=${SOURCE_DATE_EPOCH:-0}
while (($#)); do
	case "$1" in
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
[[ -n "$baseline" && -d "$baseline" ]] || \
	die "--baseline must name the exact Candidate N artifact directory"
[[ "$source_date_epoch" =~ ^[0-9]+$ && "$source_date_epoch" == 0 ]] || \
	die "Candidate O requires source-date-epoch zero"
for command in \
	awk basename cat chmod cmp cpio cut dirname find git gzip head install \
	mkdir mktemp mv python3 rm sha256sum sort tail uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
repo_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
[[ -z "$repo_status" ]] || \
	die "Candidate O requires a clean repository so repo_revision identifies every input"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
repo_status_sha256="$(printf '%s' "$repo_status" | sha256sum | awk '{print $1}')"

baseline="$(cd -- "$baseline" && pwd -P)"
baseline_id="$(basename -- "$baseline")"
if [[ -z "$output" ]]; then
	output="${HOME}/artifacts/boot-candidates/candidate-O-a53-sweep-${repo_revision:0:8}"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite $output"

initramfs_builder="${script_dir}/build-initramfs.sh"
initramfs_validator="${script_dir}/validate-initramfs-delta.sh"
foundation_validator="${script_dir}/validate-a53-foundation.py"
boot_validator="${script_dir}/validate-boot-delta.py"
candidate_builder="${script_dir}/build-cortex-a53-sweep-candidate.sh"
init_source="${experiment_dir}/initramfs/init"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in \
	"$initramfs_builder" "$initramfs_validator" "$foundation_validator" \
	"$boot_validator" "$candidate_builder" "$init_source" "$serializer" "$analyzer"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

baseline_manifest="${baseline}/SHA256SUMS"
baseline_boot="${baseline}/gemini-cpu1-online.boot.img"
baseline_dtb="${baseline}/mt6797-gemini-pda-cpu1-online.dtb"
baseline_initramfs="${baseline}/gemini-cpu1-online-initramfs.img"
baseline_provenance="${baseline}/provenance.txt"
baseline_source_build="${baseline}/source-build.json"
for input in \
	"$baseline_manifest" "$baseline_boot" "$baseline_dtb" \
	"$baseline_initramfs" "$baseline_provenance" "$baseline_source_build"; do
	[[ -s "$input" ]] || die "Candidate N baseline input is missing: $input"
done

readonly EXPECTED_BASELINE_MANIFEST_SHA256=a5e898f6cfc11c205068e930e92f2739746ec4a7df81a960191674f2e30a55b4
readonly EXPECTED_BASELINE_BOOT_SHA256=43aea71224f6261001ff00904b30dae29063334172a2f6b0163b424a84c0e3aa
readonly EXPECTED_IMAGE_GZ_SHA256=0c0d0e22c78b5b0d89b7a7363be55850b3f3474d3b4e7f922946747efbe164d3
readonly EXPECTED_BASELINE_DTB_SHA256=c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379
readonly EXPECTED_BASELINE_INITRAMFS_SHA256=3351422e594c59e5785e12cac6ffbefa2644bd6c85932ac6825a9b9c5edd6290
readonly EXPECTED_BASELINE_PROVENANCE_SHA256=a226416d873a1b0165910dd2aa5ca10e64922672f3c027eefc4bf09a5b1e3d11
readonly EXPECTED_BASELINE_SOURCE_BUILD_SHA256=5501b0ea950db90be9edfd187f68a49a8e1978623ece66547b1b8a1d531a8003
readonly EXPECTED_CANDIDATE_INITRAMFS_SHA256=3f19afd81632fbe654c024b9f865180b42caf61163bb26ea26211884271a11d8
readonly EXPECTED_CANDIDATE_SHA256=4376579c3b1a9ddfbec485eb62ba6cfc0af38183527924b5a250246345cb2146
readonly EXPECTED_CANDIDATE_SIZE=6526976
readonly BOOT2_CAPACITY=16777216
readonly IMAGE_GZ_OFFSET=2048
readonly IMAGE_GZ_SIZE=5485211

expected_baseline_files="$(printf '%s\n' \
	SHA256SUMS analysis.txt baseline-analysis.txt baseline-check.txt \
	boot-delta.txt foundation-validation.txt \
	gemini-cpu1-online-initramfs.img \
	gemini-cpu1-online.boot.img initramfs-build.txt \
	initramfs-delta.txt mt6797-gemini-pda-cpu1-online.dtb \
	provenance.txt serializer.txt source-build.json | sort)"
actual_baseline_files="$(find "$baseline" -maxdepth 1 -type f -printf '%f\n' | sort)"
[[ "$actual_baseline_files" == "$expected_baseline_files" ]] || \
	die "Candidate N artifact file set is not exact"
[[ "$(sha256sum "$baseline_manifest" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_MANIFEST_SHA256" ]] || die "Candidate N manifest is not pinned"
[[ "$(sha256sum "$baseline_boot" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_BOOT_SHA256" ]] || die "Candidate N boot image is not pinned"
[[ "$(sha256sum "$baseline_dtb" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_DTB_SHA256" ]] || die "Candidate N DTB is not pinned"
[[ "$(sha256sum "$baseline_initramfs" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || die "Candidate N initramfs is not pinned"
[[ "$(sha256sum "$baseline_provenance" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_PROVENANCE_SHA256" ]] || die "Candidate N provenance is not pinned"
[[ "$(sha256sum "$baseline_source_build" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_SOURCE_BUILD_SHA256" ]] || die "Candidate N source build is not pinned"

[[ "$EXPECTED_CANDIDATE_INITRAMFS_SHA256" != TO_PIN && \
	"$EXPECTED_CANDIDATE_SHA256" != TO_PIN && \
	"$EXPECTED_CANDIDATE_SIZE" != 0 ]] || \
	die "Candidate O output pins have not been established"

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.candidate-O-work.XXXXXX")"
staging="$(mktemp -d "$(dirname -- "$output")/.candidate-O-output.XXXXXX")"
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
		value=${value//"$baseline"/@BASELINE@}
		value=${value//"$repo_root"/@REPOSITORY@}
		printf '%s\n' "$value"
	done <"$log" >"$normalized"
	mv "$normalized" "$log"
}

(
	cd "$baseline"
	sha256sum --check SHA256SUMS
) >"${staging}/baseline-check.txt"
normalize_log "${staging}/baseline-check.txt"

image_gz="${workdir}/Image.gz"
head -c "$((IMAGE_GZ_OFFSET + IMAGE_GZ_SIZE))" "$baseline_boot" \
	| tail -c "$IMAGE_GZ_SIZE" >"$image_gz"
[[ "$(wc -c <"$image_gz")" == "$IMAGE_GZ_SIZE" ]] || \
	die "extracted Candidate N Image.gz has an unexpected size"
[[ "$(sha256sum "$image_gz" | awk '{print $1}')" == \
	"$EXPECTED_IMAGE_GZ_SHA256" ]] || die "extracted Candidate N Image.gz is not pinned"

bootopt='bootopt=64S3,32N2,64N2'
python3 "$analyzer" --validate-lk \
	--expected-image-gz "$image_gz" \
	--expected-ramdisk "$baseline_initramfs" \
	--expected-dtb "$baseline_dtb" \
	--expected-name gemini-obs-L \
	--expected-cmdline "$bootopt" \
	"$baseline_boot" >"${staging}/baseline-analysis.txt"
normalize_log "${staging}/baseline-analysis.txt"
python3 "$foundation_validator" --image-gz "$image_gz" --dtb "$baseline_dtb" \
	>"${staging}/foundation-validation.txt"
normalize_log "${staging}/foundation-validation.txt"

candidate_dtb="${staging}/mt6797-gemini-pda-a53-sweep.dtb"
candidate_initramfs="${staging}/gemini-a53-sweep-initramfs.img"
candidate="${staging}/gemini-a53-sweep.boot.img"
install -m 0600 "$baseline_dtb" "$candidate_dtb"
"$initramfs_builder" \
	--baseline "$baseline_initramfs" \
	--output "$candidate_initramfs" \
	--source-date-epoch "$source_date_epoch" \
	>"${staging}/initramfs-build.txt"
normalize_log "${staging}/initramfs-build.txt"
"$initramfs_validator" \
	--baseline "$baseline_initramfs" \
	--candidate "$candidate_initramfs" \
	>"${staging}/initramfs-delta.txt"
normalize_log "${staging}/initramfs-delta.txt"

candidate_initramfs_sha256="$(sha256sum "$candidate_initramfs" | awk '{print $1}')"
[[ "$candidate_initramfs_sha256" == "$EXPECTED_CANDIDATE_INITRAMFS_SHA256" ]] || \
	die "Candidate O initramfs does not match its pinned bytes"

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
python3 "$boot_validator" \
	--baseline "$baseline_boot" \
	--candidate "$candidate" \
	--image-gz "$image_gz" \
	--dtb "$candidate_dtb" \
	--baseline-ramdisk "$baseline_initramfs" \
	--candidate-ramdisk "$candidate_initramfs" \
	>"${staging}/boot-delta.txt"
normalize_log "${staging}/boot-delta.txt"

candidate_size="$(wc -c <"$candidate")"
candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
[[ "$candidate_size" =~ ^[0-9]+$ && "$candidate_size" -le "$BOOT2_CAPACITY" ]] || \
	die "Candidate O does not fit the known 16 MiB boot2 partition"
[[ "$candidate_size" == "$EXPECTED_CANDIDATE_SIZE" ]] || \
	die "Candidate O size is not pinned"
[[ "$candidate_sha256" == "$EXPECTED_CANDIDATE_SHA256" ]] || \
	die "Candidate O image is not pinned"
install -m 0600 "$baseline_source_build" "${staging}/source-build.json"

cpio_version="$(cpio --version | awk 'NR == 1 { first = $0 } END { print first }')"
gzip_version="$(gzip --version | awk 'NR == 1 { first = $0 } END { print first }')"
python_version="$(python3 --version)"
{
	printf 'experiment=2026-07-18-cortex-a53-sweep-diagnostic\n'
	printf 'candidate_label=O\n'
	printf 'baseline_artifact=%s\n' "$baseline_id"
	printf 'baseline_manifest_sha256=%s\n' "$EXPECTED_BASELINE_MANIFEST_SHA256"
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'repo_status_sha256=%s\n' "$repo_status_sha256"
	printf 'source_date_epoch=%s\n' "$source_date_epoch"
	printf 'kernel_recompiled=no;exact-candidate-N-kernel-segment-reused\n'
	printf 'dtb_changed=no;exact-candidate-N-DTB-reused\n'
	printf 'config_changed=no;embedded-config-sha256=%s\n' \
		5a0c442c67b64cbabd4d030c93d50837bfc93e34d8878b413805457bfcd8e7cd
	printf 'baseline_candidate_sha256=%s\n' "$EXPECTED_BASELINE_BOOT_SHA256"
	printf 'image_gz_sha256=%s\n' "$EXPECTED_IMAGE_GZ_SHA256"
	printf 'dtb_sha256=%s\n' "$EXPECTED_BASELINE_DTB_SHA256"
	printf 'baseline_initramfs_sha256=%s\n' "$EXPECTED_BASELINE_INITRAMFS_SHA256"
	printf 'candidate_initramfs_sha256=%s\n' "$candidate_initramfs_sha256"
	printf 'candidate_size=%s\n' "$candidate_size"
	printf 'candidate_sha256=%s\n' "$candidate_sha256"
	printf 'boot2_capacity=%s\n' "$BOOT2_CAPACITY"
	printf 'kernel_addr=0x40200000\nramdisk_addr=0x45000000\n'
	printf 'second_addr=0x40f00000\ntags_addr=0x44000000\n'
	printf 'header_name=gemini-obs-L;unchanged-from-candidate-N\n'
	printf 'header_cmdline=%s\n' "$bootopt"
	printf 'tool_cpio=%s\n' "$cpio_version"
	printf 'tool_gzip=%s\n' "$gzip_version"
	printf 'tool_python=%s\n' "$python_version"
	for input in \
		"$candidate_builder" "$initramfs_builder" "$initramfs_validator" \
		"$foundation_validator" "$boot_validator" "$serializer" "$analyzer" \
		"$init_source"; do
		printf 'input_sha256[%s]=%s\n' \
			"${input#"$repo_root"/}" "$(sha256sum "$input" | awk '{print $1}')"
	done
	printf 'payload_delta=initramfs:/init-replaced-only\n'
	printf 'unexpected_payload_delta=none\n'
	printf 'watchdog_action=armed-before-a53-sweep,one-handoff-ping,no-further-pings\n'
	printf 'cpu_action=sequential-write-1-once-to-cpu1-through-cpu7-online;stop-first-failure\n'
	printf 'cpu_reservation=cpu8-and-cpu9-remain-offline-and-untouched\n'
	printf 'other_sysfs_write=none\n'
	printf 'storage_access=none\nruntime_networking=none\n'
	printf 'build_hardware_write=none\nflash=none\n'
	printf 'runtime_result=not-tested\n'
	printf '\n[parser]\n'
	cat "${staging}/analysis.txt"
} >"${staging}/provenance.txt"

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
rm -rf "$workdir"
workdir=
trap - EXIT

printf 'validation=cortex-a53-sweep-candidate\n'
printf 'candidate_label=O\n'
printf 'baseline=%s\n' "$baseline_id"
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-a53-sweep.boot.img\n' "$output"
printf 'candidate_sha256=%s\n' "$candidate_sha256"
printf 'candidate_size=%s\n' "$candidate_size"
printf 'unchanged_candidate_n_kernel_segment=yes\n'
printf 'unchanged_candidate_n_dtb=yes\n'
printf 'unchanged_candidate_n_config=yes\n'
printf 'payload_delta=initramfs-init-only\n'
printf 'build_raw_block_device_access=none\n'
printf 'build_hardware_write=none\nflash=none\n'
printf 'runtime_result=not-tested\n'
