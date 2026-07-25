#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package AE_PACKAGE --baseline-package AD_PACKAGE --ad-artifact AD_ARTIFACT --output-parent DIR\n' "$0" >&2
}

package=
baseline_package=
ad_artifact=
output_parent=
while (($#)); do
	case "$1" in
	--package|--baseline-package|--ad-artifact|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--baseline-package) baseline_package=$2 ;;
		--ad-artifact) ad_artifact=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die 'run in the Linux development VM'
case "$(uname -m)" in aarch64|arm64) ;; *) die 'expected Linux AArch64' ;; esac
for directory in "$package" "$baseline_package" "$ad_artifact" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] || die "unsafe or missing directory: $directory"
done
for command in awk basename chmod cmp find grep install mkdir mktemp mv python3 \
	rm sed sha256sum sort tr uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
baseline_package="$(cd -- "$baseline_package" && pwd -P)"
ad_artifact="$(cd -- "$ad_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$package"|"$package"/*|"$baseline_package"|"$baseline_package"/*|"$ad_artifact"|"$ad_artifact"/*)
	die 'output parent must be outside the repository and all selected inputs'
	;;
esac

manifest="$repo_root/kernel/manifest.json"
package_validator="$script_dir/validate-package.py"
boot_validator="$script_dir/validate-boot.py"
normalizer="$script_dir/normalize-build-json.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in "$manifest" "$package_validator" "$boot_validator" "$normalizer" \
	"$serializer" "$analyzer"; do
	[[ -s "$input" && ! -L "$input" ]] || die "repository input missing or unsafe: $input"
done

readonly AD_NAME=candidate-AD-smp8-final-a1b61d8c
readonly AD_MANIFEST_SHA256=c3aeccf2e6e18a0c4769b909ccf45a77f75cc3677fe61fbd786d0925154fc51f
readonly AD_BOOT_SHA256=a1b61d8c34b5a447f1f672663f4e74fed6eb465b90154392a3c42f4db030826b
readonly AD_INITRAMFS_SHA256=166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3
readonly AD_IMAGE_GZ_SHA256=1ab084bd427f9fade4adb43a83cca879c3289929485ad1469c6dffa539d3548b
readonly AD_DTB_SHA256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
readonly AD_KEYMAP_SHA256=02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c
[[ "$(basename -- "$ad_artifact")" == "$AD_NAME" ]] || die 'exact Candidate AD artifact basename changed'
for member in SHA256SUMS gemini-smp8.boot.img gemini-usb-gadget-ethernet-initramfs.img \
	Image.gz System.map mt6797-gemini-pda-smp8.dtb gemini-us.bkeymap \
	console-unicode-mode console-keymap-verify input-event-capture source-build.json; do
	[[ -f "$ad_artifact/$member" && ! -L "$ad_artifact/$member" ]] || \
		die "Candidate AD member missing or unsafe: $member"
done
[[ "$(sha256sum "$ad_artifact/SHA256SUMS" | awk '{print $1}')" == "$AD_MANIFEST_SHA256" ]] || die 'exact Candidate AD manifest changed'
(cd "$ad_artifact" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'Candidate AD manifest failed'
[[ "$(sha256sum "$ad_artifact/gemini-smp8.boot.img" | awk '{print $1}')" == "$AD_BOOT_SHA256" ]] || die 'exact Candidate AD boot changed'
[[ "$(sha256sum "$ad_artifact/gemini-usb-gadget-ethernet-initramfs.img" | awk '{print $1}')" == "$AD_INITRAMFS_SHA256" ]] || die 'exact Candidate AD initramfs changed'
[[ "$(sha256sum "$ad_artifact/Image.gz" | awk '{print $1}')" == "$AD_IMAGE_GZ_SHA256" ]] || die 'exact Candidate AD Image.gz changed'
[[ "$(sha256sum "$ad_artifact/mt6797-gemini-pda-smp8.dtb" | awk '{print $1}')" == "$AD_DTB_SHA256" ]] || die 'exact Candidate AD DTB changed'
[[ "$(sha256sum "$ad_artifact/gemini-us.bkeymap" | awk '{print $1}')" == "$AD_KEYMAP_SHA256" ]] || die 'exact Candidate AD keymap changed'

workdir="$(mktemp -d "$output_parent/.candidate-AE-observer.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

python3 "$package_validator" --baseline "$baseline_package" --candidate "$package" \
	--manifest "$manifest" >"$stage/package-validation.raw"
sed -e "s|$repo_root|@REPOSITORY@|g" -e "s|$workdir|@WORK@|g" \
	-e "s|$package|@AE_PACKAGE@|g" -e "s|$baseline_package|@AD_PACKAGE@|g" \
	"$stage/package-validation.raw" >"$stage/package-validation.txt"
rm "$stage/package-validation.raw"

install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
python3 "$normalizer" --input "$package/provenance/build.json" --output "$stage/source-build.json"
install -m 0600 "$package/dtbs/mediatek/mt6797-gemini-pda.dtb" \
	"$stage/mt6797-gemini-pda-a72-observer.dtb"
install -m 0600 "$ad_artifact/gemini-usb-gadget-ethernet-initramfs.img" \
	"$stage/gemini-a72-observer-initramfs.img"
install -m 0600 "$ad_artifact/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$ad_artifact/console-unicode-mode" "$stage/console-unicode-mode"
install -m 0755 "$ad_artifact/console-keymap-verify" "$stage/console-keymap-verify"
install -m 0755 "$ad_artifact/input-event-capture" "$stage/input-event-capture"

candidate="$stage/gemini-a72-observer.boot.img"
replica_boot="$replica/gemini-a72-observer.boot.img"
bootopt=bootopt=64S3,32N2,64N2
for output in "$candidate" "$replica_boot"; do
	python3 "$serializer" --kernel "$stage/Image.gz" \
		--ramdisk "$stage/gemini-a72-observer-initramfs.img" \
		--dtb "$stage/mt6797-gemini-pda-a72-observer.dtb" --output "$output" \
		--name gemini-obs-L --cmdline "$bootopt" --kernel-addr 0x40200000 \
		--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
		--tags-addr 0x44000000 --lk-android8 >"${output}.serializer"
done
cmp -s "$candidate" "$replica_boot" || die 'two Candidate AE container constructions differ'
grep -v '^output=' "${candidate}.serializer" >"$stage/serializer.txt"
rm "${candidate}.serializer" "${replica_boot}.serializer"

python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/gemini-a72-observer-initramfs.img" \
	--expected-dtb "$stage/mt6797-gemini-pda-a72-observer.dtb" \
	--expected-name gemini-obs-L --expected-cmdline "$bootopt" "$candidate" \
	>"$stage/analysis.raw"
sed -e "s|$workdir|@WORK@|g" -e "s|$repo_root|@REPOSITORY@|g" \
	"$stage/analysis.raw" >"$stage/analysis.txt"
rm "$stage/analysis.raw"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] || die 'LK analyzer did not emit 32 gates'
python3 "$boot_validator" --candidate "$candidate" --image-gz "$stage/Image.gz" \
	--dtb "$stage/mt6797-gemini-pda-a72-observer.dtb" \
	--initramfs "$stage/gemini-a72-observer-initramfs.img" \
	>"$stage/boot-validation.txt"

candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
candidate_size="$(wc -c <"$candidate" | tr -d ' ')"
image_sha256="$(sha256sum "$stage/Image.gz" | awk '{print $1}')"
dtb_sha256="$(sha256sum "$stage/mt6797-gemini-pda-a72-observer.dtb" | awk '{print $1}')"
config_sha256="$(sha256sum "$stage/kernel.config" | awk '{print $1}')"
source_build_sha256="$(sha256sum "$stage/source-build.json" | awk '{print $1}')"
{
	printf 'experiment=2026-07-21-cortex-a72-power-observer\n'
	printf 'candidate_label=AE\n'
	printf 'kernel_profile=observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer\n'
	printf 'candidate_sha256=%s\n' "$candidate_sha256"
	printf 'candidate_size=%s\n' "$candidate_size"
	printf 'candidate_image_gz_sha256=%s\n' "$image_sha256"
	printf 'candidate_dtb_sha256=%s\n' "$dtb_sha256"
	printf 'candidate_config_sha256=%s\n' "$config_sha256"
	printf 'candidate_source_build_sha256=%s\n' "$source_build_sha256"
	printf 'ad_boot_sha256=%s\n' "$AD_BOOT_SHA256"
	printf 'candidate_initramfs_sha256=%s\n' "$AD_INITRAMFS_SHA256"
	printf 'candidate_keymap_sha256=%s\n' "$AD_KEYMAP_SHA256"
	printf 'initramfs_lineage=byte-exact-candidate-ad\n'
	printf 'console_keyboard_usb_reboot=byte-exact-candidate-ad\n'
	printf 'kernel_dtb_delta=da9214-toprgu-a72-observer\n'
	printf 'cpu_policy=maxcpus-8-cpu8-cpu9-not-requested\n'
	printf 'observer_ready=0\nobserver_hooks_armed=0\nobserver_mode=observe-only\n'
	printf 'regulator_policy=ignore-unused-preserve-firmware-state\n'
	printf 'storage_access=none\nwatchdog_userspace=none\nautomatic_reboot=none\n'
	printf 'hardware_write=none\nflash=none\nruntime_result=not-tested\n'
} >"$stage/provenance.txt"

expected_inventory="$(printf '%s\n' Image.gz System.map analysis.txt boot-validation.txt \
	console-keymap-verify console-unicode-mode gemini-a72-observer.boot.img \
	gemini-a72-observer-initramfs.img gemini-us.bkeymap input-event-capture \
	kernel.config mt6797-gemini-pda-a72-observer.dtb package-validation.txt \
	provenance.txt serializer.txt source-build.json | sort)"
actual_inventory="$(find "$stage" -mindepth 1 -maxdepth 1 -type f -printf '%f\n' | sort)"
[[ "$actual_inventory" == "$expected_inventory" ]] || die 'Candidate AE output inventory changed'
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'Candidate AE manifest failed'
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" "$stage/console-unicode-mode" "$stage/input-event-capture"

output_name="candidate-AE-a72-observer-${candidate_sha256:0:8}"
artifact="$workdir/$output_name"
mv --no-clobber --no-target-directory "$stage" "$artifact"
stage=
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv --no-clobber --no-target-directory "$artifact" "$output"
workdir=
trap - EXIT
printf 'validation=candidate-ae-a72-observer\nartifact=%s\ncandidate=%s/gemini-a72-observer.boot.img\n' "$output" "$output"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$candidate_sha256" "$candidate_size"
printf 'initramfs_sha256=%s\nruntime_result=not-tested\n' "$AD_INITRAMFS_SHA256"
