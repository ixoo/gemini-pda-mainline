#!/usr/bin/env bash

# Assemble the exact stage-18 topology, thermal, and frequency-observer image.
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly PACKAGE_NAME=linux-7.1.3-gemini-gemini-a72-frequency-thermal-candidate-b7cccd63-18ded825
readonly PACKAGE_MANIFEST_SHA256=b0c13ae492c6882816903fcaa9718629ee55e595a7535b5e28c2bb70eb6854bf
readonly BUILD_COMMIT=556575a202e09d25093c578cded454854a3e6d08
readonly PROFILE=gemini-a72-frequency-thermal-candidate
readonly RELEASE=7.1.3-gemini-a72-frequency-thermal
readonly IMAGE_GZ_SHA256=bb355b5531de49b6aea75f74e6f1340a829a1e602ec1f48a935c64b599d4118d
readonly SYSTEM_MAP_SHA256=724ad03896366e3ce8eeddada7bd743decc5235d81a0cbf277adb4fb911d2bee
readonly CONFIG_SHA256=500b3fb53e403d16fcd00bcc9634148da9ef41ab58eec5b4401f5563e1ac24cf
readonly BUILD_JSON_SHA256=c243ee06650a83ab16ea10e9c0fd679a49bb4125c0b67a3fb02c0600ebb1ab11
readonly PACKAGE_DTB_SHA256=df70033883ae3dc7bee7d3af42e7d1677573c153c24fc295b9b79d919f8722a3
readonly A41_RECORD_SHA256=1cb788595e9af5aa977882308c82938b5d1c1848ae323f4b840172d0994598db
readonly TOPOLOGY_DTB_SHA256=4b05758f0aa04fb6aeb91e69bed7224fbe411d9d5fe671ff167214725c32f923
readonly THERMAL_OVERLAY_SHA256=2f0a9a424d75f3042cabcb54fce0518133deb89a065d5671b87fce287b8cc91a
readonly PRODUCTION_DTB_SHA256=46be0ae62bf66bf8e9f905ec3ad5eebbdc51c79ff3dc21859077ebe3f1aec363
readonly INITRAMFS_SHA256=e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f
readonly SERIALIZER_SHA256=569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95
readonly DT_BUILDER_SHA256=4207f1a1083362fcf252ecb0d36c645fea529aac885b3bc610402a5a0331109c
readonly DT_VALIDATOR_SHA256=b104f6ea11d0b60006dce46b2adaa0827452d643904d33eb5fc65be7ed610fee
readonly RAW_SHA256=398ca636f54a2825ff32f1cba86d06fd55a0a4083c46c77c85a47f0be09804a7
readonly RAW_SIZE=7131136
readonly PADDED_SHA256=ea2aae419220b3c2ea11780f9c91dbb51d509286cd76d2ba1741d9e08e837c9c
readonly BOOT2_SIZE=16777216
readonly OUTPUT_NAME=candidate-mt6797-a72-frequency-zero-divider-398ca636
readonly DT_NAME=mt6797-gemini-pda-a72-frequency-thermal.dtb
readonly INITRAMFS_NAME=gemini-a72-frequency-thermal-initramfs.img
readonly BOOT_NAME=gemini-mt6797-a72-frequency-thermal.boot.img

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package DIR --ramdisk FILE --topology-dtb FILE --thermal-overlay FILE --output-parent DIR\n' "$0"
}

package=
ramdisk=
topology_dtb=
thermal_overlay=
output_parent=
while (($#)); do
	case "$1" in
	--package|--ramdisk|--topology-dtb|--thermal-overlay|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--ramdisk) ramdisk=$2 ;;
		--topology-dtb) topology_dtb=$2 ;;
		--thermal-overlay) thermal_overlay=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2 ;;
	*) usage >&2; exit 2 ;;
	esac
done
for command in awk basename chmod cmp find install jq mkdir mktemp mv python3 rm sha256sum sort tr wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
for directory in "$package" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] || die "missing or unsafe directory: $directory"
done
for file in "$ramdisk" "$topology_dtb" "$thermal_overlay"; do
	[[ -f "$file" && ! -L "$file" ]] || die "missing or unsafe input: $file"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repository=$(cd -- "$script_dir/../../.." && pwd -P)
package=$(cd -- "$package" && pwd -P)
ramdisk=$(cd -- "$(dirname -- "$ramdisk")" && pwd -P)/$(basename -- "$ramdisk")
topology_dtb=$(cd -- "$(dirname -- "$topology_dtb")" && pwd -P)/$(basename -- "$topology_dtb")
thermal_overlay=$(cd -- "$(dirname -- "$thermal_overlay")" && pwd -P)/$(basename -- "$thermal_overlay")
output_parent=$(cd -- "$output_parent" && pwd -P)
readonly script_dir repository package ramdisk topology_dtb thermal_overlay output_parent
[[ "$(basename -- "$package")" == "$PACKAGE_NAME" ]] || die 'package basename changed'
[[ "$(sha256sum "$package/SHA256SUMS" | awk '{print $1}')" == "$PACKAGE_MANIFEST_SHA256" ]] || die 'package manifest identity changed'
(cd "$package" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'package checksum validation failed'
[[ "$(sha256sum "$package/Image.gz" | awk '{print $1}')" == "$IMAGE_GZ_SHA256" ]] || die 'package Image.gz changed'
[[ "$(sha256sum "$package/System.map" | awk '{print $1}')" == "$SYSTEM_MAP_SHA256" ]] || die 'package System.map changed'
[[ "$(sha256sum "$package/kernel.config" | awk '{print $1}')" == "$CONFIG_SHA256" ]] || die 'package configuration changed'
[[ "$(sha256sum "$package/provenance/build.json" | awk '{print $1}')" == "$BUILD_JSON_SHA256" ]] || die 'package build provenance changed'
[[ "$(sha256sum "$package/dtbs/mediatek/mt6797-gemini-pda.dtb" | awk '{print $1}')" == "$PACKAGE_DTB_SHA256" ]] || die 'package DT changed'
[[ "$(sha256sum "$package/provenance/a41-record.json" | awk '{print $1}')" == "$A41_RECORD_SHA256" ]] || die 'package A41 record changed'
[[ "$(jq -er .repository_commit "$package/provenance/build.json")" == "$BUILD_COMMIT" ]] || die 'package commit changed'
[[ "$(jq -er .build_profile "$package/provenance/build.json")" == "$PROFILE" ]] || die 'package profile changed'
[[ "$(jq -er .kernel_release "$package/provenance/build.json")" == "$RELEASE" ]] || die 'package release changed'
[[ "$(sha256sum "$ramdisk" | awk '{print $1}')" == "$INITRAMFS_SHA256" ]] || die 'runtime-proven initramfs changed'
[[ "$(sha256sum "$topology_dtb" | awk '{print $1}')" == "$TOPOLOGY_DTB_SHA256" ]] || die 'runtime-proven topology DT changed'
[[ "$(sha256sum "$thermal_overlay" | awk '{print $1}')" == "$THERMAL_OVERLAY_SHA256" ]] || die 'runtime-proven thermal overlay changed'

config=$package/kernel.config
for symbol in \
	MTK_MT6797_A72_FREQUENCY_OBSERVER \
	MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER \
	MTK_MT6797_A72_ADMISSION_CONTROLLER \
	MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER \
	MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER \
	MTK_MT6797_A72_HOTPLUG_EXECUTOR \
	MTK_MT6797_A72_HOTPLUG_SNAPSHOT \
	MTK_MT6797_A72_HOTPLUG_BINDER_CORE \
	MTK_MT6797_A72_HOTPLUG_BINDING \
	PSTORE_GEMINI_MT6797_THERMAL_LEDGER THERMAL; do
	grep -qx "CONFIG_${symbol}=y" "$config" || die "production symbol is absent: $symbol"
done
grep -qx 'CONFIG_LOCALVERSION="-gemini-a72-frequency-thermal"' "$config" || die 'local version changed'
for symbol in KUNIT CPU_FREQ CPU_IDLE SUSPEND; do
	grep -qx "# CONFIG_${symbol} is not set" "$config" || die "closed policy changed: $symbol"
done

dt_builder=$script_dir/build-production-dtb.py
dt_validator=$script_dir/validate-production-dtb.py
serializer=$repository/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py
analyzer=$repository/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py
candidate_validator=$script_dir/validate-production-candidate.py
[[ "$(sha256sum "$dt_builder" | awk '{print $1}')" == "$DT_BUILDER_SHA256" ]] || die 'production DT builder changed'
[[ "$(sha256sum "$dt_validator" | awk '{print $1}')" == "$DT_VALIDATOR_SHA256" ]] || die 'production DT validator changed'
[[ "$(sha256sum "$serializer" | awk '{print $1}')" == "$SERIALIZER_SHA256" ]] || die 'container serializer changed'
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == "$ANALYZER_SHA256" ]] || die 'container analyzer changed'
[[ -f "$candidate_validator" && ! -L "$candidate_validator" ]] || die 'candidate validator is absent or unsafe'

output=$output_parent/$OUTPUT_NAME
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite final candidate'
case "$output_parent" in "$repository"|"$package") die 'unsafe output parent' ;; esac
work=$(mktemp -d "$output_parent/.a72-frequency-thermal.XXXXXXXX")
cleanup() { [[ ! -d "${work:-}" ]] || rm -rf -- "$work"; }
trap cleanup EXIT HUP INT TERM
stage=$work/$OUTPUT_NAME
replica=$work/replica
mkdir "$stage" "$replica"

install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
install -m 0600 "$package/provenance/build.json" "$stage/source-build.json"
install -m 0600 "$package/provenance/a41-record.json" "$stage/a41-record.json"
install -m 0600 "$package/SHA256SUMS" "$stage/package-SHA256SUMS"
install -m 0600 "$ramdisk" "$stage/$INITRAMFS_NAME"

dt_args=(
	--topology-dtb "$topology_dtb"
	--thermal-overlay "$thermal_overlay"
	--package-dtb "$package/dtbs/mediatek/mt6797-gemini-pda.dtb"
	--record-json "$package/provenance/a41-record.json"
)
python3 "$dt_builder" "${dt_args[@]}" --output "$stage/$DT_NAME" >"$stage/dt-build-validation.txt"
python3 "$dt_builder" "${dt_args[@]}" --output "$replica/$DT_NAME" >/dev/null
cmp -s "$stage/$DT_NAME" "$replica/$DT_NAME" || die 'independent DT compositions differ'
python3 "$dt_validator" "${dt_args[@]}" --candidate "$stage/$DT_NAME" >"$stage/dt-independent-validation.txt"

for root in "$stage" "$replica"; do
	python3 "$serializer" --kernel "$stage/Image.gz" --ramdisk "$stage/$INITRAMFS_NAME" \
		--dtb "$stage/$DT_NAME" --output "$root/$BOOT_NAME" --name gemini-a72freq \
		--cmdline bootopt=64S3,32N2,64N2 --kernel-addr 0x40200000 \
		--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
		--tags-addr 0x44000000 --lk-android8 >/dev/null
done
cmp -s "$stage/$BOOT_NAME" "$replica/$BOOT_NAME" || die 'independent container assemblies differ'
python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/$INITRAMFS_NAME" --expected-dtb "$stage/$DT_NAME" \
	--expected-name gemini-a72freq --expected-cmdline bootopt=64S3,32N2,64N2 \
	"$stage/$BOOT_NAME" >"$stage/container-validation.txt"
python3 - "$stage/$BOOT_NAME" "$stage/boot2-padded.img" "$BOOT2_SIZE" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_bytes()
size = int(sys.argv[3])
if not 0 < len(source) < size:
    raise SystemExit("raw candidate does not fit exact boot2 size")
Path(sys.argv[2]).write_bytes(source + bytes(size - len(source)))
PY
[[ "$(wc -c <"$stage/$BOOT_NAME" | tr -d ' ')" == "$RAW_SIZE" ]] || die 'raw candidate size changed'
[[ "$(sha256sum "$stage/$BOOT_NAME" | awk '{print $1}')" == "$RAW_SHA256" ]] || die 'raw candidate identity changed'
[[ "$(sha256sum "$stage/boot2-padded.img" | awk '{print $1}')" == "$PADDED_SHA256" ]] || die 'padded candidate identity changed'

{
	printf 'experiment=2026-09-04-mt6797-a72-frequency-observation\n'
	printf 'variant=stage18-thermal-frequency-zero-divider-repair\n'
	printf 'repository_commit=%s\nprofile=%s\nkernel_release=%s\n' "$BUILD_COMMIT" "$PROFILE" "$RELEASE"
	printf 'package_manifest_sha256=%s\nimage_gz_sha256=%s\nconfig_sha256=%s\n' "$PACKAGE_MANIFEST_SHA256" "$IMAGE_GZ_SHA256" "$CONFIG_SHA256"
	printf 'topology_dtb_sha256=%s\nthermal_overlay_sha256=%s\nproduction_dtb_sha256=%s\n' "$TOPOLOGY_DTB_SHA256" "$THERMAL_OVERLAY_SHA256" "$PRODUCTION_DTB_SHA256"
	printf 'a41_record_sha256=%s\ninitramfs_sha256=%s\n' "$A41_RECORD_SHA256" "$INITRAMFS_SHA256"
	printf 'candidate_raw_sha256=%s\ncandidate_raw_size=%s\n' "$RAW_SHA256" "$RAW_SIZE"
	printf 'candidate_padded_sha256=%s\ncandidate_padded_size=%s\n' "$PADDED_SHA256" "$BOOT2_SIZE"
	printf 'dt_delta=exact-thermal-transform-plus-one-package-provenance-leaf\n'
	printf 'cpu_topology=4+4+2\nthermal_zones=1\nthermal_trips=0\ncooling_maps=0\n'
	printf 'frequency_observer_attempts=3\ncpufreq_idle_suspend=disabled\n'
	printf 'device_action=none\nhardware_write=none\n'
} >"$stage/provenance.txt"
(cd "$stage" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'candidate manifest validation failed'
python3 "$candidate_validator" --repository "$repository" --package "$package" \
	--ramdisk "$ramdisk" --topology-dtb "$topology_dtb" \
	--thermal-overlay "$thermal_overlay" --candidate "$stage" >"$stage/candidate-validation.txt"
(cd "$stage" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'final candidate manifest validation failed'
mv "$stage" "$output"
chmod 0600 "$output"/*
trap - EXIT HUP INT TERM
rm -rf -- "$work"
printf 'validation=mt6797-a72-frequency-thermal-production-candidate-build\n'
printf 'artifact=%s\ncandidate_raw_sha256=%s\ncandidate_padded_sha256=%s\n' "$output" "$RAW_SHA256" "$PADDED_SHA256"
printf 'device_action=none\nhardware_write=none\nresult=pass\n'
