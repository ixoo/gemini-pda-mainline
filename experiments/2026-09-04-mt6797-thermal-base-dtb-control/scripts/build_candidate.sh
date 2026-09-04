#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly SOURCE_NAME=candidate-mt6797-pwrap-reset-305230b1
readonly SOURCE_MANIFEST_SHA256=528f38ae3459149bc6f12242118b69d104590bd8902eef7d3969a1cd1b8d0f17
readonly SOURCE_INITRAMFS=gemini-pwrap-reset-serviceability-initramfs.img
readonly SOURCE_INITRAMFS_SHA256=344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b
readonly PACKAGE_DTB=dtbs/mediatek/mt6797-gemini-pda.dtb
readonly CANDIDATE_DTB=mt6797-gemini-pda.dtb
readonly CANDIDATE_INITRAMFS=gemini-mt6797-thermal-base-dtb-control-initramfs.img
readonly CANDIDATE_BOOT=gemini-mt6797-thermal-base-dtb-control.boot.img
readonly PADDED_BOOT=boot2-padded.img
readonly BOOT2_SIZE=16777216
readonly CANDIDATE_DIR=candidate-mt6797-thermal-base-dtb-control-fb660f34
readonly CANDIDATE_RAW_SHA256=fb660f34d631109eeeaa5625c457e141ff0beadafbdbf47375f11d11ca9e449d
readonly CANDIDATE_PADDED_SHA256=ec26245757291c4d7761683b7afc8042cc8bf98fd34a4c977946cf23a5147db5

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --package DIR --initramfs-source DIR --output-parent DIR\n' "$0" >&2; }

package=
initramfs_source=
output_parent=
while (($#)); do
	case "$1" in
	--package|--initramfs-source|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--initramfs-source) initramfs_source=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
for directory in "$package" "$initramfs_source" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] || die "missing or unsafe directory: $directory"
done
for command in awk basename cmp find install jq mkdir mktemp mv python3 rm sha256sum sort tr wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "missing command: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repository=$(cd -- "$script_dir/../../.." && pwd -P)
package=$(cd -- "$package" && pwd -P)
initramfs_source=$(cd -- "$initramfs_source" && pwd -P)
output_parent=$(cd -- "$output_parent" && pwd -P)
readonly script_dir repository package initramfs_source output_parent
[[ "$(basename -- "$initramfs_source")" == "$SOURCE_NAME" ]] || die 'initramfs source basename changed'
[[ "$(sha256sum "$initramfs_source/SHA256SUMS" | awk '{print $1}')" == "$SOURCE_MANIFEST_SHA256" ]] || die 'initramfs source manifest changed'
[[ "$(sha256sum "$initramfs_source/$SOURCE_INITRAMFS" | awk '{print $1}')" == "$SOURCE_INITRAMFS_SHA256" ]] || die 'initramfs source image changed'
case "$output_parent" in "$repository"|"$package"|"$initramfs_source") die 'unsafe output parent' ;; esac

work=$(mktemp -d "$output_parent/.thermal-base-dtb-control.XXXXXXXX")
cleanup() { [[ ! -d "${work:-}" ]] || rm -rf -- "$work"; }
trap cleanup EXIT HUP INT TERM
stage="$work/$CANDIDATE_DIR"
replica="$work/replica"
mkdir "$stage" "$replica"

package_validator="$repository/experiments/2026-09-04-mt6797-thermal-stage-ledger/scripts/validate_package.py"
python3 "$package_validator" --repository "$repository" --package "$package" >"$stage/package-validation.txt"
install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
install -m 0600 "$package/provenance/build.json" "$stage/source-build.json"
install -m 0600 "$package/$PACKAGE_DTB" "$stage/$CANDIDATE_DTB"
install -m 0600 "$initramfs_source/$SOURCE_INITRAMFS" "$stage/$CANDIDATE_INITRAMFS"

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
[[ "$raw_sha" == "$CANDIDATE_RAW_SHA256" ]] || die 'selected raw candidate identity changed'
[[ "$(sha256sum "$stage/$PADDED_BOOT" | awk '{print $1}')" == "$CANDIDATE_PADDED_SHA256" ]] || die 'selected padded candidate identity changed'
output="$output_parent/$CANDIDATE_DIR"
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite final candidate'
{
	printf 'experiment=2026-09-04-mt6797-thermal-base-dtb-control\n'
	printf 'profile=mt6797-thermal-stage-ledger\n'
	printf 'repository_commit=%s\n' "$(jq -er .repository_commit "$package/provenance/build.json")"
	printf 'initramfs_source=%s\n' "$SOURCE_NAME"
	printf 'candidate_initramfs_sha256=%s\n' "$SOURCE_INITRAMFS_SHA256"
	printf 'candidate_dtb_sha256=%s\n' "$(sha256sum "$stage/$CANDIDATE_DTB" | awk '{print $1}')"
	printf 'candidate_raw_sha256=%s\n' "$raw_sha"
	printf 'candidate_raw_size=%s\n' "$(wc -c <"$stage/$CANDIDATE_BOOT" | tr -d ' ')"
	printf 'candidate_padded_sha256=%s\n' "$CANDIDATE_PADDED_SHA256"
	printf 'candidate_padded_size=%s\n' "$BOOT2_SIZE"
	printf 'appended_dtb_delta=thermal-serviceability-to-base-only\n'
	printf 'pwrap_reset_input=1\nthermal_reset_input=0\n'
	printf 'thermal_controller=disabled\nstandalone_auxadc=disabled\nthermal_zones=0\n'
	printf 'thermal_ledger_expected_owner=no-exact-model-guard\n'
	printf 'device_action=none\nhardware_write=none\n'
} >"$stage/provenance.txt"
(cd "$stage" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'candidate manifest failed'
python3 "$script_dir/validate_candidate.py" --repository "$repository" --package "$package" --initramfs-source "$initramfs_source" --candidate "$stage"
mv "$stage" "$output"
chmod 0600 "$output"/*
trap - EXIT HUP INT TERM
rm -rf -- "$work"
printf 'artifact=%s\ndevice_action=none\nhardware_write=none\n' "$output"
