#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package DIR --baseline EXACT_W_ARTIFACT --output NEW_DIR\n' "$0" >&2
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
[[ -d "$package" && ! -L "$package" && -d "$baseline" && ! -L "$baseline" && \
	-n "$output" ]] || die "exact X package, exact Candidate W baseline, and output are required"
for command in awk basename chmod cmp dirname find git grep install jq mkdir \
	mktemp mv python3 rm sha256sum sort uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

# Deliberate calibration gate. These values may be replaced only after two
# clean X-profile package builds and two deterministic candidate assemblies.
readonly PLACEHOLDER_PREFIX=REPLACE_AFTER_CALIBRATION_
readonly PACKAGE_BASENAME=linux-7.1.3-gemini-observability-fbcon-rotation-keyboard-wrrd-manual-reboot-4cd417ad-c811a159
readonly PACKAGE_SUMS_SHA256=541542094a9f516556ffcab884abd3db1d58537aff6fd7e2f95abba42e2992c7
readonly IMAGE_SHA256=cbd52cdd3b9a619cfaf6f8e502458f6904226e19f6115e28c1f8bbf6084cda92
readonly IMAGE_GZ_SHA256=d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41
readonly SYSTEM_MAP_SHA256=770e97f45aa377355faa3fa0865bdd40dd2f72a1b4bc132e65e19d6ac481f8c7
readonly CONFIG_SHA256=0a0e4ef39d5d89d0d54f55be44da753c93779d88bb94b35623679d1b08b66e74
readonly PACKAGE_DTB_SHA256=f9be46ffed6cf598f7892d88d8702ff6a4ede074c5b477734ae11bcb4c093db5
readonly BUILD_JSON_SHA256=4d710898b478b2cfed2ce6d0d0d1ecab4144f5a8c57f4b765c123e05f2b945a3
readonly CONFIG_INPUTS_SHA256=c811a1595510716777871637672f4298f4808b1d4fcea5c5da1d05d37676baa2
readonly X_INITRAMFS_SHA256=b54ce3cd75e7947ed867165e31abbf6ee6cbac7d41d171435f99bba7825bc769
readonly X_BOOT_SHA256=bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296
readonly X_BOOT_SIZE=6864896
calibration_values=(
	PACKAGE_BASENAME PACKAGE_SUMS_SHA256 IMAGE_SHA256 IMAGE_GZ_SHA256
	SYSTEM_MAP_SHA256 CONFIG_SHA256 PACKAGE_DTB_SHA256 BUILD_JSON_SHA256
	CONFIG_INPUTS_SHA256 X_INITRAMFS_SHA256 X_BOOT_SHA256 X_BOOT_SIZE
)
for name in "${calibration_values[@]}"; do
	value=${!name}
	[[ "$value" != "$PLACEHOLDER_PREFIX"* ]] || \
		die "calibration placeholder remains: $name"
done
for name in PACKAGE_SUMS_SHA256 IMAGE_SHA256 IMAGE_GZ_SHA256 \
	SYSTEM_MAP_SHA256 CONFIG_SHA256 PACKAGE_DTB_SHA256 BUILD_JSON_SHA256 \
	CONFIG_INPUTS_SHA256 X_INITRAMFS_SHA256 X_BOOT_SHA256; do
	value=${!name}
	[[ "$value" =~ ^[0-9a-f]{64}$ ]] || die "invalid calibrated SHA-256: $name"
done
[[ "$PACKAGE_BASENAME" =~ ^linux-7\.1\.3-gemini-[A-Za-z0-9._-]+$ ]] || \
	die "invalid calibrated package basename"
[[ "$X_BOOT_SIZE" =~ ^[0-9]+$ ]] || die "invalid calibrated X_BOOT_SIZE"
readonly BOOT2_CAPACITY=16777216
((X_BOOT_SIZE > 0 && X_BOOT_SIZE <= BOOT2_CAPACITY)) || \
	die "calibrated Candidate X size exceeds logical boot2 capacity"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
baseline="$(cd -- "$baseline" && pwd -P)"
[[ -d "$(dirname -- "$output")" ]] || die "output parent must already exist"
output_parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"
output_name="$(basename -- "$output")"
expected_output_name="candidate-X-keyboard-manual-reboot-final-${X_BOOT_SHA256:0:8}"
[[ "$output_name" == "$expected_output_name" ]] || \
	die "output basename must be $expected_output_name"
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
case "$output" in
"$package"|"$package"/*|"$baseline"|"$baseline"/*|"$repo_root"|"$repo_root"/*)
	die "output must be outside package, baseline, and repository"
	;;
esac

readonly W_BASELINE_BASENAME=candidate-W-keyboard-wrrd-final-34c41fad
readonly W_MANIFEST_SHA256=257b17585c171e29ae3510fdab7602aa59e4da570aa906abb8b9e5b7e8da5851
readonly W_DTB_SHA256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
readonly W_INITRAMFS_SHA256=3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6
readonly W_HELPER_SHA256=b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602
readonly SOURCE_SHA256=be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc
readonly PATCHSET_SHA256=4cd417adb0d79aad2f021e1f07e47bed4825cb51b3a069e5258ea4eb49ca5ef4
readonly MANIFEST_SHA256=a3e42edc371ffa82b4eec174614d1af13ece0b2e02f6d5c6a682d0098d360f4d
readonly SERIES_SHA256=9b465c5bcc08c8d9073c828636e9282d77c4fe22691b8f2734e89981be8c827b
readonly ARTIFACT_VALIDATOR_SHA256=fd0f57cc70f3f263e91ce6b83a36ac3895e6799550e15daa0723d16a8139414d
readonly SERIALIZER_SHA256=569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95

artifact_validator="$repo_root/scripts/validate-kernel-artifact"
manifest="$repo_root/kernel/manifest.json"
series="$repo_root/patches/series"
package_validator="$script_dir/validate-package-foundation.py"
baseline_validator="$script_dir/validate-w-baseline.py"
initramfs_builder="$script_dir/build-initramfs.sh"
initramfs_validator="$script_dir/validate-initramfs.sh"
boot_validator="$script_dir/validate-boot.py"
mutation_suite="$script_dir/test-validator-mutations.sh"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in "$artifact_validator" "$manifest" "$series" "$package_validator" \
	"$baseline_validator" "$initramfs_builder" "$initramfs_validator" \
	"$boot_validator" "$mutation_suite" "$serializer" "$analyzer"; do
	[[ -s "$input" && ! -L "$input" ]] || die "required repository input missing: $input"
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

input_paths=(
	kernel/manifest.json
	patches/series
	configs/gemini-handoff.fragment
	configs/gemini-usbdiag.fragment
	configs/gemini-clk-ignore-unused.fragment
	configs/gemini-observability.fragment
	configs/gemini-fbcon-rotation.fragment
	configs/gemini-keyboard.fragment
	configs/gemini-keyboard-wrrd.fragment
	configs/gemini-keyboard-manual-reboot.fragment
	scripts/validate-kernel-artifact
	experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py
	experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py
	experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/build-keyboard-manual-reboot-candidate.sh
	experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/validate-package-foundation.py
	experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/validate-w-baseline.py
	experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/build-initramfs.sh
	experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/validate-initramfs.sh
	experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/validate-boot.py
	experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/test-validator-mutations.sh
	experiments/2026-07-19-keyboard-manual-reboot-diagnostic/initramfs/init
	experiments/2026-07-19-keyboard-manual-reboot-diagnostic/initramfs/inittab
	experiments/2026-07-19-keyboard-manual-reboot-diagnostic/initramfs/local-shell
	experiments/2026-07-19-keyboard-manual-reboot-diagnostic/initramfs/reboot
	experiments/2026-07-19-keyboard-manual-reboot-diagnostic/initramfs/x-probe
	experiments/2026-07-19-keyboard-manual-reboot-diagnostic/initramfs/x-record
)
while IFS= read -r relative || [[ -n "$relative" ]]; do
	[[ -z "$relative" || "$relative" == \#* ]] && continue
	[[ "$relative" =~ ^[A-Za-z0-9._/-]+$ && "$relative" != /* ]] || \
		die "unsafe patch-series entry in repository input snapshot"
	case "/$relative/" in
	*/../*) die "unsafe parent component in patch-series entry" ;;
	esac
	input_paths+=("patches/$relative")
done <"$series"

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

input_tree_at_start="$(hash_repo_inputs)"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
[[ "$repo_revision" =~ ^[0-9a-f]{40}$ || "$repo_revision" =~ ^[0-9a-f]{64}$ ]] || \
	die "repository revision is not a full object ID"
[[ "$(basename -- "$package")" == "$PACKAGE_BASENAME" ]] || \
	die "package is not the calibrated Candidate X package"
[[ "$(basename -- "$baseline")" == "$W_BASELINE_BASENAME" ]] || \
	die "baseline is not exact Candidate W"

w_dtb="$baseline/mt6797-gemini-pda-keyboard-wrrd.dtb"
w_initramfs="$baseline/gemini-keyboard-wrrd-initramfs.img"
helper="$baseline/input-event-capture"
package_dtb="$package/dtbs/mediatek/mt6797-gemini-pda.dtb"
for check in \
	"$baseline/SHA256SUMS:$W_MANIFEST_SHA256" \
	"$w_dtb:$W_DTB_SHA256" \
	"$w_initramfs:$W_INITRAMFS_SHA256" \
	"$helper:$W_HELPER_SHA256" \
	"$package/SHA256SUMS:$PACKAGE_SUMS_SHA256" \
	"$package/Image:$IMAGE_SHA256" \
	"$package/Image.gz:$IMAGE_GZ_SHA256" \
	"$package/System.map:$SYSTEM_MAP_SHA256" \
	"$package/kernel.config:$CONFIG_SHA256" \
	"$package_dtb:$PACKAGE_DTB_SHA256" \
	"$package/provenance/build.json:$BUILD_JSON_SHA256"; do
	path=${check%%:*}
	expected=${check##*:}
	[[ -s "$path" && ! -L "$path" ]] || die "required artifact input missing: $path"
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || \
		die "pinned input changed: $path"
done
[[ -x "$helper" ]] || die "Candidate W helper is not executable"
jq -e --arg source "$SOURCE_SHA256" --arg patches "$PATCHSET_SHA256" \
	--arg configs "$CONFIG_INPUTS_SHA256" '
		.source_sha256 == $source and
		.patchset_sha256 == $patches and
		.config_inputs_sha256 == $configs and
		.build_profile == "observability-fbcon-rotation-keyboard-wrrd-manual-reboot" and
		.modules_built == false
	' "$package/provenance/build.json" >/dev/null || \
	die "package provenance identities changed"

staging="$(mktemp -d "$output_parent/.candidate-X.XXXXXX")"
cleanup() { [[ ! -d "$staging" ]] || rm -rf "$staging"; }
trap cleanup EXIT
normalize_log() {
	local source=$1
	local temporary="${source}.normalized"
	while IFS= read -r line || [[ -n "$line" ]]; do
		line=${line//"$staging"/@OUTPUT@}
		line=${line//"$package"/@PACKAGE@}
		line=${line//"$baseline"/@CANDIDATE_W@}
		line=${line//"$repo_root"/@REPOSITORY@}
		case "$line" in generated_utc=*) line='generated_utc=@PACKAGE_GENERATED_UTC@' ;; esac
		printf '%s\n' "$line"
	done <"$source" >"$temporary"
	mv "$temporary" "$source"
}

"$artifact_validator" "$package" >"$staging/package-validation.txt"
normalize_log "$staging/package-validation.txt"
"$package_validator" --package "$package" --manifest "$manifest" \
	>"$staging/package-foundation.txt"
normalize_log "$staging/package-foundation.txt"
"$baseline_validator" --baseline "$baseline" >"$staging/w-baseline-validation.txt"
normalize_log "$staging/w-baseline-validation.txt"

# All bytes used for assembly are copied only after their selected trees pass
# the generic, profile-specific, and exact-baseline validators.  Every copy is
# then checked against its immutable pin before the live input paths are no
# longer consulted.
inputs="$staging/.validated-inputs"
mkdir "$inputs"
install -m 0600 "$package/Image" "$inputs/Image"
install -m 0600 "$package/Image.gz" "$inputs/Image.gz"
install -m 0600 "$package/System.map" "$inputs/System.map"
install -m 0600 "$package/kernel.config" "$inputs/kernel.config"
install -m 0600 "$package_dtb" "$inputs/package.dtb"
install -m 0600 "$package/provenance/build.json" "$inputs/build.json"
install -m 0600 "$w_dtb" "$inputs/candidate-w.dtb"
install -m 0600 "$w_initramfs" "$inputs/candidate-w-initramfs.img"
install -m 0700 "$helper" "$inputs/input-event-capture"
for check in \
	"$inputs/Image:$IMAGE_SHA256" \
	"$inputs/Image.gz:$IMAGE_GZ_SHA256" \
	"$inputs/System.map:$SYSTEM_MAP_SHA256" \
	"$inputs/kernel.config:$CONFIG_SHA256" \
	"$inputs/package.dtb:$PACKAGE_DTB_SHA256" \
	"$inputs/build.json:$BUILD_JSON_SHA256" \
	"$inputs/candidate-w.dtb:$W_DTB_SHA256" \
	"$inputs/candidate-w-initramfs.img:$W_INITRAMFS_SHA256" \
	"$inputs/input-event-capture:$W_HELPER_SHA256"; do
	path=${check%%:*}
	expected=${check##*:}
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || \
		die "validated input changed during immutable snapshot: $path"
done

candidate_dtb="$staging/mt6797-gemini-pda-keyboard-manual-reboot.dtb"
candidate_initramfs="$staging/gemini-keyboard-manual-reboot-initramfs.img"
candidate="$staging/gemini-keyboard-manual-reboot.boot.img"
install -m 0600 "$inputs/candidate-w.dtb" "$candidate_dtb"
cmp -s "$candidate_dtb" "$inputs/candidate-w.dtb" || \
	die "Candidate X DTB is not byte-exact W"
"$initramfs_builder" --baseline "$inputs/candidate-w-initramfs.img" \
	--helper "$inputs/input-event-capture" \
	--output "$candidate_initramfs" >"$staging/initramfs-build.txt"
normalize_log "$staging/initramfs-build.txt"
"$initramfs_validator" --baseline "$inputs/candidate-w-initramfs.img" \
	--candidate "$candidate_initramfs" --helper "$inputs/input-event-capture" \
	>"$staging/initramfs-validation.txt"
normalize_log "$staging/initramfs-validation.txt"
[[ "$(sha256sum "$candidate_initramfs" | awk '{print $1}')" == "$X_INITRAMFS_SHA256" ]] || \
	die "Candidate X initramfs is not calibrated"

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
"$boot_validator" --candidate "$candidate" --image-gz "$inputs/Image.gz" \
	--dtb "$candidate_dtb" --initramfs "$candidate_initramfs" \
	>"$staging/boot-validation.txt"
normalize_log "$staging/boot-validation.txt"
[[ "$(wc -c <"$candidate")" == "$X_BOOT_SIZE" && \
	"$(sha256sum "$candidate" | awk '{print $1}')" == "$X_BOOT_SHA256" ]] || \
	die "Candidate X boot container is not calibrated"
[[ "$(sha256sum "$candidate_dtb" | awk '{print $1}')" == "$W_DTB_SHA256" ]] || \
	die "Candidate X DTB changed during serialization"

# Re-run both deterministic construction layers into an isolated private tree.
# The second initramfs and Android-v0 container must be byte-identical before
# any output manifest can be created.
replica="$staging/.deterministic-replica"
mkdir "$replica"
replica_initramfs="$replica/gemini-keyboard-manual-reboot-initramfs.img"
replica_boot="$replica/gemini-keyboard-manual-reboot.boot.img"
"$initramfs_builder" --baseline "$inputs/candidate-w-initramfs.img" \
	--helper "$inputs/input-event-capture" --output "$replica_initramfs" >/dev/null
cmp -s "$candidate_initramfs" "$replica_initramfs" || \
	die "independent Candidate X initramfs reconstruction differs"
python3 "$serializer" --kernel "$inputs/Image.gz" --ramdisk "$replica_initramfs" \
	--dtb "$inputs/candidate-w.dtb" --output "$replica_boot" --name gemini-obs-L \
	--cmdline "$bootopt" --kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 >/dev/null
cmp -s "$candidate" "$replica_boot" || \
	die "independent Candidate X Android-v0 reconstruction differs"
"$boot_validator" --candidate "$replica_boot" --image-gz "$inputs/Image.gz" \
	--dtb "$inputs/candidate-w.dtb" --initramfs "$replica_initramfs" >/dev/null
rm -rf "$replica"

jq -S 'del(.generated_utc)' "$inputs/build.json" \
	>"$staging/source-build.json"
input_tree_at_end="$(hash_repo_inputs)"
[[ "$input_tree_at_end" == "$input_tree_at_start" ]] || \
	die "repository build inputs changed during Candidate X assembly"
[[ "$(git -C "$repo_root" rev-parse HEAD)" == "$repo_revision" ]] || \
	die "repository revision changed during Candidate X assembly"
printf '%s\n' "$input_tree_at_start" >"$staging/input-tree.sha256"
{
	printf 'experiment=2026-07-19-keyboard-manual-reboot-diagnostic\n'
	printf 'candidate_label=X\nmarker=GEMINI_KEYBOARD_MANUAL_REBOOT_20260719_X\n'
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'package=%s\npackage_sums_sha256=%s\n' \
		"$PACKAGE_BASENAME" "$PACKAGE_SUMS_SHA256"
	printf 'source_sha256=%s\npatchset_sha256=%s\n' "$SOURCE_SHA256" "$PATCHSET_SHA256"
	printf 'config_inputs_sha256=%s\nconfig_sha256=%s\nimage_gz_sha256=%s\n' \
		"$CONFIG_INPUTS_SHA256" "$CONFIG_SHA256" "$IMAGE_GZ_SHA256"
	printf 'image_sha256=%s\nsystem_map_sha256=%s\npackage_dtb_sha256=%s\n' \
		"$IMAGE_SHA256" "$SYSTEM_MAP_SHA256" "$PACKAGE_DTB_SHA256"
	printf 'build_json_sha256=%s\n' "$BUILD_JSON_SHA256"
	printf 'candidate_w_manifest_sha256=%s\ncandidate_w_dtb_sha256=%s\n' \
		"$W_MANIFEST_SHA256" "$W_DTB_SHA256"
	printf 'candidate_w_initramfs_sha256=%s\ninput_helper_sha256=%s\n' \
		"$W_INITRAMFS_SHA256" "$W_HELPER_SHA256"
	printf 'candidate_dtb_sha256=%s\ndtb_lineage=byte-exact-candidate-w\n' "$W_DTB_SHA256"
	printf 'candidate_initramfs_sha256=%s\ncandidate_sha256=%s\n' \
		"$X_INITRAMFS_SHA256" "$X_BOOT_SHA256"
	printf 'candidate_size=%s\nboot2_capacity=%s\n' "$X_BOOT_SIZE" "$BOOT2_CAPACITY"
	printf 'kernel_virtual_console=none\nserial_console=ttyS0,921600n8\n'
	printf 'font=TER16x32\nfbcon_rotation=3\n'
	printf 'watchdog_dt=exact-w-retained\nwatchdog_userspace=start-none,open-none,ping-none\n'
	printf 'manual_reboot=busybox-reboot-no-sync-force\n'
	printf 'deterministic_replica=initramfs-and-android-v0-byte-identical\n'
	printf 'storage_access=none\nruntime_networking=none\nhardware_write=none\nflash=none\n'
	printf 'runtime_result=not-tested\n'
} >"$staging/provenance.txt"
install -m 0755 "$inputs/input-event-capture" "$staging/input-event-capture"
rm -rf "$inputs"

expected_inventory="$(printf '%s\n' analysis.txt boot-validation.txt \
	gemini-keyboard-manual-reboot-initramfs.img gemini-keyboard-manual-reboot.boot.img \
	initramfs-build.txt initramfs-validation.txt input-event-capture input-tree.sha256 \
	mt6797-gemini-pda-keyboard-manual-reboot.dtb package-foundation.txt \
	package-validation.txt provenance.txt serializer.txt source-build.json \
	w-baseline-validation.txt)"
actual_inventory="$(find "$staging" -mindepth 1 -maxdepth 1 -type f -printf '%f\n' | sort)"
unexpected_entry="$(find "$staging" -mindepth 1 ! -type f -print -quit)"
[[ -z "$unexpected_entry" && "$actual_inventory" == "$expected_inventory" ]] || \
	die "Candidate X output inventory is not exact"
(
	cd "$staging"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$staging/SHA256SUMS"
(cd "$staging" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die "Candidate X output manifest failed"
chmod 0600 "$staging"/*
chmod 0755 "$staging/input-event-capture"
mv --no-clobber --no-target-directory -- "$staging" "$output"
[[ ! -e "$staging" && ! -L "$staging" && -d "$output" && ! -L "$output" ]] || \
	die "Candidate X destination appeared during atomic handoff"
staging=
trap - EXIT
post_handoff_nonregular="$(find "$output" -mindepth 1 ! -type f -print -quit)"
[[ -z "$post_handoff_nonregular" ]] || \
	die "Candidate X destination gained a non-regular entry"
post_handoff_inventory="$(find "$output" -mindepth 1 -maxdepth 1 -type f \
	-printf '%f\n' | sort)"
[[ "$post_handoff_inventory" == "$(printf 'SHA256SUMS\n%s\n' "$expected_inventory")" ]] || \
	die "Candidate X destination inventory changed during atomic handoff"
(cd "$output" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die "Candidate X destination manifest failed after atomic handoff"

printf 'validation=candidate-x-keyboard-manual-reboot\n'
printf 'candidate=%s/gemini-keyboard-manual-reboot.boot.img\n' "$output"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$X_BOOT_SHA256" "$X_BOOT_SIZE"
printf 'dtb_lineage=byte-exact-candidate-w\nvirtual_kernel_console=none\n'
printf 'watchdog_userspace=start-none,open-none,ping-none\n'
printf 'build_hardware_write=none\nflash=none\nruntime_result=not-tested\n'
