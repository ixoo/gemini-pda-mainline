#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package AD_PACKAGE --baseline-package AB_PACKAGE --ac-artifact AC_ARTIFACT --output-parent DIR\n' "$0" >&2
}

package=
baseline_package=
ac_artifact=
output_parent=
while (($#)); do
	case "$1" in
	--package|--baseline-package|--ac-artifact|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--baseline-package) baseline_package=$2 ;;
		--ac-artifact) ac_artifact=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die 'run in the Linux development VM'
case "$(uname -m)" in aarch64|arm64) ;; *) die 'expected Linux aarch64' ;; esac
for directory in "$package" "$baseline_package" "$ac_artifact" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] || die "unsafe or missing directory: $directory"
done
for command in awk basename chmod cmp find git grep install mkdir mktemp mv \
	python3 rm sed sha256sum sort tr uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
baseline_package="$(cd -- "$baseline_package" && pwd -P)"
ac_artifact="$(cd -- "$ac_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$package"|"$package"/*|"$ac_artifact"|"$ac_artifact"/*)
	die 'output parent must be outside repository and selected inputs'
	;;
esac

manifest="$repo_root/kernel/manifest.json"
package_validator="$script_dir/validate-package-delta.py"
boot_validator="$script_dir/validate-boot.py"
normalizer="$script_dir/normalize-build-json.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in "$manifest" "$package_validator" "$boot_validator" "$normalizer" \
	"$serializer" "$analyzer"; do
	[[ -s "$input" && ! -L "$input" ]] || die "repository input missing: $input"
done

readonly AC_NAME=candidate-AC-usb-gadget-ethernet-final-3491c119
readonly AC_MANIFEST_SHA256=d95fd92cd173f0c93c2d4197d81ffba6aef1cbe40bfe2777a68acfe3acb24370
readonly AC_BOOT_SHA256=3491c119d19b7b0af2ac2342659648227182ead0e32bb4c39a66fa22cadfb39d
readonly AC_INITRAMFS_SHA256=166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3
readonly AC_DTB_SHA256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
readonly AC_KEYMAP_SHA256=02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c
[[ "$(basename "$ac_artifact")" == "$AC_NAME" ]] || die 'exact Candidate AC artifact basename changed'
for member in SHA256SUMS gemini-usb-gadget-ethernet.boot.img \
	gemini-usb-gadget-ethernet-initramfs.img \
	mt6797-gemini-pda-usb-gadget-ethernet.dtb gemini-us.bkeymap \
	console-unicode-mode console-keymap-verify input-event-capture; do
	[[ -f "$ac_artifact/$member" && ! -L "$ac_artifact/$member" ]] || \
		die "Candidate AC member is missing or unsafe: $member"
done
[[ "$(sha256sum "$ac_artifact/SHA256SUMS" | awk '{print $1}')" == "$AC_MANIFEST_SHA256" ]] || die 'exact Candidate AC manifest changed'
(cd "$ac_artifact" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'Candidate AC manifest failed'
[[ "$(sha256sum "$ac_artifact/gemini-usb-gadget-ethernet.boot.img" | awk '{print $1}')" == "$AC_BOOT_SHA256" ]] || die 'exact Candidate AC boot changed'
[[ "$(sha256sum "$ac_artifact/gemini-usb-gadget-ethernet-initramfs.img" | awk '{print $1}')" == "$AC_INITRAMFS_SHA256" ]] || die 'exact Candidate AC initramfs changed'
[[ "$(sha256sum "$ac_artifact/mt6797-gemini-pda-usb-gadget-ethernet.dtb" | awk '{print $1}')" == "$AC_DTB_SHA256" ]] || die 'exact Candidate AC final DTB changed'
[[ "$(sha256sum "$ac_artifact/gemini-us.bkeymap" | awk '{print $1}')" == "$AC_KEYMAP_SHA256" ]] || die 'exact Candidate AC keymap changed'

workdir="$(mktemp -d "$output_parent/.candidate-AD.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

python3 "$package_validator" --baseline "$baseline_package" --candidate "$package" \
	--manifest "$manifest" >"$stage/package-validation.txt"
install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
python3 "$normalizer" --input "$package/provenance/build.json" --output "$stage/source-build.json"
install -m 0600 "$ac_artifact/gemini-usb-gadget-ethernet-initramfs.img" \
	"$stage/gemini-usb-gadget-ethernet-initramfs.img"
install -m 0600 "$ac_artifact/mt6797-gemini-pda-usb-gadget-ethernet.dtb" \
	"$stage/mt6797-gemini-pda-smp8.dtb"
install -m 0600 "$ac_artifact/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$ac_artifact/console-unicode-mode" "$stage/console-unicode-mode"
install -m 0755 "$ac_artifact/console-keymap-verify" "$stage/console-keymap-verify"
install -m 0755 "$ac_artifact/input-event-capture" "$stage/input-event-capture"

candidate="$stage/gemini-smp8.boot.img"
replica_boot="$replica/gemini-smp8.boot.img"
bootopt=bootopt=64S3,32N2,64N2
python3 "$serializer" --kernel "$stage/Image.gz" \
	--ramdisk "$stage/gemini-usb-gadget-ethernet-initramfs.img" \
	--dtb "$stage/mt6797-gemini-pda-smp8.dtb" --output "$candidate" \
	--name gemini-obs-L --cmdline "$bootopt" --kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
	--tags-addr 0x44000000 --lk-android8 >"$stage/serializer.raw"
grep -v '^output=' "$stage/serializer.raw" >"$stage/serializer.txt"
rm "$stage/serializer.raw"
python3 "$serializer" --kernel "$stage/Image.gz" \
	--ramdisk "$stage/gemini-usb-gadget-ethernet-initramfs.img" \
	--dtb "$stage/mt6797-gemini-pda-smp8.dtb" --output "$replica_boot" \
	--name gemini-obs-L --cmdline "$bootopt" --kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
	--tags-addr 0x44000000 --lk-android8 >/dev/null
cmp -s "$candidate" "$replica_boot" || die 'two Candidate AD constructions differ'

python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/gemini-usb-gadget-ethernet-initramfs.img" \
	--expected-dtb "$stage/mt6797-gemini-pda-smp8.dtb" \
	--expected-name gemini-obs-L --expected-cmdline "$bootopt" "$candidate" \
	>"$stage/analysis.raw"
sed -e "s|$workdir|@WORK@|g" -e "s|$repo_root|@REPOSITORY@|g" \
	"$stage/analysis.raw" >"$stage/analysis.txt"
rm "$stage/analysis.raw"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] || die 'LK analyzer did not emit 32 gates'
python3 "$boot_validator" --candidate "$candidate" --image-gz "$stage/Image.gz" \
	--dtb "$stage/mt6797-gemini-pda-smp8.dtb" \
	--initramfs "$stage/gemini-usb-gadget-ethernet-initramfs.img" \
	>"$stage/boot-validation.txt"

candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
candidate_size="$(wc -c <"$candidate" | tr -d ' ')"
image_sha256="$(sha256sum "$stage/Image.gz" | awk '{print $1}')"
system_map_sha256="$(sha256sum "$stage/System.map" | awk '{print $1}')"
source_build_sha256="$(sha256sum "$stage/source-build.json" | awk '{print $1}')"
{
	printf 'experiment=2026-07-21-smp8-boot-diagnostic\n'
	printf 'candidate_label=AD\n'
	printf 'kernel_profile=observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8\n'
	printf 'resolved_config_delta=maxcpus-1-to-maxcpus-8-only\n'
	printf 'candidate_sha256=%s\n' "$candidate_sha256"
	printf 'candidate_size=%s\n' "$candidate_size"
	printf 'candidate_image_gz_sha256=%s\n' "$image_sha256"
	printf 'candidate_system_map_sha256=%s\n' "$system_map_sha256"
	printf 'candidate_source_build_sha256=%s\n' "$source_build_sha256"
	printf 'ac_boot_sha256=%s\n' "$AC_BOOT_SHA256"
	printf 'candidate_initramfs_sha256=%s\n' "$AC_INITRAMFS_SHA256"
	printf 'candidate_dtb_sha256=%s\n' "$AC_DTB_SHA256"
	printf 'candidate_keymap_sha256=%s\n' "$AC_KEYMAP_SHA256"
	printf 'initramfs_lineage=byte-exact-candidate-ac\n'
	printf 'dtb_lineage=byte-exact-candidate-ac-final-dtb\n'
	printf 'usb_console_keyboard_reboot=byte-exact-candidate-ac\n'
	printf 'stale_initramfs_label=cpu_policy-maxcpus-1-not-runtime-oracle\n'
	printf 'runtime_oracle=installed-hash-plus-proc-cmdline-plus-cpu-masks\n'
	printf 'cpu8_cpu9_policy=offline-not-requested\n'
	printf 'storage_access=none\nwatchdog_userspace=none\nautomatic_reboot=none\n'
	printf 'hardware_write=none\nflash=none\nruntime_result=not-tested\n'
} >"$stage/provenance.txt"

expected_inventory="$(printf '%s\n' Image.gz System.map analysis.txt boot-validation.txt \
	console-keymap-verify console-unicode-mode gemini-smp8.boot.img \
	gemini-us.bkeymap gemini-usb-gadget-ethernet-initramfs.img input-event-capture \
	mt6797-gemini-pda-smp8.dtb package-validation.txt provenance.txt serializer.txt \
	source-build.json)"
actual_inventory="$(find "$stage" -mindepth 1 -maxdepth 1 -type f -printf '%f\n' | sort)"
[[ "$actual_inventory" == "$expected_inventory" ]] || die 'Candidate AD output inventory changed'
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'Candidate AD manifest failed'
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" "$stage/console-unicode-mode" "$stage/input-event-capture"

output_name="candidate-AD-smp8-final-${candidate_sha256:0:8}"
artifact="$workdir/$output_name"
mv --no-clobber --no-target-directory "$stage" "$artifact"
stage=
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv --no-clobber --no-target-directory "$artifact" "$output"
workdir=
trap - EXIT
printf 'validation=candidate-ad-smp8\nartifact=%s\ncandidate=%s/gemini-smp8.boot.img\n' "$output" "$output"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$candidate_sha256" "$candidate_size"
printf 'runtime_result=not-tested\n'
