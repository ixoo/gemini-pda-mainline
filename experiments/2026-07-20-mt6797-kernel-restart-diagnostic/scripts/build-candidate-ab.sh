#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package EXACT_AB_PACKAGE --baseline EXACT_AA_R1_ARTIFACT --output-parent DIR\n' "$0" >&2
}

package=
baseline=
output_parent=
while (($#)); do
	case "$1" in
	--package|--baseline|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--baseline) baseline=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die 'run inside the Linux development VM'
case "$(uname -m)" in
aarch64|arm64) ;;
*) die 'Candidate AB must be built on Linux aarch64' ;;
esac
[[ -d "$package" && ! -L "$package" && -d "$baseline" && ! -L "$baseline" && \
	-d "$output_parent" && ! -L "$output_parent" ]] || \
	die 'exact AB package, exact AA r1 artifact, and output parent are required'
for command in awk basename chmod cmp cp dirname find git grep install mkdir \
	mktemp mv python3 rm sha256sum sort touch uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
baseline="$(cd -- "$baseline" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$package"|"$package"/*|"$baseline"|"$baseline"/*)
	die 'output parent must be outside repository, package, and AA baseline'
	;;
esac

manifest="$repo_root/kernel/manifest.json"
artifact_validator="$repo_root/scripts/validate-kernel-artifact"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
dispatch_validator="$repo_root/experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/scripts/validate-ash-dispatch.py"
aa_validator="$script_dir/validate-aa-baseline.py"
package_validator="$script_dir/validate-package.py"
initramfs_builder="$script_dir/build-initramfs.sh"
initramfs_validator="$script_dir/validate-initramfs.py"
boot_validator="$script_dir/validate-boot.py"
normalizer="$script_dir/normalize-build-json.py"
provenance_writer="$script_dir/write-provenance.py"
input_hasher="$script_dir/hash-input-tree.py"
final_validator="$script_dir/validate-final-artifact.py"
for input in "$manifest" "$artifact_validator" "$serializer" "$analyzer" \
	"$dispatch_validator" "$aa_validator" "$package_validator" \
	"$initramfs_builder" "$initramfs_validator" "$boot_validator" \
	"$normalizer" "$provenance_writer" "$input_hasher" "$final_validator"; do
	[[ -s "$input" && ! -L "$input" ]] || die "required repository input missing: $input"
done

repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
[[ "$repo_revision" =~ ^[0-9a-f]{40}$|^[0-9a-f]{64}$ ]] || \
	die 'repository revision is not a full object ID'
input_tree_at_start="$(python3 "$input_hasher" --repo-root "$repo_root")"

selected_paths=(
	"$package/SHA256SUMS"
	"$package/Image"
	"$package/Image.gz"
	"$package/System.map"
	"$package/kernel.config"
	"$package/dtbs/mediatek/mt6797-gemini-pda.dtb"
	"$package/provenance/build.json"
	"$baseline/SHA256SUMS"
	"$baseline/gemini-keyboard-console-map.boot.img"
	"$baseline/gemini-keyboard-console-map-initramfs.img"
	"$baseline/mt6797-gemini-pda-keyboard-console-map.dtb"
	"$baseline/gemini-us.bkeymap"
	"$baseline/console-unicode-mode"
	"$baseline/console-keymap-verify"
	"$baseline/input-event-capture"
)
hash_selected() {
	local path
	for path in "${selected_paths[@]}"; do
		[[ -f "$path" && ! -L "$path" ]] || die "selected input missing or unsafe: $path"
		sha256sum "$path"
	done
}
selected_at_start="$(hash_selected)"

workdir="$(mktemp -d "$output_parent/.candidate-AB.XXXXXX")"
cleanup() { [[ ! -d "$workdir" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
inputs="$workdir/validated-inputs"
replica="$workdir/replica"
mkdir "$stage" "$inputs" "$replica"

normalize_log() {
	local source=$1
	local temporary="${source}.normalized"
	while IFS= read -r line || [[ -n "$line" ]]; do
		line=${line//"$workdir"/@WORK@}
		line=${line//"$package"/@PACKAGE@}
		line=${line//"$baseline"/@CANDIDATE_AA_R1@}
		line=${line//"$repo_root"/@REPOSITORY@}
		case "$line" in
		generated_utc=*) line='generated_utc=@PACKAGE_GENERATED_UTC@' ;;
		build_json_sha256=*) line='build_json_sha256=@TIMESTAMP_VARIANT@' ;;
		package_sums_sha256=*) line='package_sums_sha256=@TIMESTAMP_VARIANT@' ;;
		esac
		printf '%s\n' "$line"
	done <"$source" >"$temporary"
	mv "$temporary" "$source"
}

python3 "$aa_validator" --artifact "$baseline" >"$stage/aa-baseline-validation.txt"
normalize_log "$stage/aa-baseline-validation.txt"
"$artifact_validator" "$package" >"$stage/package-validation.txt"
normalize_log "$stage/package-validation.txt"
python3 "$package_validator" --package "$package" --manifest "$manifest" \
	>"$stage/package-foundation.txt"
normalize_log "$stage/package-foundation.txt"
[[ "$(hash_selected)" == "$selected_at_start" ]] || \
	die 'selected package or AA inputs changed during validation'

# Snapshot every assembly byte only after all exact input validators pass.
install -m 0600 "$package/Image" "$inputs/Image"
install -m 0600 "$package/Image.gz" "$inputs/Image.gz"
install -m 0600 "$package/System.map" "$inputs/System.map"
install -m 0600 "$package/kernel.config" "$inputs/kernel.config"
install -m 0600 "$package/dtbs/mediatek/mt6797-gemini-pda.dtb" "$inputs/package.dtb"
install -m 0600 "$package/provenance/build.json" "$inputs/build.json"
install -m 0600 "$baseline/gemini-keyboard-console-map-initramfs.img" \
	"$inputs/aa-initramfs.img"
install -m 0600 "$baseline/mt6797-gemini-pda-keyboard-console-map.dtb" \
	"$inputs/aa.dtb"
install -m 0600 "$baseline/gemini-us.bkeymap" "$inputs/gemini-us.bkeymap"
install -m 0700 "$baseline/console-unicode-mode" "$inputs/console-unicode-mode"
install -m 0700 "$baseline/console-keymap-verify" "$inputs/console-keymap-verify"
install -m 0700 "$baseline/input-event-capture" "$inputs/input-event-capture"
[[ "$(hash_selected)" == "$selected_at_start" ]] || \
	die 'selected package or AA inputs changed during immutable snapshot'

candidate_initramfs="$stage/gemini-mt6797-kernel-restart-initramfs.img"
replica_initramfs="$replica/gemini-mt6797-kernel-restart-initramfs.img"
"$initramfs_builder" --baseline "$inputs/aa-initramfs.img" \
	--output "$candidate_initramfs" >"$stage/initramfs-build.txt"
normalize_log "$stage/initramfs-build.txt"
python3 "$initramfs_validator" --baseline "$inputs/aa-initramfs.img" \
	--candidate "$candidate_initramfs" --source-dir "$experiment_dir/initramfs" \
	>"$stage/initramfs-validation.txt"
normalize_log "$stage/initramfs-validation.txt"
"$initramfs_builder" --baseline "$inputs/aa-initramfs.img" \
	--output "$replica_initramfs" >/dev/null
cmp -s "$candidate_initramfs" "$replica_initramfs" || \
	die 'two Candidate AB initramfs constructions differ'
python3 "$dispatch_validator" --initramfs "$candidate_initramfs" \
	>"$stage/ash-dispatch-validation.txt"
normalize_log "$stage/ash-dispatch-validation.txt"

candidate_dtb="$stage/mt6797-gemini-pda-kernel-restart.dtb"
install -m 0600 "$inputs/aa.dtb" "$candidate_dtb"
candidate="$stage/gemini-mt6797-kernel-restart.boot.img"
replica_boot="$replica/gemini-mt6797-kernel-restart.boot.img"
bootopt=bootopt=64S3,32N2,64N2
python3 "$serializer" --kernel "$inputs/Image.gz" --ramdisk "$candidate_initramfs" \
	--dtb "$candidate_dtb" --output "$candidate" --name gemini-obs-L \
	--cmdline "$bootopt" --kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 \
	>"$stage/serializer.raw"
grep -v '^output=' "$stage/serializer.raw" >"$stage/serializer.txt"
rm "$stage/serializer.raw"
normalize_log "$stage/serializer.txt"
python3 "$serializer" --kernel "$inputs/Image.gz" --ramdisk "$replica_initramfs" \
	--dtb "$inputs/aa.dtb" --output "$replica_boot" --name gemini-obs-L \
	--cmdline "$bootopt" --kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 >/dev/null
cmp -s "$candidate" "$replica_boot" || \
	die 'two Candidate AB Android-v0 constructions differ'

python3 "$analyzer" --validate-lk --expected-image-gz "$inputs/Image.gz" \
	--expected-ramdisk "$candidate_initramfs" --expected-dtb "$candidate_dtb" \
	--expected-name gemini-obs-L --expected-cmdline "$bootopt" "$candidate" \
	>"$stage/analysis.txt"
normalize_log "$stage/analysis.txt"
python3 "$boot_validator" --candidate "$candidate" --image "$inputs/Image" \
	--image-gz "$inputs/Image.gz" --dtb "$candidate_dtb" \
	--initramfs "$candidate_initramfs" >"$stage/boot-validation.txt"
normalize_log "$stage/boot-validation.txt"
python3 "$boot_validator" --candidate "$replica_boot" --image "$inputs/Image" \
	--image-gz "$inputs/Image.gz" --dtb "$inputs/aa.dtb" \
	--initramfs "$replica_initramfs" >/dev/null

install -m 0600 "$inputs/Image.gz" "$stage/Image.gz"
install -m 0600 "$inputs/System.map" "$stage/System.map"
install -m 0600 "$inputs/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$inputs/console-unicode-mode" "$stage/console-unicode-mode"
install -m 0755 "$inputs/console-keymap-verify" "$stage/console-keymap-verify"
install -m 0755 "$inputs/input-event-capture" "$stage/input-event-capture"
python3 "$normalizer" --input "$inputs/build.json" --output "$stage/source-build.json"

input_tree_at_end="$(python3 "$input_hasher" --repo-root "$repo_root")"
[[ "$input_tree_at_end" == "$input_tree_at_start" ]] || \
	die 'repository build inputs changed during Candidate AB assembly'
[[ "$(git -C "$repo_root" rev-parse HEAD)" == "$repo_revision" ]] || \
	die 'repository revision changed during Candidate AB assembly'
[[ "$(hash_selected)" == "$selected_at_start" ]] || \
	die 'selected package or AA inputs changed during Candidate AB assembly'
printf '%s\n' "$input_tree_at_start" >"$stage/input-tree.sha256"
python3 "$provenance_writer" --output "$stage/provenance.txt" \
	--repo-revision "$repo_revision" --boot "$candidate" \
	--initramfs "$candidate_initramfs" --dtb "$candidate_dtb" \
	--image "$inputs/Image" --image-gz "$inputs/Image.gz" \
	--system-map "$inputs/System.map" --source-build "$stage/source-build.json"

expected_inventory="$(printf '%s\n' Image.gz System.map aa-baseline-validation.txt \
	analysis.txt ash-dispatch-validation.txt boot-validation.txt \
	console-keymap-verify console-unicode-mode \
	gemini-mt6797-kernel-restart-initramfs.img \
	gemini-mt6797-kernel-restart.boot.img gemini-us.bkeymap \
	initramfs-build.txt initramfs-validation.txt input-event-capture \
	input-tree.sha256 mt6797-gemini-pda-kernel-restart.dtb \
	package-foundation.txt package-validation.txt provenance.txt serializer.txt \
	source-build.json)"
actual_inventory="$(find "$stage" -mindepth 1 -maxdepth 1 -type f -printf '%f\n' | sort)"
unexpected_entry="$(find "$stage" -mindepth 1 ! -type f -print -quit)"
[[ -z "$unexpected_entry" && "$actual_inventory" == "$expected_inventory" ]] || \
	die 'Candidate AB output inventory is not exact'
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate AB output manifest failed'
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" "$stage/console-unicode-mode" \
	"$stage/input-event-capture"

candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
candidate_size="$(wc -c <"$candidate" | tr -d ' ')"
output_name="candidate-AB-mt6797-kernel-restart-final-${candidate_sha256:0:8}"
artifact="$workdir/$output_name"
mv --no-clobber --no-target-directory -- "$stage" "$artifact"
stage=
python3 "$final_validator" --artifact "$artifact" --baseline "$baseline" \
	--package "$package" --manifest "$manifest" >/dev/null
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv --no-clobber --no-target-directory -- "$artifact" "$output"
[[ -d "$output" && ! -L "$output" && ! -e "$artifact" ]] || \
	die 'atomic Candidate AB artifact handoff failed'
workdir=
trap - EXIT

printf 'validation=candidate-ab-mt6797-kernel-restart\n'
printf 'artifact=%s\n' "$output"
printf 'candidate=%s/gemini-mt6797-kernel-restart.boot.img\n' "$output"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$candidate_sha256" "$candidate_size"
printf 'dtb_lineage=byte-exact-hardware-passed-aa-r1\n'
printf 'keymap_and_gate=exact-aa-r1-with-attribution-only-shell-transform\n'
printf 'manual_reboot=busybox-reboot-no-sync-force\n'
printf 'watchdog_userspace=start-none,open-none,ping-none,countdown-none,fallback-none\n'
printf 'build_hardware_write=none\nflash=none\nruntime_result=not-tested\n'
