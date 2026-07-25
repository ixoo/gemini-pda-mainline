#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --baseline EXACT_X_ARTIFACT --output-parent DIR\n' "$0" >&2
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
[[ -d "$baseline" && ! -L "$baseline" && -d "$output_parent" && \
	! -L "$output_parent" ]] || die 'exact X baseline and output parent are required'
for command in awk basename chmod cmp cp dd dirname find git grep install mkdir mktemp mv \
	python3 rm sha256sum sort touch uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

readonly X_BASELINE_BASENAME=candidate-X-keyboard-manual-reboot-final-bf400387
readonly X_MANIFEST_SHA256=a37a774527385e93709bfeab8d93cc0797d908cdc596d046e16e934958218e52
readonly X_BOOT_SHA256=bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296
readonly X_INITRAMFS_SHA256=b54ce3cd75e7947ed867165e31abbf6ee6cbac7d41d171435f99bba7825bc769
readonly X_DTB_SHA256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
readonly X_HELPER_SHA256=b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602
readonly X_SOURCE_BUILD_SHA256=6c04e871811902799ff4fc68d2b4440ba2e42026b4ca8142e7bfbd425a0ce071
readonly BOOT2_CAPACITY=16777216

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
baseline="$(cd -- "$baseline" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
[[ "$(basename -- "$baseline")" == "$X_BASELINE_BASENAME" ]] || \
	die 'baseline basename is not exact Candidate X'
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$baseline"|"$baseline"/*)
	die 'output parent must be outside the repository and Candidate X baseline'
	;;
esac

x_validator="$script_dir/validate-x-baseline.py"
initramfs_builder="$script_dir/build-initramfs.sh"
initramfs_validator="$script_dir/validate-initramfs.py"
boot_builder="$script_dir/build-boot-from-x.py"
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
	scripts/validate-x-baseline.py
	scripts/build-initramfs.sh
	scripts/validate-initramfs.py
	scripts/build-boot-from-x.py
	scripts/validate-boot.py
	scripts/validate-final-artifact.py
	scripts/build-keyboard-typed-watchdog-reboot-candidate.sh
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
for input in "$x_validator" "$initramfs_builder" "$initramfs_validator" \
	"$boot_builder" "$boot_validator" "$final_validator" "$mutation_suite" "$analyzer"; do
	[[ -s "$input" && ! -L "$input" ]] || die "required script missing or unsafe: $input"
done
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == "$ANALYZER_SHA256" ]] || \
	die 'LK analyzer changed'

source_tree_at_start="$(hash_sources)"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
[[ "$repo_revision" =~ ^[0-9a-f]{40}$ || "$repo_revision" =~ ^[0-9a-f]{64}$ ]] || \
	die 'repository revision is not a full object ID'
staging="$(mktemp -d "$output_parent/.candidate-Y.XXXXXX")"
cleanup() { [[ ! -d "$staging" ]] || rm -rf -- "$staging"; }
trap cleanup EXIT

python3 "$x_validator" --baseline "$baseline" >"$staging/x-baseline-validation.txt"
inputs="$staging/.validated-inputs"
mkdir "$inputs"
install -m 0600 "$baseline/SHA256SUMS" "$inputs/x-SHA256SUMS"
install -m 0600 "$baseline/gemini-keyboard-manual-reboot.boot.img" "$inputs/x.boot.img"
install -m 0600 "$baseline/gemini-keyboard-manual-reboot-initramfs.img" "$inputs/x-initramfs.img"
install -m 0600 "$baseline/mt6797-gemini-pda-keyboard-manual-reboot.dtb" "$inputs/x.dtb"
install -m 0700 "$baseline/input-event-capture" "$inputs/input-event-capture"
install -m 0600 "$baseline/source-build.json" "$inputs/source-build.json"
dd if="$inputs/x.boot.img" of="$inputs/Image.gz" bs=1 skip=2048 count=5529675 status=none
chmod 0600 "$inputs/Image.gz"
for check in \
	"$inputs/x-SHA256SUMS:$X_MANIFEST_SHA256" \
	"$inputs/x.boot.img:$X_BOOT_SHA256" \
	"$inputs/x-initramfs.img:$X_INITRAMFS_SHA256" \
	"$inputs/x.dtb:$X_DTB_SHA256" \
	"$inputs/input-event-capture:$X_HELPER_SHA256" \
	"$inputs/source-build.json:$X_SOURCE_BUILD_SHA256" \
	"$inputs/Image.gz:d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41"; do
	path=${check%%:*}
	expected=${check##*:}
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || \
		die "immutable Candidate X input changed: $path"
done

y_initramfs="$staging/gemini-keyboard-typed-watchdog-reboot-initramfs.img"
y_boot="$staging/gemini-keyboard-typed-watchdog-reboot.boot.img"
y_dtb="$staging/mt6797-gemini-pda-keyboard-typed-watchdog-reboot.dtb"
install -m 0600 "$inputs/x.dtb" "$y_dtb"
"$initramfs_builder" --baseline "$inputs/x-initramfs.img" --output "$y_initramfs" \
	>"$staging/initramfs-build.txt"
python3 "$initramfs_validator" --baseline "$inputs/x-initramfs.img" \
	--candidate "$y_initramfs" --source-dir "$experiment_dir/initramfs" \
	>"$staging/initramfs-validation.txt"
python3 "$boot_builder" --x-boot "$inputs/x.boot.img" \
	--x-initramfs "$inputs/x-initramfs.img" --y-initramfs "$y_initramfs" \
	--output "$y_boot" >"$staging/boot-build.txt"
python3 "$boot_validator" --x-boot "$inputs/x.boot.img" \
	--x-initramfs "$inputs/x-initramfs.img" --y-boot "$y_boot" \
	--y-initramfs "$y_initramfs" --dtb "$y_dtb" >"$staging/boot-validation.txt"
python3 "$analyzer" --validate-lk --expected-image-gz "$inputs/Image.gz" \
	--expected-ramdisk "$y_initramfs" --expected-dtb "$y_dtb" \
	--expected-name gemini-obs-L --expected-cmdline bootopt=64S3,32N2,64N2 \
	"$y_boot" >"$staging/lk-analysis.txt"
[[ "$(grep -c '^gate_.*=yes$' "$staging/lk-analysis.txt")" == 32 ]] || \
	die 'LK analyzer did not pass all 32 gates'
grep -Fxq 'lk_validation=passed' "$staging/lk-analysis.txt" || \
	die 'LK analyzer did not report a passing result'

replica="$staging/.deterministic-replica"
mkdir "$replica"
"$initramfs_builder" --baseline "$inputs/x-initramfs.img" \
	--output "$replica/initramfs.img" >/dev/null
cmp -s "$y_initramfs" "$replica/initramfs.img" || \
	die 'independent Candidate Y initramfs reconstruction differs'
python3 "$boot_builder" --x-boot "$inputs/x.boot.img" \
	--x-initramfs "$inputs/x-initramfs.img" --y-initramfs "$replica/initramfs.img" \
	--output "$replica/boot.img" >/dev/null
cmp -s "$y_boot" "$replica/boot.img" || \
	die 'independent Candidate Y boot reconstruction differs'
python3 "$boot_validator" --x-boot "$inputs/x.boot.img" \
	--x-initramfs "$inputs/x-initramfs.img" --y-boot "$replica/boot.img" \
	--y-initramfs "$replica/initramfs.img" --dtb "$inputs/x.dtb" >/dev/null
rm -rf -- "$replica"

y_initramfs_sha256="$(sha256sum "$y_initramfs" | awk '{print $1}')"
y_boot_sha256="$(sha256sum "$y_boot" | awk '{print $1}')"
y_boot_size="$(wc -c <"$y_boot")"
[[ "$y_initramfs_sha256" =~ ^[0-9a-f]{64}$ && "$y_boot_sha256" =~ ^[0-9a-f]{64}$ ]] || \
	die 'generated Candidate Y checksum is malformed'
((y_boot_size > 0 && y_boot_size <= BOOT2_CAPACITY)) || \
	die 'generated Candidate Y exceeds boot2 capacity'
[[ "$(sha256sum "$y_dtb" | awk '{print $1}')" == "$X_DTB_SHA256" ]] || \
	die 'Candidate Y DTB changed during construction'

install -m 0755 "$inputs/input-event-capture" "$staging/input-event-capture"
install -m 0600 "$inputs/source-build.json" "$staging/source-build.json"
install -m 0600 "$inputs/Image.gz" "$staging/Image.gz"
printf '%s\n' "$source_tree_at_start" >"$staging/input-tree.sha256"
{
	printf 'experiment=2026-07-19-keyboard-typed-watchdog-reboot-diagnostic\n'
	printf 'candidate_label=Y\nmarker=GEMINI_KEYBOARD_TYPED_WATCHDOG_REBOOT_20260719_Y\n'
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'x_artifact_manifest_sha256=%s\nx_boot_sha256=%s\n' \
		"$X_MANIFEST_SHA256" "$X_BOOT_SHA256"
	printf 'x_initramfs_sha256=%s\nx_dtb_sha256=%s\n' \
		"$X_INITRAMFS_SHA256" "$X_DTB_SHA256"
	printf 'kernel_package=byte-exact-candidate-x\nkernel_field=byte-exact-candidate-x\n'
	printf 'dtb_lineage=byte-exact-candidate-x\nconfig_lineage=byte-exact-candidate-x\n'
	printf 'candidate_initramfs_sha256=%s\ncandidate_sha256=%s\ncandidate_size=%s\n' \
		"$y_initramfs_sha256" "$y_boot_sha256" "$y_boot_size"
	printf 'initramfs_delta=init,bin/local-shell,bin/reboot,bin/x-record\n'
	printf 'watchdog_ownership=typed-only\nwatchdog_timeout_seconds=31\n'
	printf 'watchdog_userspace_ping_count=one\nsoftware_reboot_fallback=none\n'
	printf 'deterministic_replica=initramfs-and-android-v0-byte-identical\n'
	printf 'boot2_capacity=%s\nstorage_access=none\nruntime_networking=none\n' "$BOOT2_CAPACITY"
	printf 'hardware_write=none\nflash=none\nruntime_result=not-tested\n'
} >"$staging/provenance.txt"
rm -rf -- "$inputs"

source_tree_at_end="$(hash_sources)"
[[ "$source_tree_at_end" == "$source_tree_at_start" ]] || \
	die 'repository inputs changed during Candidate Y construction'
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == "$ANALYZER_SHA256" ]] || \
	die 'LK analyzer changed during Candidate Y construction'
python3 "$x_validator" --baseline "$baseline" >/dev/null || \
	die 'Candidate X baseline changed during Candidate Y construction'
[[ "$(git -C "$repo_root" rev-parse HEAD)" == "$repo_revision" ]] || \
	die 'repository revision changed during Candidate Y construction'

expected_inventory="$(printf '%s\n' Image.gz boot-build.txt boot-validation.txt \
	gemini-keyboard-typed-watchdog-reboot-initramfs.img \
	gemini-keyboard-typed-watchdog-reboot.boot.img initramfs-build.txt \
	initramfs-validation.txt input-event-capture input-tree.sha256 \
	lk-analysis.txt mt6797-gemini-pda-keyboard-typed-watchdog-reboot.dtb provenance.txt \
	source-build.json x-baseline-validation.txt)"
actual_inventory="$(find "$staging" -mindepth 1 -maxdepth 1 -type f -printf '%f\n' | sort)"
unexpected="$(find "$staging" -mindepth 1 ! -type f -print -quit)"
[[ -z "$unexpected" && "$actual_inventory" == "$expected_inventory" ]] || \
	die 'Candidate Y output inventory is not exact'
(
	cd "$staging"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$staging/SHA256SUMS"
(cd "$staging" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate Y output manifest failed'
chmod 0600 "$staging"/*
chmod 0755 "$staging/input-event-capture"

output_name="candidate-Y-keyboard-typed-watchdog-reboot-final-${y_boot_sha256:0:8}"
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv --no-clobber --no-target-directory -- "$staging" "$output"
[[ -d "$output" && ! -L "$output" && ! -e "$staging" ]] || \
	die 'atomic Candidate Y output handoff failed'
staging=
trap - EXIT
(cd "$output" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate Y output manifest failed after handoff'
python3 "$final_validator" --artifact "$output" --baseline "$baseline" >/dev/null || \
	die 'Candidate Y final artifact failed post-handoff validation'

printf 'validation=candidate-y-keyboard-typed-watchdog-reboot\n'
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-keyboard-typed-watchdog-reboot.boot.img\n' "$output"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$y_boot_sha256" "$y_boot_size"
printf 'candidate_initramfs_sha256=%s\n' "$y_initramfs_sha256"
printf 'kernel_dtb_config=byte-exact-candidate-x\nwatchdog_ownership=typed-only\n'
printf 'hardware_write=none\nflash=none\nruntime_result=not-tested\n'
