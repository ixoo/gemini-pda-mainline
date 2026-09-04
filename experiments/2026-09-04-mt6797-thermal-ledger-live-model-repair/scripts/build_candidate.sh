#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly PROFILE=mt6797-thermal-stage-ledger
readonly BUILD_COMMIT=08fd54667c620649938f2b500779e59f4d4b8762
readonly SOURCE_NAME=candidate-mt6797-thermal-serviceability-dt-repair-dd7a6ec4
readonly SOURCE_MANIFEST_SHA256=b89a4d603a55e7f923d70c5dc2699039536244255f6ea7f40b9747fccac2d3d7
readonly SOURCE_DTB=mt6797-gemini-pda-thermal-serviceability.dtb
readonly SOURCE_DTB_SHA256=f131a06474ad5665dd957d7290f7b1240ca9603028046c93f4a5527ba3aa1366
readonly SOURCE_INITRAMFS=gemini-mt6797-thermal-serviceability-dt-repair-initramfs.img
readonly SOURCE_INITRAMFS_SHA256=344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b
readonly CANDIDATE_DTB=mt6797-gemini-pda-thermal-ledger-live-model-repair.dtb
readonly CANDIDATE_INITRAMFS=gemini-mt6797-thermal-ledger-live-model-repair-initramfs.img
readonly CANDIDATE_BOOT=gemini-mt6797-thermal-ledger-live-model-repair.boot.img
readonly PADDED_BOOT=boot2-padded.img
readonly BOOT2_SIZE=16777216
readonly CANDIDATE_DIR=candidate-mt6797-thermal-ledger-live-model-repair-40361fae
readonly CANDIDATE_RAW_SHA256=40361fae05a603b5f05c98ef88950a404ba95c646b7ded4f773e1088febca27d
readonly CANDIDATE_PADDED_SHA256=93a78b490a9ffbf32eb60c5c875f508fd05b43b726220b3ccdbe9277792752a4

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
package=
source=
output_parent=
while (($#)); do
	case "$1" in
	--package|--source|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--source) source=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2 ;;
	*) die "usage: $0 --package DIR --source DIR --output-parent DIR" ;;
	esac
done
for directory in "$package" "$source" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] || die "missing or unsafe directory: $directory"
done
for command in awk basename cmp find install jq mkdir mktemp mv python3 rm sha256sum sort tr wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "missing command: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repository=$(cd -- "$script_dir/../../.." && pwd -P)
package=$(cd -- "$package" && pwd -P)
source=$(cd -- "$source" && pwd -P)
output_parent=$(cd -- "$output_parent" && pwd -P)
readonly script_dir repository package source output_parent
[[ "$(basename -- "$source")" == "$SOURCE_NAME" ]] || die 'source candidate basename changed'
[[ "$(sha256sum "$source/SHA256SUMS" | awk '{print $1}')" == "$SOURCE_MANIFEST_SHA256" ]] ||
	die 'source candidate manifest changed'
(
	cd "$source"
	sha256sum --check --strict SHA256SUMS >/dev/null
) || die 'source candidate manifest failed'
[[ "$(sha256sum "$source/$SOURCE_DTB" | awk '{print $1}')" == "$SOURCE_DTB_SHA256" ]] ||
	die 'runtime-proven source DT changed'
[[ "$(sha256sum "$source/$SOURCE_INITRAMFS" | awk '{print $1}')" == "$SOURCE_INITRAMFS_SHA256" ]] ||
	die 'source initramfs changed'
case "$output_parent" in "$repository"|"$package"|"$source") die 'unsafe output parent' ;; esac

work=$(mktemp -d "$output_parent/.thermal-ledger-live-model-repair.XXXXXXXX")
cleanup() { [[ ! -d "${work:-}" ]] || rm -rf -- "$work"; }
trap cleanup EXIT HUP INT TERM
stage="$work/$CANDIDATE_DIR"
replica="$work/replica"
mkdir "$stage" "$replica"

package_validator="$script_dir/validate_package.py"
python3 "$package_validator" --repository "$repository" --package "$package" >"$stage/package-validation.txt"
install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
install -m 0600 "$package/provenance/build.json" "$stage/source-build.json"
install -m 0600 "$source/$SOURCE_DTB" "$stage/$CANDIDATE_DTB"
install -m 0600 "$source/$SOURCE_INITRAMFS" "$stage/$CANDIDATE_INITRAMFS"

serializer="$repository/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repository/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for output in "$stage/$CANDIDATE_BOOT" "$replica/$CANDIDATE_BOOT"; do
	python3 "$serializer" --kernel "$stage/Image.gz" \
		--ramdisk "$stage/$CANDIDATE_INITRAMFS" --dtb "$stage/$CANDIDATE_DTB" \
		--output "$output" --name gemini-obs-L \
		--cmdline bootopt=64S3,32N2,64N2 --kernel-addr 0x40200000 \
		--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
		--tags-addr 0x44000000 --lk-android8 >/dev/null
done
cmp -s "$stage/$CANDIDATE_BOOT" "$replica/$CANDIDATE_BOOT" ||
	die 'independent container assemblies differ'
python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/$CANDIDATE_INITRAMFS" --expected-dtb "$stage/$CANDIDATE_DTB" \
	--expected-name gemini-obs-L --expected-cmdline bootopt=64S3,32N2,64N2 \
	"$stage/$CANDIDATE_BOOT" >"$stage/container-validation.txt"

python3 - "$stage/$CANDIDATE_BOOT" "$stage/$PADDED_BOOT" "$BOOT2_SIZE" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_bytes()
size = int(sys.argv[3])
if not 0 < len(source) < size:
    raise SystemExit("raw candidate does not fit exact boot2 size")
Path(sys.argv[2]).write_bytes(source + bytes(size - len(source)))
PY
raw_sha=$(sha256sum "$stage/$CANDIDATE_BOOT" | awk '{print $1}')
[[ "$raw_sha" == "$CANDIDATE_RAW_SHA256" ]] || die 'selected raw candidate identity changed'
[[ "$(sha256sum "$stage/$PADDED_BOOT" | awk '{print $1}')" == "$CANDIDATE_PADDED_SHA256" ]] ||
	die 'selected padded candidate identity changed'

output="$output_parent/$CANDIDATE_DIR"
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite final candidate'
{
	printf 'experiment=2026-09-04-mt6797-thermal-ledger-live-model-repair\n'
	printf 'profile=%s\nrepository_commit=%s\n' "$PROFILE" "$BUILD_COMMIT"
	printf 'runtime_proven_source=%s\nsource_manifest_sha256=%s\n' "$SOURCE_NAME" "$SOURCE_MANIFEST_SHA256"
	printf 'source_runtime_evidence_sha256=%s\n' 012fa2ec367424da240359a34b82f3285f289eb91b07499e3b7d213440bb1a0c
	printf 'candidate_dtb_sha256=%s\ncandidate_initramfs_sha256=%s\n' "$SOURCE_DTB_SHA256" "$SOURCE_INITRAMFS_SHA256"
	printf 'candidate_raw_sha256=%s\ncandidate_raw_size=%s\n' "$raw_sha" "$(wc -c <"$stage/$CANDIDATE_BOOT" | tr -d ' ')"
	printf 'candidate_padded_sha256=%s\ncandidate_padded_size=%s\n' "$CANDIDATE_PADDED_SHA256" "$BOOT2_SIZE"
	printf 'dt_delta=none-from-runtime-proven-candidate\n'
	printf 'kernel_delta=thermal-ledger-live-model-guard-only\n'
	printf 'usb_keyboard_pwrap_emmc_simplefb=runtime-proven-preserved\n'
	printf 'thermal_reset_input=0\nthermal_zones=1\nthermal_trips=0\ncooling_maps=0\n'
	printf 'cpu8_cpu9=offline-no-request\nload=none\ncpufreq_opp=disabled\n'
	printf 'device_action=none\nhardware_write=none\n'
} >"$stage/provenance.txt"
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(
	cd "$stage"
	sha256sum --check --strict SHA256SUMS >/dev/null
) || die 'candidate manifest failed'
python3 "$script_dir/validate_candidate.py" --repository "$repository" \
	--package "$package" --source "$source" --candidate "$stage"
mv "$stage" "$output"
chmod 0600 "$output"/*
trap - EXIT HUP INT TERM
rm -rf -- "$work"
printf 'artifact=%s\ndevice_action=none\nhardware_write=none\n' "$output"
