#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --baseline EXACT_Y_ARTIFACT --output-parent DIR\n' "$0" >&2
}

baseline=
output_parent=
while (($#)); do
	case "$1" in
	--baseline|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
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
*) die 'exact BusyBox dispatch validation requires a Linux aarch64 host' ;;
esac
[[ -d "$baseline" && ! -L "$baseline" && -d "$output_parent" && \
	! -L "$output_parent" ]] || die 'exact Y baseline and output parent are required'
for command in awk basename chmod cmp cp dd dirname find git grep install mkdir mktemp mv \
	python3 rm sha256sum sort touch uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

readonly Y_BASELINE_BASENAME=candidate-Y-keyboard-typed-watchdog-reboot-final-94edd593
readonly Y_MANIFEST_SHA256=310ac503b4bbd8c5a3d5c31bcecb473064d5207ff30ad73111325ffe1a1c56a6
readonly Y_BOOT_SHA256=94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee
readonly Y_INITRAMFS_SHA256=11b0a8ecb144ebde0c9802e0cf7357b2d74b95e8ba44fbf6007a9f4d0d8bf3e2
readonly Y_DTB_SHA256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
readonly Y_IMAGE_GZ_SHA256=d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41
readonly Y_HELPER_SHA256=b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602
readonly Y_SOURCE_BUILD_SHA256=6c04e871811902799ff4fc68d2b4440ba2e42026b4ca8142e7bfbd425a0ce071
readonly BOOT2_CAPACITY=16777216

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
baseline="$(cd -- "$baseline" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
[[ "$(basename -- "$baseline")" == "$Y_BASELINE_BASENAME" ]] || \
	die 'baseline basename is not exact Candidate Y'
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$baseline"|"$baseline"/*)
	die 'output parent must be outside the repository and Candidate Y baseline'
	;;
esac

y_validator="$script_dir/validate-y-baseline.py"
initramfs_builder="$script_dir/build-initramfs.sh"
initramfs_validator="$script_dir/validate-initramfs.py"
dispatch_validator="$script_dir/validate-ash-dispatch.py"
boot_builder="$script_dir/build-boot-from-y.py"
boot_validator="$script_dir/validate-boot.py"
final_validator="$script_dir/validate-final-artifact.py"
mutation_suite="$script_dir/test-validator-mutations.sh"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95
source_paths=(
	initramfs/init
	initramfs/local-shell
	initramfs/reboot
	initramfs/x-record
	initramfs/reboot-dispatch.env
	scripts/validate-y-baseline.py
	scripts/build-initramfs.sh
	scripts/validate-initramfs.py
	scripts/validate-ash-dispatch.py
	scripts/build-boot-from-y.py
	scripts/validate-boot.py
	scripts/validate-final-artifact.py
	scripts/build-keyboard-reboot-dispatch-candidate.sh
	scripts/test-validator-mutations.sh
)
hash_sources() {
	local checksum
	local relative
	for relative in "${source_paths[@]}"; do
		[[ -f "$experiment_dir/$relative" && ! -L "$experiment_dir/$relative" ]] || \
			die "repository input missing or unsafe: $relative"
		checksum="$(sha256sum "$experiment_dir/$relative" | awk '{print $1}')"
		[[ "$checksum" =~ ^[0-9a-f]{64}$ ]] || die "malformed source hash: $relative"
		printf '%s  %s\n' "$checksum" "$relative"
	done
}
for input in "$y_validator" "$initramfs_builder" "$initramfs_validator" \
	"$dispatch_validator" "$boot_builder" "$boot_validator" "$final_validator" \
	"$mutation_suite" "$analyzer"; do
	[[ -s "$input" && ! -L "$input" ]] || die "required script missing or unsafe: $input"
done
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == "$ANALYZER_SHA256" ]] || \
	die 'LK analyzer changed'

source_tree_at_start="$(hash_sources)"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
[[ "$repo_revision" =~ ^[0-9a-f]{40}$ || "$repo_revision" =~ ^[0-9a-f]{64}$ ]] || \
	die 'repository revision is not a full object ID'
staging="$(mktemp -d "$output_parent/.candidate-Z.XXXXXX")"
cleanup() { [[ ! -d "$staging" ]] || rm -rf -- "$staging"; }
trap cleanup EXIT

python3 "$y_validator" --baseline "$baseline" >"$staging/y-baseline-validation.txt"
inputs="$staging/.validated-inputs"
mkdir "$inputs"
install -m 0600 "$baseline/SHA256SUMS" "$inputs/y-SHA256SUMS"
install -m 0600 "$baseline/gemini-keyboard-typed-watchdog-reboot.boot.img" \
	"$inputs/y.boot.img"
install -m 0600 "$baseline/gemini-keyboard-typed-watchdog-reboot-initramfs.img" \
	"$inputs/y-initramfs.img"
install -m 0600 "$baseline/mt6797-gemini-pda-keyboard-typed-watchdog-reboot.dtb" \
	"$inputs/y.dtb"
install -m 0700 "$baseline/input-event-capture" "$inputs/input-event-capture"
install -m 0600 "$baseline/source-build.json" "$inputs/source-build.json"
dd if="$inputs/y.boot.img" of="$inputs/Image.gz" bs=1 skip=2048 count=5529675 status=none
chmod 0600 "$inputs/Image.gz"
for check in \
	"$inputs/y-SHA256SUMS:$Y_MANIFEST_SHA256" \
	"$inputs/y.boot.img:$Y_BOOT_SHA256" \
	"$inputs/y-initramfs.img:$Y_INITRAMFS_SHA256" \
	"$inputs/y.dtb:$Y_DTB_SHA256" \
	"$inputs/input-event-capture:$Y_HELPER_SHA256" \
	"$inputs/source-build.json:$Y_SOURCE_BUILD_SHA256" \
	"$inputs/Image.gz:$Y_IMAGE_GZ_SHA256"; do
	path=${check%%:*}
	expected=${check##*:}
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || \
		die "immutable Candidate Y input changed: $path"
done

z_initramfs="$staging/gemini-keyboard-reboot-dispatch-initramfs.img"
z_boot="$staging/gemini-keyboard-reboot-dispatch.boot.img"
z_dtb="$staging/mt6797-gemini-pda-keyboard-reboot-dispatch.dtb"
dispatch_result="$staging/ash-dispatch-validation.txt"
install -m 0600 "$inputs/y.dtb" "$z_dtb"
"$initramfs_builder" --baseline "$inputs/y-initramfs.img" --output "$z_initramfs" \
	--dispatch-result "$dispatch_result" >"$staging/initramfs-build.txt"
python3 "$initramfs_validator" --baseline "$inputs/y-initramfs.img" \
	--candidate "$z_initramfs" --source-dir "$experiment_dir/initramfs" \
	>"$staging/initramfs-validation.txt"
python3 "$dispatch_validator" --initramfs "$z_initramfs" \
	--verify-saved "$dispatch_result" >/dev/null
python3 "$boot_builder" --y-boot "$inputs/y.boot.img" \
	--y-initramfs "$inputs/y-initramfs.img" --z-initramfs "$z_initramfs" \
	--output "$z_boot" >"$staging/boot-build.txt"
python3 "$boot_validator" --y-boot "$inputs/y.boot.img" \
	--y-initramfs "$inputs/y-initramfs.img" --z-boot "$z_boot" \
	--z-initramfs "$z_initramfs" --dtb "$z_dtb" >"$staging/boot-validation.txt"
python3 "$analyzer" --validate-lk --expected-image-gz "$inputs/Image.gz" \
	--expected-ramdisk "$z_initramfs" --expected-dtb "$z_dtb" \
	--expected-name gemini-obs-L --expected-cmdline bootopt=64S3,32N2,64N2 \
	"$z_boot" >"$staging/lk-analysis.txt"
[[ "$(grep -c '^gate_.*=yes$' "$staging/lk-analysis.txt")" == 32 ]] || \
	die 'LK analyzer did not pass all 32 gates'
grep -Fxq 'lk_validation=passed' "$staging/lk-analysis.txt" || \
	die 'LK analyzer did not report a passing result'

replica="$staging/.deterministic-replica"
mkdir "$replica"
"$initramfs_builder" --baseline "$inputs/y-initramfs.img" \
	--output "$replica/initramfs.img" \
	--dispatch-result "$replica/ash-dispatch-validation.txt" >/dev/null
cmp -s "$z_initramfs" "$replica/initramfs.img" || \
	die 'independent Candidate Z initramfs reconstruction differs'
cmp -s "$dispatch_result" "$replica/ash-dispatch-validation.txt" || \
	die 'independent Candidate Z dynamic dispatch result differs'
python3 "$boot_builder" --y-boot "$inputs/y.boot.img" \
	--y-initramfs "$inputs/y-initramfs.img" --z-initramfs "$replica/initramfs.img" \
	--output "$replica/boot.img" >/dev/null
cmp -s "$z_boot" "$replica/boot.img" || \
	die 'independent Candidate Z boot reconstruction differs'
python3 "$boot_validator" --y-boot "$inputs/y.boot.img" \
	--y-initramfs "$inputs/y-initramfs.img" --z-boot "$replica/boot.img" \
	--z-initramfs "$replica/initramfs.img" --dtb "$inputs/y.dtb" >/dev/null
rm -rf -- "$replica"

z_initramfs_sha256="$(sha256sum "$z_initramfs" | awk '{print $1}')"
z_boot_sha256="$(sha256sum "$z_boot" | awk '{print $1}')"
z_boot_size="$(wc -c <"$z_boot")"
[[ "$z_initramfs_sha256" =~ ^[0-9a-f]{64}$ && "$z_boot_sha256" =~ ^[0-9a-f]{64}$ ]] || \
	die 'generated Candidate Z checksum is malformed'
((z_boot_size > 0 && z_boot_size <= BOOT2_CAPACITY)) || \
	die 'generated Candidate Z exceeds boot2 capacity'
[[ "$(sha256sum "$z_dtb" | awk '{print $1}')" == "$Y_DTB_SHA256" ]] || \
	die 'Candidate Z DTB changed during construction'

install -m 0755 "$inputs/input-event-capture" "$staging/input-event-capture"
install -m 0600 "$inputs/source-build.json" "$staging/source-build.json"
install -m 0600 "$inputs/Image.gz" "$staging/Image.gz"
printf '%s\n' "$source_tree_at_start" >"$staging/input-tree.sha256"
{
	printf 'experiment=2026-07-19-keyboard-reboot-dispatch-diagnostic\n'
	printf 'candidate_label=Z\nmarker=GEMINI_KEYBOARD_REBOOT_DISPATCH_20260719_Z\n'
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'y_artifact_manifest_sha256=%s\ny_boot_sha256=%s\n' \
		"$Y_MANIFEST_SHA256" "$Y_BOOT_SHA256"
	printf 'y_initramfs_sha256=%s\ny_dtb_sha256=%s\n' \
		"$Y_INITRAMFS_SHA256" "$Y_DTB_SHA256"
	printf 'kernel_package=byte-exact-candidate-y\nkernel_field=byte-exact-candidate-y\n'
	printf 'dtb_lineage=byte-exact-candidate-y\nconfig_lineage=byte-exact-candidate-y\n'
	printf 'candidate_initramfs_sha256=%s\ncandidate_sha256=%s\ncandidate_size=%s\n' \
		"$z_initramfs_sha256" "$z_boot_sha256" "$z_boot_size"
	printf 'initramfs_delta=init,bin/local-shell,bin/reboot,bin/x-record,+bin/reboot-dispatch.env:0444\n'
	printf 'reboot_dispatch=ENV-alias-absolute-wrapper\n'
	printf 'runtime_dispatch_oracle=inherited-exported-ENV\n'
	printf 'dispatch_validation=exact-busybox-dynamic-linux-aarch64\n'
	printf 'clean_tty1_background=yes\n'
	printf 'watchdog_ownership=typed-only\nwatchdog_timeout_seconds=31\n'
	printf 'watchdog_userspace_ping_count=one\nsoftware_reboot_fallback=none\n'
	printf 'deterministic_replica=initramfs-dispatch-result-and-android-v0-byte-identical\n'
	printf 'boot2_capacity=%s\nstorage_access=none\nruntime_networking=none\n' "$BOOT2_CAPACITY"
	printf 'hardware_write=none\nflash=none\nruntime_result=not-tested\n'
} >"$staging/provenance.txt"
rm -rf -- "$inputs"

source_tree_at_end="$(hash_sources)"
[[ "$source_tree_at_end" == "$source_tree_at_start" ]] || \
	die 'repository inputs changed during Candidate Z construction'
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == "$ANALYZER_SHA256" ]] || \
	die 'LK analyzer changed during Candidate Z construction'
python3 "$y_validator" --baseline "$baseline" >/dev/null || \
	die 'Candidate Y baseline changed during Candidate Z construction'
[[ "$(git -C "$repo_root" rev-parse HEAD)" == "$repo_revision" ]] || \
	die 'repository revision changed during Candidate Z construction'

expected_inventory="$(printf '%s\n' Image.gz ash-dispatch-validation.txt \
	boot-build.txt boot-validation.txt gemini-keyboard-reboot-dispatch-initramfs.img \
	gemini-keyboard-reboot-dispatch.boot.img initramfs-build.txt \
	initramfs-validation.txt input-event-capture input-tree.sha256 lk-analysis.txt \
	mt6797-gemini-pda-keyboard-reboot-dispatch.dtb provenance.txt source-build.json \
	y-baseline-validation.txt)"
actual_inventory="$(find "$staging" -mindepth 1 -maxdepth 1 -type f -printf '%f\n' | sort)"
unexpected="$(find "$staging" -mindepth 1 ! -type f -print -quit)"
[[ -z "$unexpected" && "$actual_inventory" == "$expected_inventory" ]] || \
	die 'Candidate Z output inventory is not exact'
(
	cd "$staging"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$staging/SHA256SUMS"
(cd "$staging" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate Z output manifest failed'
chmod 0600 "$staging"/*
chmod 0755 "$staging/input-event-capture"

output_name="candidate-Z-keyboard-reboot-dispatch-final-${z_boot_sha256:0:8}"
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv --no-clobber --no-target-directory -- "$staging" "$output"
[[ -d "$output" && ! -L "$output" && ! -e "$staging" ]] || \
	die 'atomic Candidate Z output handoff failed'
staging=
trap - EXIT
(cd "$output" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate Z output manifest failed after handoff'
python3 "$final_validator" --artifact "$output" --baseline "$baseline" >/dev/null || \
	die 'Candidate Z final artifact failed post-handoff validation'

printf 'validation=candidate-z-keyboard-reboot-dispatch\n'
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-keyboard-reboot-dispatch.boot.img\n' "$output"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$z_boot_sha256" "$z_boot_size"
printf 'candidate_initramfs_sha256=%s\n' "$z_initramfs_sha256"
printf 'kernel_dtb_config=byte-exact-candidate-y\n'
printf 'reboot_dispatch=ENV-alias-absolute-wrapper\n'
printf 'watchdog_ownership=typed-only\n'
printf 'hardware_write=none\nflash=none\nruntime_result=not-tested\n'
