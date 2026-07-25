#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package DIR --baseline EXACT_V_ARTIFACT --output NEW_DIR\n' "$0" >&2
}

package=
baseline=
output=
while (($#)); do
	case "$1" in
	--package|--baseline|--output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--baseline) baseline=$2 ;;
		--output) output=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || \
	die "run inside the AArch64 Linux development VM"
[[ -d "$package" && -d "$baseline" && -n "$output" ]] || \
	die "an exact W package, exact Candidate V baseline, and output are required"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
for command in awk basename chmod cmp dirname find git grep install jq mkdir \
	mktemp mv python3 rm sha256sum sort uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
baseline="$(cd -- "$baseline" && pwd -P)"
[[ -d "$(dirname -- "$output")" ]] || \
	die "output parent must already exist"
output_parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"
output_name="$(basename -- "$output")"
[[ "$output_name" != . && "$output_name" != .. ]] || die "unsafe output name"
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
case "$output" in
"$package"|"$package"/*)
	die "output must not modify the selected kernel package"
	;;
"$baseline"|"$baseline"/*)
	die "output must not modify the Candidate V baseline"
	;;
"$repo_root"|"$repo_root"/*)
	die "generated candidates must remain outside the repository"
	;;
esac

readonly PLACEHOLDER_PREFIX=REPLACE_AFTER_CALIBRATION_
readonly PACKAGE_SUMS_SHA256=6337c00318acecea64ed77fe67757744f9c2ad9d730c1c22b14b7ad43b2a91d0
readonly IMAGE_SHA256=7b48ee247baa5b22a48b9b06a7c64b9a529c6b39786fa664ed64112d97986cc6
readonly IMAGE_GZ_SHA256=e5da5fe6c1e4ae21e8005e0638abc938e37526ea872ede2c2163ee07397c8f21
readonly SYSTEM_MAP_SHA256=d66c22e2606ead28d023da72a6696173ce956db001c65a39acbbd6a8e3052101
readonly CONFIG_SHA256=e143daa84127e2c04895c2576943dfb77ee10903c35f4d8cc9fe1dc90bf1bebb
readonly PACKAGE_DTB_SHA256=f9be46ffed6cf598f7892d88d8702ff6a4ede074c5b477734ae11bcb4c093db5
readonly BUILD_JSON_SHA256=4f6bdab0b3379a92495fcf10656e3e45bde5a8bc1bab4da29455209b601530bd
readonly W_INITRAMFS_SHA256=3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6
readonly W_BOOT_SHA256=34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4
readonly W_BOOT_SIZE=6866944

readonly PACKAGE_BASENAME=linux-7.1.3-gemini-observability-fbcon-rotation-keyboard-wrrd-4cd417ad-28a94091
readonly SOURCE_SHA256=be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc
readonly PATCHSET_SHA256=4cd417adb0d79aad2f021e1f07e47bed4825cb51b3a069e5258ea4eb49ca5ef4
readonly CONFIG_INPUTS_SHA256=28a940914585f2e15484f35f7e9e0eda70c35bd5ce46344ad9061858bfb08012
readonly CONTROLLER_PATCH_SHA256=1cab9b0094885164a16bc386321c6218767e94190ce6d8e109f6686129c58f72
readonly MANIFEST_SHA256=f24139d92781bbc0ba62f2c1711c5eb230548b498c4f7be95fa8225c92179ac1
readonly SERIES_SHA256=9b465c5bcc08c8d9073c828636e9282d77c4fe22691b8f2734e89981be8c827b

readonly V_BASELINE_BASENAME=candidate-V-keyboard-watchdog-final-9ef0ee8d
readonly V_SUMS_SHA256=0ab8291fef437cc4d2cc2b415852d21e6ccfb9deff67e8bec41b4dbfc8068ef9
readonly V_DTB_SHA256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
readonly V_INITRAMFS_SHA256=9382288385b50fed67b47ae494609f4ee9d314cfac0257c738e33e86094508b6
readonly V_HELPER_SHA256=b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602
readonly BOOT2_CAPACITY=16777216

readonly ARTIFACT_VALIDATOR_SHA256=fd0f57cc70f3f263e91ce6b83a36ac3895e6799550e15daa0723d16a8139414d
readonly SERIALIZER_SHA256=569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95

calibration_values=(
	PACKAGE_SUMS_SHA256 IMAGE_SHA256 IMAGE_GZ_SHA256 SYSTEM_MAP_SHA256
	CONFIG_SHA256 PACKAGE_DTB_SHA256 BUILD_JSON_SHA256 W_INITRAMFS_SHA256
	W_BOOT_SHA256 W_BOOT_SIZE
)
for name in "${calibration_values[@]}"; do
	value=${!name}
	[[ "$value" != "$PLACEHOLDER_PREFIX"* ]] || \
		die "calibration placeholder remains: $name"
done
for name in PACKAGE_SUMS_SHA256 IMAGE_SHA256 IMAGE_GZ_SHA256 \
	SYSTEM_MAP_SHA256 CONFIG_SHA256 PACKAGE_DTB_SHA256 BUILD_JSON_SHA256 \
	W_INITRAMFS_SHA256 W_BOOT_SHA256; do
	value=${!name}
	[[ "$value" =~ ^[0-9a-f]{64}$ ]] || die "invalid calibrated SHA-256: $name"
done
[[ "$W_BOOT_SIZE" =~ ^[0-9]+$ ]] || die "invalid calibrated W_BOOT_SIZE"
((W_BOOT_SIZE > 0 && W_BOOT_SIZE <= BOOT2_CAPACITY)) || \
	die "calibrated Candidate W size exceeds boot2"
expected_output_name="candidate-W-keyboard-wrrd-final-${W_BOOT_SHA256:0:8}"
[[ "$output_name" == "$expected_output_name" ]] || \
	die "output basename must be $expected_output_name"

artifact_validator="$repo_root/scripts/validate-kernel-artifact"
manifest="$repo_root/kernel/manifest.json"
series="$repo_root/patches/series"
controller_patch="$repo_root/patches/v7.1.3/0086-i2c-mediatek-use-MT8173-data-for-MT6797.patch"
package_validator="$script_dir/validate-package-foundation.py"
controller_validator="$script_dir/validate-controller-patch.sh"
baseline_validator="$script_dir/validate-v-baseline.py"
initramfs_builder="$script_dir/build-initramfs.sh"
initramfs_validator="$script_dir/validate-initramfs.sh"
boot_validator="$script_dir/validate-boot.py"
mutation_suite="$script_dir/test-validator-mutations.sh"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
input_paths=(
	kernel/manifest.json
	patches/series
	patches/v7.1.3/0086-i2c-mediatek-use-MT8173-data-for-MT6797.patch
	configs/gemini-handoff.fragment
	configs/gemini-usbdiag.fragment
	configs/gemini-clk-ignore-unused.fragment
	configs/gemini-observability.fragment
	configs/gemini-fbcon-rotation.fragment
	configs/gemini-keyboard.fragment
	configs/gemini-keyboard-wrrd.fragment
	scripts/validate-kernel-artifact
	experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py
	experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py
	experiments/2026-07-19-keyboard-wrrd-diagnostic/scripts/build-keyboard-wrrd-candidate.sh
	experiments/2026-07-19-keyboard-wrrd-diagnostic/scripts/validate-package-foundation.py
	experiments/2026-07-19-keyboard-wrrd-diagnostic/scripts/validate-controller-patch.sh
	experiments/2026-07-19-keyboard-wrrd-diagnostic/scripts/validate-v-baseline.py
	experiments/2026-07-19-keyboard-wrrd-diagnostic/scripts/build-initramfs.sh
	experiments/2026-07-19-keyboard-wrrd-diagnostic/scripts/validate-initramfs.sh
	experiments/2026-07-19-keyboard-wrrd-diagnostic/scripts/validate-boot.py
	experiments/2026-07-19-keyboard-wrrd-diagnostic/scripts/test-validator-mutations.sh
	experiments/2026-07-19-keyboard-wrrd-diagnostic/initramfs/init
	experiments/2026-07-19-keyboard-wrrd-diagnostic/initramfs/inittab
	experiments/2026-07-19-keyboard-wrrd-diagnostic/initramfs/local-shell
	experiments/2026-07-19-keyboard-wrrd-diagnostic/initramfs/pass
	experiments/2026-07-19-keyboard-wrrd-diagnostic/initramfs/w-probe
	experiments/2026-07-19-keyboard-wrrd-diagnostic/initramfs/w-record
	experiments/2026-07-19-keyboard-wrrd-diagnostic/initramfs/w-watchdog
)

hash_repo_inputs() {
	local checksum
	local relative
	for relative in "${input_paths[@]}"; do
		[[ -f "$repo_root/$relative" && ! -L "$repo_root/$relative" ]] || \
			die "provenance input is not a regular non-symlink file: $relative"
		checksum="$(sha256sum "$repo_root/$relative")" || \
			die "cannot hash provenance input: $relative"
		checksum=${checksum%% *}
		[[ "$checksum" =~ ^[0-9a-f]{64}$ ]] || \
			die "invalid SHA-256 for provenance input: $relative"
		printf '%s  %s\n' "$checksum" "$relative"
	done
}

for input in "$artifact_validator" "$manifest" "$series" "$controller_patch" \
	"$package_validator" "$controller_validator" "$baseline_validator" \
	"$initramfs_builder" "$initramfs_validator" "$boot_validator" \
	"$mutation_suite" "$serializer" "$analyzer"; do
	[[ -s "$input" ]] || die "required repository input missing: $input"
done
[[ "$(sha256sum "$artifact_validator" | awk '{print $1}')" == \
	"$ARTIFACT_VALIDATOR_SHA256" ]] || die "kernel-artifact validator changed"
[[ "$(sha256sum "$serializer" | awk '{print $1}')" == "$SERIALIZER_SHA256" ]] || \
	die "Android-v0 serializer changed"
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == "$ANALYZER_SHA256" ]] || \
	die "LK analyzer changed"
[[ "$(sha256sum "$manifest" | awk '{print $1}')" == "$MANIFEST_SHA256" ]] || \
	die "kernel manifest changed"
[[ "$(sha256sum "$series" | awk '{print $1}')" == "$SERIES_SHA256" ]] || \
	die "patch series changed"
[[ "$(sha256sum "$controller_patch" | awk '{print $1}')" == \
	"$CONTROLLER_PATCH_SHA256" ]] || die "controller patch changed"
input_tree_at_start="$(hash_repo_inputs)"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
[[ "$repo_revision" =~ ^[0-9a-f]{40}$ || "$repo_revision" =~ ^[0-9a-f]{64}$ ]] || \
	die "repository revision is not a full object ID"

[[ "$(basename -- "$package")" == "$PACKAGE_BASENAME" ]] || \
	die "package is not the selected Candidate W build"
[[ "$(basename -- "$baseline")" == "$V_BASELINE_BASENAME" ]] || \
	die "baseline is not the exact Candidate V artifact"

v_dtb="$baseline/mt6797-gemini-pda-keyboard-watchdog.dtb"
v_initramfs="$baseline/gemini-keyboard-watchdog-initramfs.img"
helper="$baseline/input-event-capture"
package_dtb="$package/dtbs/mediatek/mt6797-gemini-pda.dtb"
for input in "$baseline/SHA256SUMS" "$v_dtb" "$v_initramfs" "$helper" \
	"$package/SHA256SUMS" "$package/Image" "$package/Image.gz" \
	"$package/System.map" "$package/kernel.config" "$package_dtb" \
	"$package/provenance/build.json"; do
	[[ -s "$input" && ! -L "$input" ]] || die "required artifact input missing: $input"
done
[[ -x "$helper" ]] || die "Candidate V helper is not executable"

for check in \
	"$baseline/SHA256SUMS:$V_SUMS_SHA256" \
	"$v_dtb:$V_DTB_SHA256" \
	"$v_initramfs:$V_INITRAMFS_SHA256" \
	"$helper:$V_HELPER_SHA256" \
	"$package/SHA256SUMS:$PACKAGE_SUMS_SHA256" \
	"$package/Image:$IMAGE_SHA256" \
	"$package/Image.gz:$IMAGE_GZ_SHA256" \
	"$package/System.map:$SYSTEM_MAP_SHA256" \
	"$package/kernel.config:$CONFIG_SHA256" \
	"$package_dtb:$PACKAGE_DTB_SHA256" \
	"$package/provenance/build.json:$BUILD_JSON_SHA256"; do
	path=${check%%:*}
	expected=${check##*:}
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || \
		die "pinned input changed: $path"
done
jq -e --arg source "$SOURCE_SHA256" --arg patches "$PATCHSET_SHA256" \
	--arg configs "$CONFIG_INPUTS_SHA256" '
		.source_sha256 == $source and
		.patchset_sha256 == $patches and
		.config_inputs_sha256 == $configs and
		.build_profile == "observability-fbcon-rotation-keyboard-wrrd" and
		.modules_built == false
	' "$package/provenance/build.json" >/dev/null || \
	die "package provenance identities changed"

staging="$(mktemp -d "$output_parent/.candidate-W.XXXXXX")"
cleanup() { [[ ! -d "$staging" ]] || rm -rf "$staging"; }
trap cleanup EXIT

normalize_log() {
	local source=$1
	local temporary="${source}.normalized"
	while IFS= read -r line || [[ -n "$line" ]]; do
		line=${line//"$staging"/@OUTPUT@}
		line=${line//"$package"/@PACKAGE@}
		line=${line//"$baseline"/@CANDIDATE_V@}
		line=${line//"$repo_root"/@REPOSITORY@}
		case "$line" in
		generated_utc=*) line='generated_utc=@PACKAGE_GENERATED_UTC@' ;;
		esac
		printf '%s\n' "$line"
	done <"$source" >"$temporary"
	mv "$temporary" "$source"
}

"$artifact_validator" "$package" >"$staging/package-validation.txt"
normalize_log "$staging/package-validation.txt"
"$package_validator" --package "$package" --manifest "$manifest" \
	>"$staging/package-foundation.txt"
normalize_log "$staging/package-foundation.txt"
"$controller_validator" --patch "$controller_patch" \
	>"$staging/controller-patch.txt"
normalize_log "$staging/controller-patch.txt"
"$baseline_validator" --baseline "$baseline" \
	>"$staging/v-baseline-validation.txt"
normalize_log "$staging/v-baseline-validation.txt"

inputs="$staging/.validated-inputs"
mkdir "$inputs"
install -m 0600 "$package/Image.gz" "$inputs/Image.gz"
install -m 0600 "$package/provenance/build.json" "$inputs/build.json"
install -m 0600 "$v_dtb" "$inputs/candidate-v.dtb"
install -m 0600 "$v_initramfs" "$inputs/candidate-v-initramfs.img"
install -m 0700 "$helper" "$inputs/input-event-capture"
for check in \
	"$inputs/Image.gz:$IMAGE_GZ_SHA256" \
	"$inputs/build.json:$BUILD_JSON_SHA256" \
	"$inputs/candidate-v.dtb:$V_DTB_SHA256" \
	"$inputs/candidate-v-initramfs.img:$V_INITRAMFS_SHA256" \
	"$inputs/input-event-capture:$V_HELPER_SHA256"; do
	path=${check%%:*}
	expected=${check##*:}
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || \
		die "validated input changed during snapshot: $path"
done

candidate_dtb="$staging/mt6797-gemini-pda-keyboard-wrrd.dtb"
candidate_initramfs="$staging/gemini-keyboard-wrrd-initramfs.img"
candidate="$staging/gemini-keyboard-wrrd.boot.img"
install -m 0600 "$inputs/candidate-v.dtb" "$candidate_dtb"
cmp -s "$candidate_dtb" "$inputs/candidate-v.dtb" || \
	die "Candidate W DTB is not byte-exact Candidate V"
"$initramfs_builder" --baseline "$inputs/candidate-v-initramfs.img" \
	--helper "$inputs/input-event-capture" --output "$candidate_initramfs" \
	>"$staging/initramfs-build.txt"
normalize_log "$staging/initramfs-build.txt"
"$initramfs_validator" --baseline "$inputs/candidate-v-initramfs.img" \
	--candidate "$candidate_initramfs" --helper "$inputs/input-event-capture" \
	>"$staging/initramfs-validation.txt"
normalize_log "$staging/initramfs-validation.txt"
[[ "$(sha256sum "$candidate_initramfs" | awk '{print $1}')" == \
	"$W_INITRAMFS_SHA256" ]] || die "Candidate W initramfs is not pinned"

bootopt=bootopt=64S3,32N2,64N2
python3 "$serializer" --kernel "$inputs/Image.gz" \
	--ramdisk "$candidate_initramfs" --dtb "$candidate_dtb" \
	--output "$candidate" --name gemini-obs-L --cmdline "$bootopt" \
	--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 \
	>"$staging/serializer.raw"
grep -v '^output=' "$staging/serializer.raw" >"$staging/serializer.txt"
rm "$staging/serializer.raw"
normalize_log "$staging/serializer.txt"
python3 "$analyzer" --validate-lk --expected-image-gz "$inputs/Image.gz" \
	--expected-ramdisk "$candidate_initramfs" --expected-dtb "$candidate_dtb" \
	--expected-name gemini-obs-L --expected-cmdline "$bootopt" "$candidate" \
	>"$staging/analysis.txt"
normalize_log "$staging/analysis.txt"
"$boot_validator" --candidate "$candidate" --image-gz "$inputs/Image.gz" \
	--dtb "$candidate_dtb" --initramfs "$candidate_initramfs" \
	>"$staging/boot-validation.txt"
normalize_log "$staging/boot-validation.txt"

candidate_size="$(wc -c <"$candidate")"
candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
[[ "$candidate_size" == "$W_BOOT_SIZE" && "$candidate_sha256" == \
	"$W_BOOT_SHA256" ]] || die "Candidate W boot container is not pinned"
[[ "$candidate_size" -le "$BOOT2_CAPACITY" ]] || die "Candidate W exceeds boot2"
[[ "$(sha256sum "$candidate_dtb" | awk '{print $1}')" == "$V_DTB_SHA256" ]] || \
	die "Candidate W DTB changed after serialization"

jq -S 'del(.generated_utc)' "$inputs/build.json" \
	>"$staging/source-build.json"
input_tree_at_end="$(hash_repo_inputs)"
[[ "$input_tree_at_end" == "$input_tree_at_start" ]] || \
	die "repository build inputs changed during Candidate W assembly"
[[ "$(git -C "$repo_root" rev-parse HEAD)" == "$repo_revision" ]] || \
	die "repository revision changed during Candidate W assembly"
printf '%s\n' "$input_tree_at_start" >"$staging/input-tree.sha256"

{
	printf 'experiment=2026-07-19-keyboard-wrrd-diagnostic\n'
	printf 'candidate_label=W\nmarker=GEMINI_KEYBOARD_WRRD_20260719_W\n'
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'package=%s\npackage_sums_sha256=%s\n' \
		"$PACKAGE_BASENAME" "$PACKAGE_SUMS_SHA256"
	printf 'source_sha256=%s\npatchset_sha256=%s\nconfig_inputs_sha256=%s\n' \
		"$SOURCE_SHA256" "$PATCHSET_SHA256" "$CONFIG_INPUTS_SHA256"
	printf 'controller_patch_sha256=%s\ncontroller_delta=one-line-mt6797-to-mt8173-data\n' \
		"$CONTROLLER_PATCH_SHA256"
	printf 'image_sha256=%s\nimage_gz_sha256=%s\nsystem_map_sha256=%s\n' \
		"$IMAGE_SHA256" "$IMAGE_GZ_SHA256" "$SYSTEM_MAP_SHA256"
	printf 'config_sha256=%s\npackage_dtb_sha256=%s\nbuild_json_sha256=%s\n' \
		"$CONFIG_SHA256" "$PACKAGE_DTB_SHA256" "$BUILD_JSON_SHA256"
	printf 'candidate_v_manifest_sha256=%s\ncandidate_v_dtb_sha256=%s\n' \
		"$V_SUMS_SHA256" "$V_DTB_SHA256"
	printf 'candidate_v_initramfs_sha256=%s\ninput_helper_sha256=%s\n' \
		"$V_INITRAMFS_SHA256" "$V_HELPER_SHA256"
	printf 'candidate_dtb_sha256=%s\ndtb_lineage=byte-exact-candidate-v\n' \
		"$V_DTB_SHA256"
	printf 'candidate_initramfs_sha256=%s\ncandidate_sha256=%s\n' \
		"$W_INITRAMFS_SHA256" "$W_BOOT_SHA256"
	printf 'candidate_size=%s\nboot2_capacity=%s\n' "$W_BOOT_SIZE" "$BOOT2_CAPACITY"
	printf 'header_name=gemini-obs-L\nheader_cmdline=%s\n' "$bootopt"
	printf 'kernel_addr=0x40200000\nramdisk_addr=0x45000000\n'
	printf 'second_addr=0x40f00000\ntags_addr=0x44000000\n'
	printf 'simplefb=exact-v-retained\nwatchdog_irq=exact-v-absent\n'
	printf 'ramoops=exact-v-retained\ni2c5_aw9523_matrix=exact-v-retained\n'
	printf 'observation_deltas=tty2-kernel-console,TER16x32,tty1-clean-pass-token\n'
	printf 'storage_access=none\nruntime_networking=none\nhardware_write=none\nflash=none\n'
	printf 'runtime_result=not-tested\n'
} >"$staging/provenance.txt"

install -m 0755 "$inputs/input-event-capture" "$staging/input-event-capture"
rm -rf "$inputs"
expected_inventory="$(printf '%s\n' \
	analysis.txt \
	boot-validation.txt \
	controller-patch.txt \
	gemini-keyboard-wrrd-initramfs.img \
	gemini-keyboard-wrrd.boot.img \
	initramfs-build.txt \
	initramfs-validation.txt \
	input-event-capture \
	input-tree.sha256 \
	mt6797-gemini-pda-keyboard-wrrd.dtb \
	package-foundation.txt \
	package-validation.txt \
	provenance.txt \
	serializer.txt \
	source-build.json \
	v-baseline-validation.txt)"
actual_inventory="$(find "$staging" -mindepth 1 -maxdepth 1 -type f \
	-printf '%f\n' | sort)"
unexpected_entry="$(find "$staging" -mindepth 1 ! -type f -print -quit)"
[[ -z "$unexpected_entry" ]] || \
	die "Candidate W output has a non-regular or nested entry: $unexpected_entry"
[[ "$actual_inventory" == "$expected_inventory" ]] || \
	die "Candidate W output inventory is not exact before manifest creation"
(
	cd "$staging"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$staging/SHA256SUMS"
(cd "$staging" && sha256sum --check SHA256SUMS >/dev/null) || \
	die "Candidate W output manifest failed"

chmod 0600 "$staging"/*
chmod 0755 "$staging/input-event-capture"
mv --no-clobber --no-target-directory -- "$staging" "$output"
[[ ! -e "$staging" && ! -L "$staging" && -d "$output" && ! -L "$output" ]] || \
	die "Candidate W destination appeared during the atomic handoff"
staging=
trap - EXIT

printf 'validation=candidate-w-keyboard-wrrd\n'
printf 'candidate_label=W\npackage=%s\n' "$PACKAGE_BASENAME"
printf 'baseline=%s\ndtb_sha256=%s\n' "$V_BASELINE_BASENAME" "$V_DTB_SHA256"
printf 'candidate=%s/gemini-keyboard-wrrd.boot.img\n' "$output"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$W_BOOT_SHA256" "$W_BOOT_SIZE"
printf 'causal_delta=one-line-mt6797-to-mt8173-controller-data\n'
printf 'build_hardware_write=none\nflash=none\nruntime_result=not-tested\n'
