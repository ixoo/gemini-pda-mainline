#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly PROFILE=mt6797-pwrap-reset-serviceability
readonly CONTROL_NAME=candidate-AW-emmc-pmic-wrap-42c5c403
readonly CONTROL_MANIFEST_SHA256=22b2cc789c0ac39792617f693b8852ff1a8ad25d71e733cb6f8727716f34171b
readonly CONTROL_DTB=mt6797-gemini-pda-emmc-pmic-development.dtb
readonly CONTROL_INITRAMFS=gemini-emmc-pmic-development-initramfs.img
readonly CANDIDATE_DTB=mt6797-gemini-pda-pwrap-reset-serviceability.dtb
readonly CANDIDATE_INITRAMFS=gemini-pwrap-reset-serviceability-initramfs.img
readonly CANDIDATE_BOOT=gemini-mt6797-pwrap-reset-serviceability.boot.img
readonly PADDED_BOOT=boot2-padded.img
readonly BOOT2_SIZE=16777216

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --package DIR --control DIR --output-parent DIR\n' "$0" >&2; }

package=
control=
output_parent=
while (($#)); do
	case "$1" in
	--package|--control|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--control) control=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
for directory in "$package" "$control" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] || die "missing or unsafe directory: $directory"
done
for command in awk basename cmp find git install jq mkdir mktemp mv python3 \
	rm sha256sum sort tr wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "missing command: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repository=$(cd -- "$script_dir/../../.." && pwd -P)
package=$(cd -- "$package" && pwd -P)
control=$(cd -- "$control" && pwd -P)
output_parent=$(cd -- "$output_parent" && pwd -P)
readonly script_dir repository package control output_parent
[[ "$(basename -- "$control")" == "$CONTROL_NAME" ]] || die 'control artifact basename changed'
[[ "$(sha256sum "$control/SHA256SUMS" | awk '{print $1}')" == "$CONTROL_MANIFEST_SHA256" ]] ||
	die 'control artifact manifest changed'
case "$output_parent" in
"$repository"|"$package"|"$control") die 'unsafe output parent' ;;
esac

work=$(mktemp -d "$output_parent/.pwrap-reset-candidate.XXXXXXXX")
cleanup() { [[ ! -d "${work:-}" ]] || rm -rf -- "$work"; }
trap cleanup EXIT HUP INT TERM
stage="$work/stage"
replica="$work/replica"
mkdir "$stage" "$replica"

python3 "$script_dir/validate_package.py" --repository "$repository" --package "$package" >"$stage/package-validation.txt"
install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
install -m 0600 "$package/provenance/build.json" "$stage/source-build.json"
install -m 0600 "$control/$CONTROL_INITRAMFS" "$stage/$CANDIDATE_INITRAMFS"

python3 "$script_dir/build_dtb.py" --control "$control/$CONTROL_DTB" --output "$stage/$CANDIDATE_DTB" >"$stage/dtb-transform.txt"
python3 "$script_dir/build_dtb.py" --control "$control/$CONTROL_DTB" --output "$replica/$CANDIDATE_DTB" >/dev/null
cmp -s "$stage/$CANDIDATE_DTB" "$replica/$CANDIDATE_DTB" || die 'independent DT transforms differ'

serializer="$repository/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repository/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for output in "$stage/$CANDIDATE_BOOT" "$replica/$CANDIDATE_BOOT"; do
	python3 "$serializer" --kernel "$stage/Image.gz" --ramdisk "$stage/$CANDIDATE_INITRAMFS" \
		--dtb "$stage/$CANDIDATE_DTB" --output "$output" --name gemini-obs-L \
		--cmdline bootopt=64S3,32N2,64N2 --kernel-addr 0x40200000 \
		--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
		--tags-addr 0x44000000 --lk-android8 >/dev/null
done
cmp -s "$stage/$CANDIDATE_BOOT" "$replica/$CANDIDATE_BOOT" || die 'independent container assemblies differ'
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
readonly raw_sha
output="$output_parent/candidate-mt6797-pwrap-reset-${raw_sha:0:8}"
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite final candidate'
{
	printf 'experiment=2026-09-04-mt6797-pwrap-reset-serviceability\n'
	printf 'profile=%s\n' "$PROFILE"
	printf 'repository_commit=%s\n' "$(jq -er .repository_commit "$package/provenance/build.json")"
	printf 'control_artifact=%s\n' "$CONTROL_NAME"
	printf 'control_manifest_sha256=%s\n' "$CONTROL_MANIFEST_SHA256"
	printf 'control_dtb_sha256=%s\n' "$(sha256sum "$control/$CONTROL_DTB" | awk '{print $1}')"
	printf 'control_initramfs_sha256=%s\n' "$(sha256sum "$control/$CONTROL_INITRAMFS" | awk '{print $1}')"
	printf 'candidate_dtb_sha256=%s\n' "$(sha256sum "$stage/$CANDIDATE_DTB" | awk '{print $1}')"
	printf 'candidate_raw_sha256=%s\n' "$raw_sha"
	printf 'candidate_raw_size=%s\n' "$(wc -c <"$stage/$CANDIDATE_BOOT" | tr -d ' ')"
	printf 'candidate_padded_sha256=%s\n' "$(sha256sum "$stage/$PADDED_BOOT" | awk '{print $1}')"
	printf 'candidate_padded_size=%s\n' "$BOOT2_SIZE"
	printf 'dt_delta=pwrap-reset-cell-64-to-1\n'
	printf 'thermal_enable=none\n'
	printf 'device_action=none\n'
	printf 'hardware_write=none\n'
} >"$stage/provenance.txt"
(cd "$stage" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'candidate manifest failed'
python3 "$script_dir/validate_candidate.py" --repository "$repository" --package "$package" \
	--control "$control" --candidate "$stage"
mv "$stage" "$output"
chmod 0600 "$output"/*
cleanup
trap - EXIT HUP INT TERM
printf 'artifact=%s\n' "$output"
printf 'device_action=none\nhardware_write=none\n'
