#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package AN_PACKAGE --ah-artifact AH_ARTIFACT --output-parent DIR\n' "$0" >&2
}

package=
ah_artifact=
output_parent=
while (($#)); do
	case "$1" in
	--package|--ah-artifact|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--ah-artifact) ah_artifact=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die 'run in the Linux recovery VM'
case "$(uname -m)" in aarch64|arm64) ;; *) die 'expected Linux AArch64' ;; esac
for directory in "$package" "$ah_artifact" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] || \
		die "unsafe or missing directory: $directory"
done
for command in awk basename chmod cmp find grep install mkdir mktemp mv \
	python3 rm rmdir sed sha256sum sort tr uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || \
		die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
ah_artifact="$(cd -- "$ah_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$package"|"$package"/*|\
"$ah_artifact"|"$ah_artifact"/*)
	die 'output parent must be outside the repository and selected inputs'
	;;
esac

manifest="$repo_root/kernel/manifest.json"
package_validator="$script_dir/validate-package.py"
dtb_builder="$script_dir/build-an-dtb.sh"
dtb_validator="$script_dir/validate-dtb-delta.py"
boot_validator="$script_dir/validate-boot.py"
normalizer="$script_dir/normalize-build-json.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
patch_0094="$repo_root/patches/v7.1.3/0094-dt-bindings-soc-mediatek-add-MT6797-DVFSP-handoff-observer.patch"
patch_0095="$repo_root/patches/v7.1.3/0095-soc-mediatek-add-MT6797-DVFSP-handoff-observer.patch"
for input in "$manifest" "$package_validator" "$dtb_builder" "$dtb_validator" \
	"$boot_validator" "$normalizer" "$serializer" "$analyzer" \
	"$patch_0094" "$patch_0095"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || \
		die "repository input missing or unsafe: $input"
done
[[ "$(sha256sum "$serializer" | awk '{ print $1 }')" == \
	569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4 ]] || \
	die 'source-pinned Android-v0 serializer changed'
[[ "$(sha256sum "$analyzer" | awk '{ print $1 }')" == \
	aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95 ]] || \
	die 'source-pinned LK analyzer changed'
[[ "$(sha256sum "$patch_0094" | awk '{ print $1 }')" == \
	2e20664ff4cb08a4f2296bdafb84148d4e4cf79b1eb17b3e92f6a7bb145abe59 ]] || \
	die 'source-pinned patch 0094 changed'
[[ "$(sha256sum "$patch_0095" | awk '{ print $1 }')" == \
	4ac79ec2653e829fef973e85176cc00c7be908983cb5261d940b3395332ae764 ]] || \
	die 'source-pinned patch 0095 changed'

readonly PROFILE=observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-observer
readonly AH_NAME=candidate-AH-ad-contract-af-kernel-split-e5ba6ee0
readonly AH_MANIFEST_SHA256=04b25bfc5e72645318273e03adc80191df7d52994acc7ade8202a64d95223997
readonly AH_DTB_SHA256=27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845
readonly AH_INITRAMFS_SHA256=166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3
readonly AH_KEYMAP_SHA256=02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c
readonly AH_DTB=mt6797-gemini-pda-ad-contract-af-kernel-split.dtb
readonly AH_INITRAMFS=gemini-ad-contract-af-kernel-split-initramfs.img
readonly AN_DTB=mt6797-gemini-pda-dvfsp-handoff-observer.dtb
readonly AN_INITRAMFS=gemini-dvfsp-handoff-observer-initramfs.img
readonly AN_BOOT=gemini-mt6797-dvfsp-handoff-observer.boot.img

[[ "$(basename -- "$ah_artifact")" == "$AH_NAME" ]] || \
	die 'exact Candidate AH artifact basename changed'
for member in SHA256SUMS "$AH_DTB" "$AH_INITRAMFS" gemini-us.bkeymap \
	console-unicode-mode console-keymap-verify input-event-capture; do
	[[ -f "$ah_artifact/$member" && ! -L "$ah_artifact/$member" ]] || \
		die "Candidate AH member missing or unsafe: $member"
done
[[ "$(sha256sum "$ah_artifact/SHA256SUMS" | awk '{ print $1 }')" == \
	"$AH_MANIFEST_SHA256" ]] || die 'exact Candidate AH manifest changed'
(cd "$ah_artifact" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate AH manifest failed'
[[ "$(sha256sum "$ah_artifact/$AH_DTB" | awk '{ print $1 }')" == \
	"$AH_DTB_SHA256" ]] || die 'exact Candidate AH final DT changed'
[[ "$(sha256sum "$ah_artifact/$AH_INITRAMFS" | awk '{ print $1 }')" == \
	"$AH_INITRAMFS_SHA256" ]] || die 'exact Candidate AH initramfs changed'
[[ "$(sha256sum "$ah_artifact/gemini-us.bkeymap" | awk '{ print $1 }')" == \
	"$AH_KEYMAP_SHA256" ]] || die 'exact Candidate AH keymap changed'

workdir="$(mktemp -d "$output_parent/.candidate-AN-dvfsp-observer.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

python3 "$package_validator" --repository "$repo_root" --package "$package" \
	>"$stage/package-validation.raw"
sed -e "s|$repo_root|@REPOSITORY@|g" -e "s|$workdir|@WORK@|g" \
	-e "s|$package|@AN_PACKAGE@|g" \
	-e 's/^calibration_package_manifest_sha256=.*/calibration_package_manifest_sha256=validated-build-specific-generation-manifest/' \
	"$stage/package-validation.raw" >"$stage/package-validation.txt"
rm "$stage/package-validation.raw"

install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
python3 "$normalizer" --input "$package/provenance/build.json" \
	--output "$stage/source-build.json"
install -m 0600 "$ah_artifact/$AH_INITRAMFS" "$stage/$AN_INITRAMFS"
install -m 0600 "$ah_artifact/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$ah_artifact/console-unicode-mode" "$stage/console-unicode-mode"
install -m 0755 "$ah_artifact/console-keymap-verify" \
	"$stage/console-keymap-verify"
install -m 0755 "$ah_artifact/input-event-capture" \
	"$stage/input-event-capture"

bash "$dtb_builder" --ah-dtb "$ah_artifact/$AH_DTB" \
	--output "$stage/$AN_DTB" >"$stage/dtb-validation.raw"
bash "$dtb_builder" --ah-dtb "$ah_artifact/$AH_DTB" \
	--output "$replica/$AN_DTB" >/dev/null
cmp -s "$stage/$AN_DTB" "$replica/$AN_DTB" || \
	die 'two independent Candidate AN final-DT derivations differ'
sed -e "s|$stage/$AN_DTB|@AN_DTB@|g" \
	"$stage/dtb-validation.raw" >"$stage/dtb-validation.txt"
rm "$stage/dtb-validation.raw"

candidate="$stage/$AN_BOOT"
replica_boot="$replica/$AN_BOOT"
boot_cmdline=bootopt=64S3,32N2,64N2
for output in "$candidate" "$replica_boot"; do
	python3 "$serializer" --kernel "$stage/Image.gz" \
		--ramdisk "$stage/$AN_INITRAMFS" --dtb "$stage/$AN_DTB" \
		--output "$output" --name gemini-obs-L --cmdline "$boot_cmdline" \
		--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
		--second-addr 0x40f00000 --tags-addr 0x44000000 \
		--lk-android8 >"${output}.serializer"
done
cmp -s "$candidate" "$replica_boot" || \
	die 'two independent Candidate AN container assemblies differ'
grep -v '^output=' "${candidate}.serializer" >"$stage/serializer.txt"
rm "${candidate}.serializer" "${replica_boot}.serializer"

python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/$AN_INITRAMFS" \
	--expected-dtb "$stage/$AN_DTB" --expected-name gemini-obs-L \
	--expected-cmdline "$boot_cmdline" "$candidate" >"$stage/analysis.raw"
sed -e "s|$workdir|@WORK@|g" -e "s|$repo_root|@REPOSITORY@|g" \
	"$stage/analysis.raw" >"$stage/analysis.txt"
rm "$stage/analysis.raw"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] || \
	die 'LK analyzer did not emit exactly 32 gates'

python3 "$boot_validator" --candidate "$candidate" \
	--image-gz "$stage/Image.gz" --system-map "$stage/System.map" \
	--kernel-config "$stage/kernel.config" --dtb "$stage/$AN_DTB" \
	--ah-dtb "$ah_artifact/$AH_DTB" --initramfs "$stage/$AN_INITRAMFS" \
	>"$stage/boot-validation.txt"

candidate_sha256="$(sha256sum "$candidate" | awk '{ print $1 }')"
candidate_size="$(wc -c <"$candidate" | tr -d ' ')"
image_sha256="$(sha256sum "$stage/Image.gz" | awk '{ print $1 }')"
system_map_sha256="$(sha256sum "$stage/System.map" | awk '{ print $1 }')"
dtb_sha256="$(sha256sum "$stage/$AN_DTB" | awk '{ print $1 }')"
config_sha256="$(sha256sum "$stage/kernel.config" | awk '{ print $1 }')"
source_build_sha256="$(sha256sum "$stage/source-build.json" | awk '{ print $1 }')"
{
	printf 'experiment=2026-07-24-mt6797-dvfsp-handoff-observer\n'
	printf 'candidate_label=AN\nkernel_profile=%s\n' "$PROFILE"
	printf 'candidate_sha256=%s\ncandidate_size=%s\n' \
		"$candidate_sha256" "$candidate_size"
	printf 'candidate_image_gz_sha256=%s\n' "$image_sha256"
	printf 'candidate_system_map_sha256=%s\n' "$system_map_sha256"
	printf 'candidate_dtb_sha256=%s\n' "$dtb_sha256"
	printf 'candidate_config_sha256=%s\n' "$config_sha256"
	printf 'candidate_source_build_sha256=%s\n' "$source_build_sha256"
	printf 'ah_raw_sha256=e5ba6ee0a257b804a02af11b83e733f861b89de17470470a497f07056b6b3197\n'
	printf 'ah_dtb_sha256=%s\n' "$AH_DTB_SHA256"
	printf 'candidate_initramfs_sha256=%s\n' "$AH_INITRAMFS_SHA256"
	printf 'candidate_keymap_sha256=%s\n' "$AH_KEYMAP_SHA256"
	printf 'patch_0094_sha256=2e20664ff4cb08a4f2296bdafb84148d4e4cf79b1eb17b3e92f6a7bb145abe59\n'
	printf 'patch_0095_sha256=4ac79ec2653e829fef973e85176cc00c7be908983cb5261d940b3395332ae764\n'
	# Frozen reproduced-artifact label: this means AH's hardware contract,
	# not whole-artifact byte identity. AN has a different observer kernel.
	# Keep the historical bytes exact; README.md records the scope correction.
	printf 'functional_baseline=byte-exact-hardware-passed-candidate-ah\n'
	printf 'final_dtb_baseline=exact-candidate-ah-final-dtb\n'
	printf 'final_dtb_delta=one-read-only-dvfsp-observer-node\n'
	printf 'initramfs_keyboard_console_usb_reboot=byte-exact-candidate-ah\n'
	printf 'observer_snapshots=3\nobserver_mmio=read-only\n'
	printf 'i2c6=disabled\nda9214_node=absent\na72_power_node=absent\n'
	printf 'maxcpus=8\na72_observer_initcall=blacklisted\n'
	printf 'dvfsp_observer_initcall=enabled\n'
	printf 'cpu8_cpu9_request=none\nregulator_operation=none\n'
	printf 'storage_access=none\nwatchdog_userspace=none\nautomatic_reboot=none\n'
	printf 'artifact_builder_device_access=none\nflash=none\nruntime_result=not-tested\n'
} >"$stage/provenance.txt"

expected_pre_manifest="$(printf '%s\n' Image.gz System.map analysis.txt \
	boot-validation.txt console-keymap-verify console-unicode-mode \
	dtb-validation.txt "$AN_BOOT" "$AN_INITRAMFS" gemini-us.bkeymap \
	input-event-capture kernel.config "$AN_DTB" package-validation.txt \
	provenance.txt serializer.txt source-build.json | sort)"
actual_inventory="$(find "$stage" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)"
[[ "$actual_inventory" == "$expected_pre_manifest" ]] || \
	die 'Candidate AN output inventory changed'
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate AN artifact manifest failed'
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" "$stage/console-unicode-mode" \
	"$stage/input-event-capture"

output_name="candidate-AN-mt6797-dvfsp-handoff-observer-${candidate_sha256:0:8}"
artifact="$workdir/$output_name"
mv -n "$stage" "$artifact"
stage=
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || \
	die "refusing to overwrite $output"
mv -n "$artifact" "$output"
[[ -d "$output" && ! -e "$artifact" ]] || \
	die 'exclusive Candidate AN publication failed'
rm -rf -- "$replica"
rmdir "$workdir"
workdir=
trap - EXIT
printf 'validation=candidate-an-mt6797-dvfsp-handoff-observer\n'
printf 'artifact=%s\ncandidate=%s/%s\n' "$output" "$output" "$AN_BOOT"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' \
	"$candidate_sha256" "$candidate_size"
printf 'dtb_sha256=%s\nruntime_result=not-tested\n' "$dtb_sha256"
