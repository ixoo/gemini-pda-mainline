#!/usr/bin/env bash

# Assemble Candidate Galileo from a validated kernel package and the exact
# hardware-tested AO console/keyboard/USB initramfs and DT lineage.
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --package DIR --ao-artifact DIR --output-parent DIR\n' "$0" >&2; }
package=; ao_artifact=; output_parent=
while (($#)); do
	case "$1" in
	--package|--ao-artifact|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;; --ao-artifact) ao_artifact=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$package" && -n "$ao_artifact" && -n "$output_parent" ]] || { usage; exit 2; }
[[ "$(uname -s)" == Linux ]] || die 'run in the Linux recovery VM'
[[ "$(uname -m)" == aarch64 || "$(uname -m)" == arm64 ]] || die 'expected Linux AArch64'
for directory in "$package" "$ao_artifact" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] || die "unsafe or missing directory: $directory"
done
for command in awk bash chmod cmp cut dd find grep install mkdir mktemp mv \
	python3 rm rmdir sha256sum sort tr uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "$0")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
ao_artifact="$(cd -- "$ao_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$package"|"$package"/*|"$ao_artifact"|"$ao_artifact"/*)
	die 'output parent must be outside selected inputs' ;;
esac

module="$script_dir/candidate_galileo.py"
value() { PYTHONPATH="$script_dir" python3 -c 'import candidate_galileo as c,sys; print(getattr(c,sys.argv[1]))' "$1"; }
PROFILE="$(value PROFILE)"
AO_NAME="$(value AO_ARTIFACT_DIR)"
AO_DTB="$(value AO_DTB_MEMBER)"
AO_INITRAMFS="$(value AO_INITRAMFS_MEMBER)"
AO_DTB_SHA256="$(value AO_DTB_SHA256)"
AO_INITRAMFS_SHA256="$(value AO_INITRAMFS_SHA256)"
AO_KEYMAP_SHA256="$(value AO_KEYMAP_SHA256)"
SERIALIZER_SHA256="$(value SERIALIZER_SHA256)"
ANALYZER_SHA256="$(value ANALYZER_SHA256)"
BOOT_MEMBER="$(value BOOT_MEMBER)"
DTB_MEMBER="$(value DTB_MEMBER)"
INITRAMFS_MEMBER="$(value INITRAMFS_MEMBER)"
validator="$script_dir/validate-package-galileo.py"
dtb_builder="$repo_root/experiments/2026-07-25-da9214-legacy-identification/scripts/build-as-dtb.sh"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
normalizer="$repo_root/experiments/2026-07-24-mt6797-dvfsp-i2c6-consumer/scripts/normalize-build-json.py"
for input in "$module" "$validator" "$dtb_builder" "$serializer" "$analyzer" "$normalizer"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || die "repository input missing: $input"
done
[[ "$(sha256sum "$serializer" | awk '{print $1}')" == "$SERIALIZER_SHA256" ]] || die 'serializer source changed'
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == "$ANALYZER_SHA256" ]] || die 'LK analyzer source changed'
[[ "$(basename "$ao_artifact")" == "$AO_NAME" ]] || die 'wrong AO artifact'
for member in SHA256SUMS "$AO_DTB" "$AO_INITRAMFS" gemini-us.bkeymap \
	console-unicode-mode console-keymap-verify input-event-capture; do
	[[ -f "$ao_artifact/$member" && ! -L "$ao_artifact/$member" ]] || die "AO member missing: $member"
done
(cd "$ao_artifact" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'AO manifest failed'
[[ "$(sha256sum "$ao_artifact/SHA256SUMS" | awk '{print $1}')" == "$(value AO_MANIFEST_SHA256)" ]] || die 'AO manifest identity changed'
[[ "$(sha256sum "$ao_artifact/$AO_DTB" | awk '{print $1}')" == "$AO_DTB_SHA256" ]] || die 'AO DT identity changed'
[[ "$(sha256sum "$ao_artifact/$AO_INITRAMFS" | awk '{print $1}')" == "$AO_INITRAMFS_SHA256" ]] || die 'AO initramfs identity changed'
[[ "$(sha256sum "$ao_artifact/gemini-us.bkeymap" | awk '{print $1}')" == "$AO_KEYMAP_SHA256" ]] || die 'AO keymap identity changed'

workdir="$(mktemp -d "$output_parent/.candidate-galileo.XXXXXX")"
cleanup() { if [[ -n "$workdir" && -d "$workdir" ]]; then rm -rf -- "$workdir"; fi; }
trap cleanup EXIT
stage="$workdir/stage"; replica="$workdir/replica"; mkdir "$stage" "$replica"
python3 "$validator" --repository "$repo_root" --package "$package" >"$stage/package-validation.txt"
install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
python3 "$normalizer" --input "$package/provenance/build.json" --output "$stage/source-build.json"
install -m 0600 "$ao_artifact/$AO_INITRAMFS" "$stage/$INITRAMFS_MEMBER"
install -m 0600 "$ao_artifact/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$ao_artifact/console-unicode-mode" "$stage/console-unicode-mode"
install -m 0755 "$ao_artifact/console-keymap-verify" "$stage/console-keymap-verify"
install -m 0755 "$ao_artifact/input-event-capture" "$stage/input-event-capture"
bash "$dtb_builder" --ao-dtb "$ao_artifact/$AO_DTB" --output "$stage/$DTB_MEMBER" >"$stage/dtb-validation.txt"
bash "$dtb_builder" --ao-dtb "$ao_artifact/$AO_DTB" --output "$replica/$DTB_MEMBER" >/dev/null
cmp -s "$stage/$DTB_MEMBER" "$replica/$DTB_MEMBER" || die 'independent DT derivations differ'
boot_cmdline=bootopt=64S3,32N2,64N2
for output in "$stage/$BOOT_MEMBER" "$replica/$BOOT_MEMBER"; do
	python3 "$serializer" --kernel "$stage/Image.gz" --ramdisk "$stage/$INITRAMFS_MEMBER" \
		--dtb "$stage/$DTB_MEMBER" --output "$output" --name gemini-galileo \
		--cmdline "$boot_cmdline" --kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
		--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 >"$output.serializer"
done
cmp -s "$stage/$BOOT_MEMBER" "$replica/$BOOT_MEMBER" || die 'independent boot assemblies differ'
grep -v '^output=' "$stage/$BOOT_MEMBER.serializer" >"$stage/serializer.txt"
rm "$stage/$BOOT_MEMBER.serializer" "$replica/$BOOT_MEMBER.serializer"
python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/$INITRAMFS_MEMBER" --expected-dtb "$stage/$DTB_MEMBER" \
	--expected-name gemini-galileo --expected-cmdline "$boot_cmdline" \
	"$stage/$BOOT_MEMBER" >"$stage/analysis.txt"
raw_sha256="$(sha256sum "$stage/$BOOT_MEMBER" | awk '{print $1}')"
raw_size="$(wc -c <"$stage/$BOOT_MEMBER" | tr -d ' ')"
padded="$workdir/padded.img"
dd if=/dev/zero of="$padded" bs=16M count=1 status=none
dd if="$stage/$BOOT_MEMBER" of="$padded" bs=4M conv=notrunc,fsync status=none
padded_sha256="$(sha256sum "$padded" | awk '{print $1}')"
install -m 0600 "$padded" "$stage/boot2-padded.img"
cat >"$stage/provenance.txt" <<EOF
experiment=2026-07-26-a72-active-galileo
candidate=Galileo
kernel_profile=$PROFILE
boot_container=canonical-android-v0-lk-android8
candidate_raw_sha256=$raw_sha256
candidate_raw_size=$raw_size
candidate_padded_boot2_sha256=$padded_sha256
ao_dtb_sha256=$AO_DTB_SHA256
ao_initramfs_sha256=$AO_INITRAMFS_SHA256
ao_keymap_sha256=$AO_KEYMAP_SHA256
usb_shell=byte-exact-AO-initramfs-and-gadget-cmdline
cpu8=active-experiment
cpu9=fail-closed
dvfs_hps_idle_thermal_policy=firmware-owned
storage_access=none
hardware_write=none
runtime_result=not-tested
EOF
expected="$(printf '%s\n' Image.gz System.map analysis.txt boot2-padded.img \
	console-keymap-verify console-unicode-mode dtb-validation.txt gemini-us.bkeymap \
	input-event-capture kernel.config package-validation.txt provenance.txt serializer.txt \
	source-build.json "$BOOT_MEMBER" "$DTB_MEMBER" "$INITRAMFS_MEMBER" | sort)"
actual="$(find "$stage" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)"
[[ "$actual" == "$expected" ]] || die 'Candidate Galileo output inventory changed'
(cd "$stage" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'Candidate Galileo manifest failed'
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" "$stage/console-unicode-mode" "$stage/input-event-capture"
short_sha="$(printf '%s' "$raw_sha256" | cut -c1-8)"
artifact="$workdir/$(value ARTIFACT_PREFIX)$short_sha"
mv -n "$stage" "$artifact"
stage=
output="$output_parent/$(basename "$artifact")"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv -n "$artifact" "$output"
rm -f -- "$padded"
rm -rf -- "$replica"; rmdir "$workdir"; workdir=
trap - EXIT
printf 'validation=candidate-galileo-assembled\nartifact=%s\nraw_sha256=%s\nraw_size=%s\npadded_boot2_sha256=%s\nruntime_result=not-tested\n' "$output" "$raw_sha256" "$raw_size" "$padded_sha256"
