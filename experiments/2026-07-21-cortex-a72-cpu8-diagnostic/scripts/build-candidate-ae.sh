#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --baseline-artifact AD_ARTIFACT --initramfs AE_INITRAMFS --output-parent DIR\n' "$0" >&2
}

baseline_artifact=
initramfs=
output_parent=
while (($#)); do
	case "$1" in
	--baseline-artifact|--initramfs|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--baseline-artifact) baseline_artifact=$2 ;;
		--initramfs) initramfs=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die 'run in the Linux AArch64 recovery VM'
case "$(uname -m)" in aarch64|arm64) ;; *) die 'expected Linux AArch64' ;; esac
for directory in "$baseline_artifact" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] || die "unsafe or missing directory: $directory"
done
[[ -f "$initramfs" && ! -L "$initramfs" ]] || die 'safe Candidate AE initramfs is required'
for command in awk basename chmod cmp find grep install mkdir mktemp mv python3 \
	rm sed sha256sum sort tr uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
baseline_artifact="$(cd -- "$baseline_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
initramfs_parent="$(cd -- "$(dirname -- "$initramfs")" && pwd -P)"
initramfs="$initramfs_parent/$(basename -- "$initramfs")"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$baseline_artifact"|"$baseline_artifact"/*)
	die 'output parent must be outside repository and baseline artifact'
	;;
esac

readonly AD_NAME=candidate-AD-smp8-final-a1b61d8c
readonly AD_MANIFEST_SHA256=c3aeccf2e6e18a0c4769b909ccf45a77f75cc3677fe61fbd786d0925154fc51f
readonly AD_BOOT_SHA256=a1b61d8c34b5a447f1f672663f4e74fed6eb465b90154392a3c42f4db030826b
readonly AD_INITRAMFS_SHA256=166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3
readonly AD_IMAGE_GZ_SHA256=1ab084bd427f9fade4adb43a83cca879c3289929485ad1469c6dffa539d3548b
readonly AD_DTB_SHA256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
[[ "$(basename -- "$baseline_artifact")" == "$AD_NAME" ]] || die 'exact Candidate AD artifact basename changed'
for member in SHA256SUMS gemini-smp8.boot.img gemini-usb-gadget-ethernet-initramfs.img \
	Image.gz System.map mt6797-gemini-pda-smp8.dtb gemini-us.bkeymap \
	console-unicode-mode console-keymap-verify input-event-capture source-build.json; do
	[[ -f "$baseline_artifact/$member" && ! -L "$baseline_artifact/$member" ]] || \
		die "Candidate AD member missing or unsafe: $member"
done
[[ "$(sha256sum "$baseline_artifact/SHA256SUMS" | awk '{print $1}')" == "$AD_MANIFEST_SHA256" ]] || die 'exact Candidate AD manifest changed'
(cd "$baseline_artifact" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'Candidate AD manifest failed'
[[ "$(sha256sum "$baseline_artifact/gemini-smp8.boot.img" | awk '{print $1}')" == "$AD_BOOT_SHA256" ]] || die 'exact Candidate AD boot changed'
[[ "$(sha256sum "$baseline_artifact/gemini-usb-gadget-ethernet-initramfs.img" | awk '{print $1}')" == "$AD_INITRAMFS_SHA256" ]] || die 'exact Candidate AD initramfs changed'
[[ "$(sha256sum "$baseline_artifact/Image.gz" | awk '{print $1}')" == "$AD_IMAGE_GZ_SHA256" ]] || die 'exact Candidate AD Image.gz changed'
[[ "$(sha256sum "$baseline_artifact/mt6797-gemini-pda-smp8.dtb" | awk '{print $1}')" == "$AD_DTB_SHA256" ]] || die 'exact Candidate AD DTB changed'
[[ "$(sha256sum "$initramfs" | awk '{print $1}')" != "$AD_INITRAMFS_SHA256" ]] || die 'Candidate AE initramfs equals Candidate AD'

serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
initramfs_validator="$script_dir/validate-initramfs.py"
boot_validator="$script_dir/validate-boot.py"
for input in "$serializer" "$analyzer" "$initramfs_validator" "$boot_validator"; do
	[[ -s "$input" && ! -L "$input" ]] || die "repository input missing or unsafe: $input"
done

workdir="$(mktemp -d "$output_parent/.candidate-AE.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

install -m 0600 "$baseline_artifact/Image.gz" "$stage/Image.gz"
install -m 0600 "$baseline_artifact/System.map" "$stage/System.map"
install -m 0600 "$baseline_artifact/source-build.json" "$stage/source-build.json"
install -m 0600 "$baseline_artifact/mt6797-gemini-pda-smp8.dtb" "$stage/mt6797-gemini-pda-smp8.dtb"
install -m 0600 "$baseline_artifact/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$baseline_artifact/console-unicode-mode" "$stage/console-unicode-mode"
install -m 0755 "$baseline_artifact/console-keymap-verify" "$stage/console-keymap-verify"
install -m 0755 "$baseline_artifact/input-event-capture" "$stage/input-event-capture"
install -m 0600 "$initramfs" "$stage/gemini-cpu8-initramfs.img"

python3 "$initramfs_validator" \
	--baseline "$baseline_artifact/gemini-usb-gadget-ethernet-initramfs.img" \
	--candidate "$stage/gemini-cpu8-initramfs.img" \
	--source-dir "$experiment_dir/initramfs" >"$stage/initramfs-validation.raw"
sed -e "s|$repo_root|@REPOSITORY@|g" -e "s|$workdir|@WORK@|g" \
	-e "s|$baseline_artifact|@CANDIDATE_AD@|g" \
	"$stage/initramfs-validation.raw" >"$stage/initramfs-validation.txt"
rm "$stage/initramfs-validation.raw"

candidate="$stage/gemini-cpu8.boot.img"
replica_boot="$replica/gemini-cpu8.boot.img"
bootopt=bootopt=64S3,32N2,64N2
for output in "$candidate" "$replica_boot"; do
	python3 "$serializer" --kernel "$stage/Image.gz" \
		--ramdisk "$stage/gemini-cpu8-initramfs.img" \
		--dtb "$stage/mt6797-gemini-pda-smp8.dtb" --output "$output" \
		--name gemini-obs-L --cmdline "$bootopt" --kernel-addr 0x40200000 \
		--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
		--tags-addr 0x44000000 --lk-android8 \
		>${output}.serializer
done
cmp -s "$candidate" "$replica_boot" || die 'two Candidate AE container constructions differ'
grep -v '^output=' "${candidate}.serializer" >"$stage/serializer.txt"
rm "${candidate}.serializer" "${replica_boot}.serializer"

python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/gemini-cpu8-initramfs.img" \
	--expected-dtb "$stage/mt6797-gemini-pda-smp8.dtb" \
	--expected-name gemini-obs-L --expected-cmdline "$bootopt" "$candidate" \
	>"$stage/analysis.raw"
sed -e "s|$workdir|@WORK@|g" -e "s|$repo_root|@REPOSITORY@|g" \
	"$stage/analysis.raw" >"$stage/analysis.txt"
rm "$stage/analysis.raw"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] || die 'LK analyzer did not emit 32 gates'
python3 "$boot_validator" --candidate "$candidate" --image-gz "$stage/Image.gz" \
	--dtb "$stage/mt6797-gemini-pda-smp8.dtb" \
	--initramfs "$stage/gemini-cpu8-initramfs.img" >"$stage/boot-validation.txt"

candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
candidate_size="$(wc -c <"$candidate" | tr -d ' ')"
initramfs_sha256="$(sha256sum "$stage/gemini-cpu8-initramfs.img" | awk '{print $1}')"
{
	printf 'experiment=2026-07-21-cortex-a72-cpu8-diagnostic\n'
	printf 'candidate_label=AE\n'
	printf 'candidate_sha256=%s\n' "$candidate_sha256"
	printf 'candidate_size=%s\n' "$candidate_size"
	printf 'candidate_initramfs_sha256=%s\n' "$initramfs_sha256"
	printf 'ad_boot_sha256=%s\n' "$AD_BOOT_SHA256"
	printf 'ad_image_gz_sha256=%s\n' "$AD_IMAGE_GZ_SHA256"
	printf 'ad_dtb_sha256=%s\n' "$AD_DTB_SHA256"
	printf 'kernel_dtb_config_cmdline=byte-exact-candidate-ad\n'
	printf 'container_delta=initramfs-only\n'
	printf 'cpu_policy=maxcpus-8-then-one-cpu8-hotplug-request\n'
	printf 'cpu9_action=validate-offline-never-write\n'
	printf 'watchdog_action=31-second-auto-reset-on-every-runtime-outcome\n'
	printf 'storage_access=none\nflash=none\nhardware_write=none\n'
	printf 'runtime_result=not-tested\n'
} >"$stage/provenance.txt"

expected_inventory="$(printf '%s\n' Image.gz System.map analysis.txt boot-validation.txt \
	console-keymap-verify console-unicode-mode gemini-cpu8.boot.img \
	gemini-cpu8-initramfs.img gemini-us.bkeymap initramfs-validation.txt \
	input-event-capture mt6797-gemini-pda-smp8.dtb provenance.txt serializer.txt \
	source-build.json)"
actual_inventory="$(find "$stage" -mindepth 1 -maxdepth 1 -type f -printf '%f\n' | sort)"
[[ "$actual_inventory" == "$expected_inventory" ]] || die 'Candidate AE output inventory changed'
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'Candidate AE manifest failed'
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" "$stage/console-unicode-mode" "$stage/input-event-capture"

output_name="candidate-AE-cpu8-hotplug-${candidate_sha256:0:8}"
artifact="$workdir/$output_name"
mv --no-clobber --no-target-directory "$stage" "$artifact"
stage=
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv --no-clobber --no-target-directory "$artifact" "$output"
workdir=
trap - EXIT
printf 'validation=candidate-ae-cpu8-hotplug\nartifact=%s\ncandidate=%s/gemini-cpu8.boot.img\n' "$output" "$output"
printf 'candidate_sha256=%s\ncandidate_size=%s\ninitramfs_sha256=%s\n' "$candidate_sha256" "$candidate_size" "$initramfs_sha256"
printf 'runtime_result=not-tested\n'
