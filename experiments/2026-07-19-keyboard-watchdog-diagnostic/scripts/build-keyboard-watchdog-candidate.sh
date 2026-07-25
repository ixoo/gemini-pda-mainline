#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package DIR --baseline EXACT_P_ARTIFACT --output NEW_DIR\n' "$0" >&2
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
	die "an explicit corrected package, exact Candidate P artifact, and output are required"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
for command in awk basename chmod cmp dirname file find git grep gzip install jq \
	mkdir mktemp mv python3 readelf rm sha256sum sort strings uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
baseline="$(cd -- "$baseline" && pwd -P)"
mkdir -p "$(dirname -- "$output")"
output_parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"
output_name="$(basename -- "$output")"
[[ "$output_name" != . && "$output_name" != .. ]] || die "unsafe output name"
output="$output_parent/$output_name"

readonly PACKAGE_BASENAME=linux-7.1.3-gemini-observability-fbcon-rotation-keyboard-polling-5f9f1dcf-b727350a
readonly PACKAGE_SUMS_SHA256=22193d6149579be5c9e34d20db88853e55e46f1490c5f85314504bbe0e6ce257
readonly IMAGE_SHA256=202aef6bcec0458cfad077fb08bcdbb4fe3ef3a836538a21faf2f9f6b4d9eda2
readonly IMAGE_GZ_SHA256=69095483a984eb05a94e5ae212aeeb87cc3ffbded2d753f09f89661972ed89a3
readonly SYSTEM_MAP_SHA256=f63ac8143fe840119407030513838d8be6b1bb478f55d191498073cf57097d25
readonly CONFIG_SHA256=63c1012cc87d517dbd072fae59b0e20064649a4572501a42e63d8311ae10aeaa
readonly PACKAGE_DTB_SHA256=f9be46ffed6cf598f7892d88d8702ff6a4ede074c5b477734ae11bcb4c093db5
readonly BUILD_JSON_SHA256=3b35cfc1d3bb3d5556aefde404b433ce66aad292c65707a48af1c1e8cde4660a
readonly PATCHSET_SHA256=5f9f1dcf746de55a6a258803f4a9c214fc287c0a9d39e738e9f15b8a503544c5
readonly POLLING_PATCH_SHA256=4a183e91b07fb5d62e005d94bf1b416c798555945b93047b5619ceca4a0d09de

readonly P_BASENAME=candidate-P-fbcon-rotation-170a640
readonly P_SUMS_SHA256=e063bf5ddeb576deaec8aea3fa050f23a890027c7cf58b0133e3672f1ad07835
readonly P_BOOT_SHA256=d192dac9e4516eac9319da2a885abaf3203da6c357c574e7f1f6deef2208d341
readonly P_DTB_SHA256=c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379
readonly P_INITRAMFS_SHA256=3f19afd81632fbe654c024b9f865180b42caf61163bb26ea26211884271a11d8

readonly HELPER_SHA256=b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602
readonly V_DTB_SHA256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
readonly V_INITRAMFS_SHA256=9382288385b50fed67b47ae494609f4ee9d314cfac0257c738e33e86094508b6
readonly V_BOOT_SHA256=9ef0ee8dc1eb49752f9cf8f60b247b9b85e4fd2a9f090473f1d91848114087b0
readonly V_BOOT_SIZE=6864896
readonly BOOT2_CAPACITY=16777216

readonly ARTIFACT_VALIDATOR_SHA256=fd0f57cc70f3f263e91ce6b83a36ac3895e6799550e15daa0723d16a8139414d
readonly SERIALIZER_SHA256=569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95

artifact_validator="$repo_root/scripts/validate-kernel-artifact"
manifest="$repo_root/kernel/manifest.json"
series="$repo_root/patches/series"
polling_patch="$repo_root/patches/v7.1.3/0084-Input-matrix-keypad-add-optional-polling-mode.patch"
package_validator="$script_dir/validate-package-foundation.py"
patch_validator="$script_dir/validate-corrected-polling-patch.sh"
helper_builder="$script_dir/build-input-event-capture.sh"
dtb_builder="$script_dir/build-keyboard-watchdog-dtb.sh"
dtb_validator="$script_dir/validate-dtb-delta.py"
initramfs_builder="$script_dir/build-initramfs.sh"
initramfs_validator="$script_dir/validate-initramfs.sh"
boot_validator="$script_dir/validate-boot.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in "$artifact_validator" "$manifest" "$series" "$polling_patch" \
	"$package_validator" "$patch_validator" "$helper_builder" "$dtb_builder" \
	"$dtb_validator" "$initramfs_builder" "$initramfs_validator" \
	"$boot_validator" "$serializer" "$analyzer"; do
	[[ -s "$input" ]] || die "required repository input missing: $input"
done
[[ "$(sha256sum "$artifact_validator" | awk '{print $1}')" == "$ARTIFACT_VALIDATOR_SHA256" ]] || \
	die "kernel-artifact validator changed"
[[ "$(sha256sum "$serializer" | awk '{print $1}')" == "$SERIALIZER_SHA256" ]] || \
	die "Android-v0 serializer changed"
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == "$ANALYZER_SHA256" ]] || \
	die "LK analyzer changed"
[[ "$(sha256sum "$polling_patch" | awk '{print $1}')" == "$POLLING_PATCH_SHA256" ]] || \
	die "corrected polling patch changed"

[[ "$(basename -- "$package")" == "$PACKAGE_BASENAME" ]] || \
	die "package is not the selected corrected build"
[[ "$(basename -- "$baseline")" == "$P_BASENAME" ]] || \
	die "baseline is not the exact Candidate P artifact"
p_boot="$baseline/gemini-fbcon-rotation.boot.img"
p_dtb="$baseline/mt6797-gemini-pda-fbcon-rotation.dtb"
p_initramfs="$baseline/gemini-fbcon-rotation-initramfs.img"
for input in "$baseline/SHA256SUMS" "$p_boot" "$p_dtb" "$p_initramfs" \
	"$package/SHA256SUMS" "$package/Image" "$package/Image.gz" \
	"$package/System.map" "$package/kernel.config" \
	"$package/dtbs/mediatek/mt6797-gemini-pda.dtb" \
	"$package/provenance/build.json"; do
	[[ -s "$input" ]] || die "required artifact input missing: $input"
done
[[ "$(sha256sum "$baseline/SHA256SUMS" | awk '{print $1}')" == "$P_SUMS_SHA256" ]] || \
	die "Candidate P manifest changed"
(cd "$baseline" && sha256sum --check SHA256SUMS >/dev/null) || \
	die "Candidate P artifact manifest failed"
for check in \
	"$p_boot:$P_BOOT_SHA256" \
	"$p_dtb:$P_DTB_SHA256" \
	"$p_initramfs:$P_INITRAMFS_SHA256" \
	"$package/SHA256SUMS:$PACKAGE_SUMS_SHA256" \
	"$package/Image:$IMAGE_SHA256" \
	"$package/Image.gz:$IMAGE_GZ_SHA256" \
	"$package/System.map:$SYSTEM_MAP_SHA256" \
	"$package/kernel.config:$CONFIG_SHA256" \
	"$package/dtbs/mediatek/mt6797-gemini-pda.dtb:$PACKAGE_DTB_SHA256" \
	"$package/provenance/build.json:$BUILD_JSON_SHA256"; do
	path=${check%%:*}
	expected=${check##*:}
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || \
		die "pinned input changed: $path"
done

staging="$(mktemp -d "$output_parent/.candidate-V.XXXXXX")"
cleanup() { [[ ! -d "$staging" ]] || rm -rf "$staging"; }
trap cleanup EXIT

normalize_log() {
	local source=$1
	local temporary="${source}.normalized"
	while IFS= read -r line || [[ -n "$line" ]]; do
		line=${line//"$staging"/@OUTPUT@}
		line=${line//"$package"/@PACKAGE@}
		line=${line//"$baseline"/@CANDIDATE_P@}
		line=${line//"$repo_root"/@REPOSITORY@}
		printf '%s\n' "$line"
	done <"$source" >"$temporary"
	mv "$temporary" "$source"
}

"$artifact_validator" "$package" >"$staging/package-validation.txt"
normalize_log "$staging/package-validation.txt"
"$package_validator" --package "$package" --manifest "$manifest" \
	>"$staging/package-foundation.txt"
normalize_log "$staging/package-foundation.txt"
"$patch_validator" --patch "$polling_patch" >"$staging/polling-patch.txt"

inputs="$staging/.validated-inputs"
mkdir "$inputs"
install -m 0600 "$package/Image.gz" "$inputs/Image.gz"
install -m 0600 "$package/dtbs/mediatek/mt6797-gemini-pda.dtb" "$inputs/package-oracle.dtb"
install -m 0600 "$p_dtb" "$inputs/candidate-p.dtb"
install -m 0600 "$p_initramfs" "$inputs/candidate-p-initramfs.img"
for check in \
	"$inputs/Image.gz:$IMAGE_GZ_SHA256" \
	"$inputs/package-oracle.dtb:$PACKAGE_DTB_SHA256" \
	"$inputs/candidate-p.dtb:$P_DTB_SHA256" \
	"$inputs/candidate-p-initramfs.img:$P_INITRAMFS_SHA256"; do
	path=${check%%:*}
	expected=${check##*:}
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || \
		die "validated input changed during snapshot: $path"
done

helper="$staging/input-event-capture"
candidate_dtb="$staging/mt6797-gemini-pda-keyboard-watchdog.dtb"
candidate_initramfs="$staging/gemini-keyboard-watchdog-initramfs.img"
candidate="$staging/gemini-keyboard-watchdog.boot.img"
"$helper_builder" "$helper" >"$staging/helper-build.txt"
[[ "$(sha256sum "$helper" | awk '{print $1}')" == "$HELPER_SHA256" ]] || \
	die "static input helper is not pinned"
"$dtb_builder" "$inputs/candidate-p.dtb" "$inputs/package-oracle.dtb" \
	"$candidate_dtb" >"$staging/dtb-build.txt"
"$dtb_validator" --baseline-p "$inputs/candidate-p.dtb" \
	--package-oracle "$inputs/package-oracle.dtb" --candidate "$candidate_dtb" \
	>"$staging/dtb-validation.txt"
[[ "$(sha256sum "$candidate_dtb" | awk '{print $1}')" == "$V_DTB_SHA256" ]] || \
	die "Candidate V DTB is not pinned"
"$initramfs_builder" --baseline "$inputs/candidate-p-initramfs.img" \
	--helper "$helper" --output "$candidate_initramfs" \
	>"$staging/initramfs-build.txt"
"$initramfs_validator" --baseline "$inputs/candidate-p-initramfs.img" \
	--candidate "$candidate_initramfs" --helper "$helper" \
	>"$staging/initramfs-validation.txt"
[[ "$(sha256sum "$candidate_initramfs" | awk '{print $1}')" == "$V_INITRAMFS_SHA256" ]] || \
	die "Candidate V initramfs is not pinned"

bootopt=bootopt=64S3,32N2,64N2
python3 "$serializer" --kernel "$inputs/Image.gz" --ramdisk "$candidate_initramfs" \
	--dtb "$candidate_dtb" --output "$candidate" --name gemini-obs-L \
	--cmdline "$bootopt" --kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
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
python3 "$boot_validator" --candidate "$candidate" --image-gz "$inputs/Image.gz" \
	--dtb "$candidate_dtb" --initramfs "$candidate_initramfs" \
	>"$staging/boot-validation.txt"
candidate_size="$(wc -c <"$candidate")"
candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
[[ "$candidate_size" == "$V_BOOT_SIZE" && "$candidate_sha256" == "$V_BOOT_SHA256" ]] || \
	die "Candidate V boot container is not pinned"
[[ "$candidate_size" -le "$BOOT2_CAPACITY" ]] || die "Candidate V exceeds boot2 capacity"

jq -S 'del(.generated_utc)' "$package/provenance/build.json" \
	>"$staging/source-build.json"
input_paths=(
	kernel/manifest.json
	patches/series
	patches/v7.1.3/0084-Input-matrix-keypad-add-optional-polling-mode.patch
	scripts/validate-kernel-artifact
	experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py
	experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py
	experiments/2026-07-19-keyboard-watchdog-diagnostic/scripts/build-keyboard-watchdog-candidate.sh
	experiments/2026-07-19-keyboard-watchdog-diagnostic/scripts/validate-package-foundation.py
	experiments/2026-07-19-keyboard-watchdog-diagnostic/scripts/validate-corrected-polling-patch.sh
	experiments/2026-07-19-keyboard-watchdog-diagnostic/scripts/build-input-event-capture.sh
	experiments/2026-07-19-keyboard-watchdog-diagnostic/scripts/build-keyboard-watchdog-dtb.sh
	experiments/2026-07-19-keyboard-watchdog-diagnostic/scripts/validate-dtb-delta.py
	experiments/2026-07-19-keyboard-watchdog-diagnostic/scripts/build-initramfs.sh
	experiments/2026-07-19-keyboard-watchdog-diagnostic/scripts/validate-initramfs.sh
	experiments/2026-07-19-keyboard-watchdog-diagnostic/scripts/validate-boot.py
	experiments/2026-07-19-keyboard-watchdog-diagnostic/src/input-event-capture.c
	experiments/2026-07-19-keyboard-watchdog-diagnostic/initramfs/init
	experiments/2026-07-19-keyboard-watchdog-diagnostic/initramfs/inittab
	experiments/2026-07-19-keyboard-watchdog-diagnostic/initramfs/local-shell
	experiments/2026-07-19-keyboard-watchdog-diagnostic/initramfs/v-pass
	experiments/2026-07-19-keyboard-watchdog-diagnostic/initramfs/v-probe
	experiments/2026-07-19-keyboard-watchdog-diagnostic/initramfs/v-record
	experiments/2026-07-19-keyboard-watchdog-diagnostic/initramfs/v-watchdog
)
for relative in "${input_paths[@]}"; do
	[[ -f "$repo_root/$relative" ]] || die "provenance input missing: $relative"
	printf '%s  %s\n' "$(sha256sum "$repo_root/$relative" | awk '{print $1}')" "$relative"
done >"$staging/input-tree.sha256"

{
	printf 'experiment=2026-07-19-keyboard-watchdog-diagnostic\n'
	printf 'candidate_label=V\nmarker=GEMINI_KEYBOARD_WATCHDOG_20260719_V\n'
	printf 'repo_revision=%s\n' "$(git -C "$repo_root" rev-parse HEAD)"
	printf 'package=%s\npackage_sums_sha256=%s\n' "$PACKAGE_BASENAME" "$PACKAGE_SUMS_SHA256"
	printf 'image_sha256=%s\nimage_gz_sha256=%s\nsystem_map_sha256=%s\n' \
		"$IMAGE_SHA256" "$IMAGE_GZ_SHA256" "$SYSTEM_MAP_SHA256"
	printf 'config_sha256=%s\npackage_dtb_oracle_sha256=%s\n' "$CONFIG_SHA256" "$PACKAGE_DTB_SHA256"
	printf 'patchset_sha256=%s\ncorrected_polling_patch_sha256=%s\n' \
		"$PATCHSET_SHA256" "$POLLING_PATCH_SHA256"
	printf 'candidate_p_manifest_sha256=%s\ncandidate_p_boot_sha256=%s\n' \
		"$P_SUMS_SHA256" "$P_BOOT_SHA256"
	printf 'candidate_p_dtb_sha256=%s\ncandidate_p_initramfs_sha256=%s\n' \
		"$P_DTB_SHA256" "$P_INITRAMFS_SHA256"
	printf 'input_helper_sha256=%s\ncandidate_dtb_sha256=%s\n' "$HELPER_SHA256" "$V_DTB_SHA256"
	printf 'candidate_initramfs_sha256=%s\ncandidate_sha256=%s\n' \
		"$V_INITRAMFS_SHA256" "$V_BOOT_SHA256"
	printf 'candidate_size=%s\nboot2_capacity=%s\n' "$V_BOOT_SIZE" "$BOOT2_CAPACITY"
	printf 'header_name=gemini-obs-L\nheader_cmdline=%s\n' "$bootopt"
	printf 'kernel_addr=0x40200000\nramdisk_addr=0x45000000\n'
	printf 'second_addr=0x40f00000\ntags_addr=0x44000000\n'
	printf 'dt_lineage=exact-candidate-P-plus-keyboard-allowlist\n'
	printf 'simplefb=exact-P-retained\nwatchdog_irq=exact-P-absent\nramoops=exact-P-retained\n'
	printf 'watchdog_recovery=one-handoff-ping-then-no-irq-expiry-31s\n'
	printf 'event_observation=5s-discovery-plus-15s-absolute-capture-no-grab\n'
	printf 'storage_access=none\nruntime_networking=none\nhardware_write=none\nflash=none\n'
	printf 'runtime_result=not-tested\n'
} >"$staging/provenance.txt"

rm -rf "$inputs"
(
	cd "$staging"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$staging/SHA256SUMS"
(cd "$staging" && sha256sum --check SHA256SUMS >/dev/null)
chmod 0600 "$staging"/*
chmod 0755 "$helper"
mv "$staging" "$output"
staging=
trap - EXIT

printf 'validation=candidate-v-keyboard-watchdog\n'
printf 'candidate_label=V\npackage=%s\n' "$PACKAGE_BASENAME"
printf 'candidate=%s/gemini-keyboard-watchdog.boot.img\n' "$output"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$V_BOOT_SHA256" "$V_BOOT_SIZE"
printf 'automatic_recovery=mtk-wdt-no-irq-expiry\n'
printf 'build_hardware_write=none\nflash=none\nruntime_result=not-tested\n'
