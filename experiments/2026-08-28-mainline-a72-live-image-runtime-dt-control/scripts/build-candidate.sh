#!/usr/bin/env bash

# Cross the exact current production Image with the closest runtime-proven DT.
set -euo pipefail
export LC_ALL=C
umask 077

readonly COMMIT=c147e2ddc1acc93827b59f8e3bb38b9b2f4d3fb2
readonly PROFILE=a72-admission-live-trigger-candidate
readonly RELEASE=7.1.3-gemini-a72-admission-live
readonly IMAGE_SHA256=96c86abe4084333bf462f028c217c41eb0342ad080dae3014b439eef0f0cab18
readonly IMAGE_GZ_SHA256=4b884c0176d4d3e7d96c35f84ce36f0e591b2b7a411fe217f43427824f8377f4
readonly CONFIG_SHA256=265f610b5200dff9184cd0dcca3c6993b572e167316e149a9856f05723c9eebd
readonly SYSTEM_MAP_SHA256=4d6e3ad347b755907a99b0c7dc0f1cb91fff00f533f21baeab663e77373731bd
readonly BUILD_JSON_SHA256=c1009fab6642739161d913bdb676fb027d7849dd60c61e1291ec04a8c2541241
readonly PACKAGE_MANIFEST_SHA256=0b6c85b3d6d870c22513f64d3b61d0944a3e9729ad26c0297b4d29414d561f41
readonly CONTROL_DTB_SHA256=90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d
readonly RAMDISK_SHA256=e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f
readonly SERIALIZER_SHA256=569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95
readonly RAW_SHA256=35d0c6ef99f69a1dd00afac390f8d68b5514577e38819448b7465c44243c2f12
readonly PADDED_SHA256=c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab
readonly RAW_SIZE=6934528
readonly BOOT2_SIZE=16777216
readonly BOOT_NAME=gemini-a72dtctl
readonly BOOT_CMDLINE=bootopt=64S3,32N2,64N2
readonly BOOT_FILE=gemini-mt6797-a72-live-image-runtime-dt-control.boot.img

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --package DIR --ramdisk FILE --control-dtb FILE --output-parent DIR\n' "$0"; }
package=''
ramdisk=''
control_dtb=''
output_parent=''
while (($#)); do
	case "$1" in
	--package) package=${2:-}; shift 2 ;;
	--ramdisk) ramdisk=${2:-}; shift 2 ;;
	--control-dtb) control_dtb=${2:-}; shift 2 ;;
	--output-parent) output_parent=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$package" && -n "$ramdisk" && -n "$control_dtb" && -n "$output_parent" ]] || { usage >&2; exit 2; }
for command in awk chmod cmp cp dd dtc find grep jq mkdir mktemp mv python3 rm rmdir sha256sum sort stat strings truncate wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
package=$(cd -- "$package" && pwd -P)
ramdisk=$(cd -- "$(dirname -- "$ramdisk")" && pwd -P)/$(basename -- "$ramdisk")
control_dtb=$(cd -- "$(dirname -- "$control_dtb")" && pwd -P)/$(basename -- "$control_dtb")
output_parent=$(cd -- "$output_parent" && pwd -P)
case "$output_parent/" in "$repo_root/artifacts/"*) ;; *) die 'output parent must be below ignored artifacts' ;; esac

image="$package/Image"; image_gz="$package/Image.gz"; config="$package/kernel.config"
system_map="$package/System.map"; build_json="$package/provenance/build.json"; manifest="$package/SHA256SUMS"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in "$image" "$image_gz" "$config" "$system_map" "$build_json" "$manifest" "$ramdisk" "$control_dtb" "$serializer" "$analyzer"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || die "missing, empty, or unsafe input: $input"
done
check_hash() { [[ "$(sha256sum "$1" | awk '{print $1}')" == "$2" ]] || die "$3 changed"; }
check_hash "$image" "$IMAGE_SHA256" Image
check_hash "$image_gz" "$IMAGE_GZ_SHA256" Image.gz
check_hash "$config" "$CONFIG_SHA256" configuration
check_hash "$system_map" "$SYSTEM_MAP_SHA256" System.map
check_hash "$build_json" "$BUILD_JSON_SHA256" build.json
check_hash "$manifest" "$PACKAGE_MANIFEST_SHA256" package-manifest
check_hash "$control_dtb" "$CONTROL_DTB_SHA256" runtime-proven-DTB
check_hash "$ramdisk" "$RAMDISK_SHA256" serviceability-ramdisk
check_hash "$serializer" "$SERIALIZER_SHA256" serializer
check_hash "$analyzer" "$ANALYZER_SHA256" analyzer
(cd "$package" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'package checksums failed'
[[ "$(jq -er .repository_commit "$build_json")" == "$COMMIT" &&
	"$(jq -er .build_profile "$build_json")" == "$PROFILE" &&
	"$(jq -er .kernel_release "$build_json")" == "$RELEASE" ]] || die 'package provenance changed'
grep -qx 'CONFIG_LOCALVERSION="-gemini-a72-admission-live"' "$config" || die 'local version changed'
grep -qx 'CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y' "$config" || die 'live trigger is absent from current Image'

workdir=$(mktemp -d "$output_parent/.a72-live-image-runtime-dt-control.XXXXXXXX")
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
stage="$workdir/stage"; replica="$workdir/replica"; mkdir "$stage" "$replica"
dtc -I dtb -O dts -o "$workdir/control.dts" "$control_dtb" 2>"$workdir/dtc.stderr"
[[ "$(grep -Fc 'mediatek,mt6797-a72-platform-state' "$workdir/control.dts")" == 1 ]] || die 'platform-state node changed'
[[ "$(grep -Fc 'mediatek,mt6797-a72-platform-provider-clock-observer' "$workdir/control.dts")" == 1 ]] || die 'composed observer node changed'
[[ "$(grep -Ec 'mt6797-a72-admission-controller|mt6797-a72-admission-binder' "$workdir/control.dts")" == 0 ]] || die 'admission node leaked into control DT'

for root in "$stage" "$replica"; do
	python3 "$serializer" --kernel "$image_gz" --ramdisk "$ramdisk" --dtb "$control_dtb" --output "$root/$BOOT_FILE" --name "$BOOT_NAME" --cmdline "$BOOT_CMDLINE" --kernel-addr 0x40200000 --ramdisk-addr 0x45000000 --second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 >"$root/serializer.txt"
done
cmp -s "$stage/$BOOT_FILE" "$replica/$BOOT_FILE" || die 'independent raw assemblies differ'
cp "$stage/$BOOT_FILE" "$stage/boot2-padded.img"; truncate -s "$BOOT2_SIZE" "$stage/boot2-padded.img"
dd if=/dev/zero of="$replica/boot2-padded.img" bs=1048576 count=16 status=none
dd if="$replica/$BOOT_FILE" of="$replica/boot2-padded.img" bs=1048576 conv=notrunc status=none
cmp -s "$stage/boot2-padded.img" "$replica/boot2-padded.img" || die 'independent padding differs'
python3 "$analyzer" --validate-lk --expected-image-gz "$image_gz" --expected-ramdisk "$ramdisk" --expected-dtb "$control_dtb" --expected-name "$BOOT_NAME" --expected-cmdline "$BOOT_CMDLINE" "$stage/$BOOT_FILE" >"$stage/container-analysis.txt"
[[ "$(grep -c '^gate_.*=yes$' "$stage/container-analysis.txt")" == 32 ]] || die 'LK gate count changed'
grep -qx 'lk_validation=passed' "$stage/container-analysis.txt" || die 'LK validation failed'
raw_sha=$(sha256sum "$stage/$BOOT_FILE" | awk '{print $1}'); padded_sha=$(sha256sum "$stage/boot2-padded.img" | awk '{print $1}')
[[ "$(stat -f '%z' "$stage/$BOOT_FILE" 2>/dev/null || stat -c '%s' "$stage/$BOOT_FILE")" == "$RAW_SIZE" && "$raw_sha" == "$RAW_SHA256" ]] || die 'raw candidate changed'
[[ "$(stat -f '%z' "$stage/boot2-padded.img" 2>/dev/null || stat -c '%s' "$stage/boot2-padded.img")" == "$BOOT2_SIZE" && "$padded_sha" == "$PADDED_SHA256" ]] || die 'padded candidate changed'
grep -v '^output=' "$stage/serializer.txt" >"$stage/serializer.normalized"; mv "$stage/serializer.normalized" "$stage/serializer.txt"
{
	printf 'experiment=2026-08-28-mainline-a72-live-image-runtime-dt-control\n'
	printf 'repository_commit=%s\nprofile=%s\nkernel_release=%s\n' "$COMMIT" "$PROFILE" "$RELEASE"
	printf 'image_sha256=%s\nimage_gzip_sha256=%s\nconfig_sha256=%s\nsystem_map_sha256=%s\n' "$IMAGE_SHA256" "$IMAGE_GZ_SHA256" "$CONFIG_SHA256" "$SYSTEM_MAP_SHA256"
	printf 'control_dtb_sha256=%s\ncontrol_dtb_runtime_candidate=6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7\n' "$CONTROL_DTB_SHA256"
	printf 'ramdisk_sha256=%s\ncandidate_sha256=%s\ncandidate_size=%s\npadded_sha256=%s\npadded_size=%s\n' "$RAMDISK_SHA256" "$RAW_SHA256" "$RAW_SIZE" "$PADDED_SHA256" "$BOOT2_SIZE"
	printf 'lk_name=%s\nlk_cmdline=%s\nlk_gates=32-of-32\n' "$BOOT_NAME" "$BOOT_CMDLINE"
	printf 'controller_nodes=0\nbinder_nodes=0\ncpu8_requests=0\ncpu9_requests=0\ncpu_off_requests=0\nretries=0\n'
	printf 'independent_raw_assemblies=byte-identical\nindependent_padding_constructions=byte-identical\n'
	printf 'device_access=none\nhardware_write=none\nnative_vm_build=none\nboot_candidate=pending-independent-validation\n'
} >"$stage/provenance.txt"
{
	printf 'validation=current-image-runtime-dt-package\npackage_manifest_sha256=%s\nsha256sums=passed\n' "$PACKAGE_MANIFEST_SHA256"
	printf 'dt_semantics=platform-provider-protected-clock-prefix-without-admission-nodes\nresult=pass\n'
} >"$stage/package-validation.txt"
(cd "$stage" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'artifact manifest failed'
chmod 0600 "$stage"/*
output_name="candidate-a72-live-image-runtime-dt-control-${RAW_SHA256:0:8}"
output="$output_parent/$output_name"; [[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output'
mv "$stage" "$output"; stage=
rm -rf -- "$replica"
rm -f -- "$workdir/control.dts" "$workdir/dtc.stderr"
rmdir "$workdir"; workdir=; trap - EXIT HUP INT TERM
printf 'validation=a72-live-image-runtime-dt-control-build\nartifact=%s\ncandidate_sha256=%s\npadded_sha256=%s\ndevice_access=none\nhardware_write=none\n' "$output" "$RAW_SHA256" "$PADDED_SHA256"
