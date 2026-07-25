#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --baseline EXACT_Z_ARTIFACT --defkeymap FILE --output-parent DIR\n' "$0" >&2
}

baseline=
defkeymap=
output_parent=
while (($#)); do
	case "$1" in
	--baseline|--defkeymap|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--baseline) baseline=$2 ;;
		--defkeymap) defkeymap=$2 ;;
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
*) die 'Candidate AA must be built on Linux aarch64' ;;
esac
[[ -d "$baseline" && ! -L "$baseline" && -f "$defkeymap" && ! -L "$defkeymap" && \
	-d "$output_parent" && ! -L "$output_parent" ]] || \
	die 'exact Z baseline, pinned defkeymap source, and output parent are required'
for command in awk basename chmod cmp cp dd dirname find git grep install mkdir \
	mktemp mv python3 rm sha256sum sort touch uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

readonly Z_BASELINE_NAME=candidate-Z-keyboard-reboot-dispatch-final-985a6472
readonly Z_MANIFEST_SHA256=534484e5362e1e4c73ec8438bd36656b444e88199dbd17724a160c75403dbaaa
readonly Z_BOOT_SHA256=985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9
readonly Z_INITRAMFS_SHA256=a21cc6bed9024bba9e01864aeb0c6c3339231d217f77ff5fa733ea33e6a0e7d2
readonly Z_DTB_SHA256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
readonly Z_IMAGE_GZ_SHA256=d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41
readonly Z_HELPER_SHA256=b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602
readonly Z_SOURCE_BUILD_SHA256=6c04e871811902799ff4fc68d2b4440ba2e42026b4ca8142e7bfbd425a0ce071
readonly DEFKEYMAP_SHA256=318f48316e6bed5ada064879535ec2bca470dc1a8b8c9abd1d92da81bb2c6c7c
readonly KEYMAP_SHA256=02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c
readonly UNICODE_SOURCE_SHA256=4a3f8064dddb5845886453bc0fdc5753e87b3f6ef8ce064c0c2a32fb7c7bf357
readonly UNICODE_HELPER_SHA256=5949ee28aedeb8f8ba7b5486abbec7714034f7b833265bace9a1438b8a1dd650
readonly VERIFIER_SOURCE_SHA256=70d70bcef6e403d850c32b85f4bab928b2eb1444fae68ec3f629d7ff7c22785d
readonly KEYMAP_VERIFIER_SHA256=29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238
readonly BOOT2_CAPACITY=16777216

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
baseline="$(cd -- "$baseline" && pwd -P)"
defkeymap="$(cd -- "$(dirname -- "$defkeymap")" && pwd -P)/$(basename -- "$defkeymap")"
output_parent="$(cd -- "$output_parent" && pwd -P)"
[[ "$(basename -- "$baseline")" == "$Z_BASELINE_NAME" ]] || \
	die 'baseline basename is not exact Candidate Z'
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$baseline"|"$baseline"/*)
	die 'output parent must be outside the repository and Candidate Z baseline'
	;;
esac
[[ "$(sha256sum "$defkeymap" | awk '{print $1}')" == "$DEFKEYMAP_SHA256" ]] || \
	die 'defkeymap source identity mismatch'

baseline_validator="$script_dir/validate-z-baseline.py"
initramfs_builder="$script_dir/build-initramfs.sh"
initramfs_validator="$script_dir/validate-initramfs.py"
keymap_validator="$script_dir/validate-console-keymap.py"
keymap_test="$script_dir/test-console-keymap.py"
verifier_test="$script_dir/test-keymap-verifier.py"
boot_builder="$script_dir/build-boot-from-z.py"
boot_validator="$script_dir/validate-boot.py"
final_validator="$script_dir/validate-final-artifact.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95
source_paths=(
	initramfs/init
	initramfs/local-shell
	initramfs/x-record
	src/console-unicode-mode.c
	src/console-keymap-verify.c
	scripts/generate-console-keymap.py
	scripts/validate-console-keymap.py
	scripts/test-console-keymap.py
	scripts/test-keymap-verifier.py
	scripts/validate-z-baseline.py
	scripts/build-initramfs.sh
	scripts/validate-initramfs.py
	scripts/build-boot-from-z.py
	scripts/validate-boot.py
	scripts/validate-final-artifact.py
	scripts/build-keyboard-console-map-candidate.sh
	scripts/test-validator-mutations.py
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
for input in "$baseline_validator" "$initramfs_builder" "$initramfs_validator" \
	"$keymap_validator" "$keymap_test" "$verifier_test" "$boot_builder" \
	"$boot_validator" "$analyzer"; do
	[[ -s "$input" && ! -L "$input" ]] || die "required script missing or unsafe: $input"
done
[[ -s "$final_validator" && ! -L "$final_validator" ]] || \
	die "required script missing or unsafe: $final_validator"
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == "$ANALYZER_SHA256" ]] || \
	die 'LK analyzer changed'

source_tree_at_start="$(hash_sources)"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
[[ "$repo_revision" =~ ^[0-9a-f]{40}$ || "$repo_revision" =~ ^[0-9a-f]{64}$ ]] || \
	die 'repository revision is not a full object ID'
staging="$(mktemp -d "$output_parent/.candidate-AA.XXXXXX")"
cleanup() { [[ ! -d "$staging" ]] || rm -rf -- "$staging"; }
trap cleanup EXIT

python3 "$baseline_validator" --baseline "$baseline" >"$staging/z-baseline-validation.txt"
inputs="$staging/.validated-inputs"
mkdir "$inputs"
install -m 0600 "$baseline/SHA256SUMS" "$inputs/z-SHA256SUMS"
install -m 0600 "$baseline/gemini-keyboard-reboot-dispatch.boot.img" "$inputs/z.boot.img"
install -m 0600 "$baseline/gemini-keyboard-reboot-dispatch-initramfs.img" "$inputs/z-initramfs.img"
install -m 0600 "$baseline/mt6797-gemini-pda-keyboard-reboot-dispatch.dtb" "$inputs/z.dtb"
install -m 0600 "$baseline/Image.gz" "$inputs/Image.gz"
install -m 0700 "$baseline/input-event-capture" "$inputs/input-event-capture"
install -m 0600 "$baseline/source-build.json" "$inputs/source-build.json"
for check in \
	"$inputs/z-SHA256SUMS:$Z_MANIFEST_SHA256" \
	"$inputs/z.boot.img:$Z_BOOT_SHA256" \
	"$inputs/z-initramfs.img:$Z_INITRAMFS_SHA256" \
	"$inputs/z.dtb:$Z_DTB_SHA256" \
	"$inputs/Image.gz:$Z_IMAGE_GZ_SHA256" \
	"$inputs/input-event-capture:$Z_HELPER_SHA256" \
	"$inputs/source-build.json:$Z_SOURCE_BUILD_SHA256"; do
	path=${check%%:*}
	expected=${check##*:}
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || \
		die "immutable Candidate Z input changed: $path"
done

aa_initramfs="$staging/gemini-keyboard-console-map-initramfs.img"
aa_boot="$staging/gemini-keyboard-console-map.boot.img"
aa_dtb="$staging/mt6797-gemini-pda-keyboard-console-map.dtb"
keymap="$staging/gemini-us.bkeymap"
unicode_helper="$staging/console-unicode-mode"
keymap_verifier="$staging/console-keymap-verify"
install -m 0600 "$inputs/z.dtb" "$aa_dtb"
"$initramfs_builder" --baseline "$inputs/z-initramfs.img" --defkeymap "$defkeymap" \
	--output "$aa_initramfs" --keymap-output "$keymap" \
	--helper-output "$unicode_helper" --verifier-output "$keymap_verifier" \
	>"$staging/initramfs-build.txt"
python3 "$keymap_validator" --source "$defkeymap" --keymap "$keymap" \
	>"$staging/keymap-validation.txt"
python3 "$keymap_test" --source "$defkeymap" >"$staging/keymap-test.txt"
python3 "$verifier_test" --verifier "$keymap_verifier" --keymap "$keymap" \
	>"$staging/keymap-verifier-test.txt"
python3 "$initramfs_validator" --baseline "$inputs/z-initramfs.img" \
	--candidate "$aa_initramfs" --source-dir "$experiment_dir/initramfs" \
	--keymap "$keymap" --unicode-helper "$unicode_helper" \
	--keymap-verifier "$keymap_verifier" \
	>"$staging/initramfs-validation.txt"
python3 "$boot_builder" --z-boot "$inputs/z.boot.img" \
	--z-initramfs "$inputs/z-initramfs.img" --aa-initramfs "$aa_initramfs" \
	--output "$aa_boot" >"$staging/boot-build.txt"
python3 "$boot_validator" --z-boot "$inputs/z.boot.img" \
	--z-initramfs "$inputs/z-initramfs.img" --aa-boot "$aa_boot" \
	--aa-initramfs "$aa_initramfs" --dtb "$aa_dtb" \
	>"$staging/boot-validation.txt"
python3 "$analyzer" --validate-lk --expected-image-gz "$inputs/Image.gz" \
	--expected-ramdisk "$aa_initramfs" --expected-dtb "$aa_dtb" \
	--expected-name gemini-obs-L --expected-cmdline bootopt=64S3,32N2,64N2 \
	"$aa_boot" >"$staging/lk-analysis.txt"
[[ "$(grep -c '^gate_.*=yes$' "$staging/lk-analysis.txt")" == 32 ]] || \
	die 'LK analyzer did not pass all 32 gates'
grep -Fxq 'lk_validation=passed' "$staging/lk-analysis.txt" || \
	die 'LK analyzer did not report a passing result'

replica="$staging/.deterministic-replica"
mkdir "$replica"
"$initramfs_builder" --baseline "$inputs/z-initramfs.img" --defkeymap "$defkeymap" \
	--output "$replica/initramfs.img" --keymap-output "$replica/keymap" \
	--helper-output "$replica/helper" --verifier-output "$replica/verifier" >/dev/null
for pair in "$aa_initramfs:$replica/initramfs.img" "$keymap:$replica/keymap" \
	"$unicode_helper:$replica/helper" "$keymap_verifier:$replica/verifier"; do
	cmp -s "${pair%%:*}" "${pair##*:}" || die "deterministic replica differs: $pair"
done
python3 "$boot_builder" --z-boot "$inputs/z.boot.img" \
	--z-initramfs "$inputs/z-initramfs.img" --aa-initramfs "$replica/initramfs.img" \
	--output "$replica/boot.img" >/dev/null
cmp -s "$aa_boot" "$replica/boot.img" || die 'independent Candidate AA boot differs'
rm -rf -- "$replica"

aa_initramfs_sha256="$(sha256sum "$aa_initramfs" | awk '{print $1}')"
aa_boot_sha256="$(sha256sum "$aa_boot" | awk '{print $1}')"
aa_boot_size="$(wc -c <"$aa_boot")"
unicode_helper_sha256="$(sha256sum "$unicode_helper" | awk '{print $1}')"
keymap_verifier_sha256="$(sha256sum "$keymap_verifier" | awk '{print $1}')"
[[ "$aa_initramfs_sha256" =~ ^[0-9a-f]{64}$ && "$aa_boot_sha256" =~ ^[0-9a-f]{64}$ ]] || \
	die 'generated Candidate AA checksum is malformed'
((aa_boot_size > 0 && aa_boot_size <= BOOT2_CAPACITY)) || \
	die 'generated Candidate AA exceeds boot2 capacity'
[[ "$(sha256sum "$aa_dtb" | awk '{print $1}')" == "$Z_DTB_SHA256" ]] || \
	die 'Candidate AA DTB changed during construction'
[[ "$(sha256sum "$experiment_dir/src/console-unicode-mode.c" | awk '{print $1}')" == \
	"$UNICODE_SOURCE_SHA256" && "$unicode_helper_sha256" == "$UNICODE_HELPER_SHA256" ]] || \
	die 'console Unicode helper source or binary identity changed'
[[ "$(sha256sum "$experiment_dir/src/console-keymap-verify.c" | awk '{print $1}')" == \
	"$VERIFIER_SOURCE_SHA256" && "$keymap_verifier_sha256" == \
	"$KEYMAP_VERIFIER_SHA256" ]] || die 'console keymap verifier source or binary identity changed'

install -m 0755 "$inputs/input-event-capture" "$staging/input-event-capture"
install -m 0600 "$inputs/source-build.json" "$staging/source-build.json"
install -m 0600 "$inputs/Image.gz" "$staging/Image.gz"
printf '%s\n' "$source_tree_at_start" >"$staging/input-tree.sha256"
{
	printf 'experiment=2026-07-20-keyboard-console-map-diagnostic\n'
	printf 'candidate_label=AA\ncandidate_revision=r1\nmarker=GEMINI_KEYBOARD_CONSOLE_MAP_20260720_AA_R1\n'
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'z_artifact_manifest_sha256=%s\nz_boot_sha256=%s\n' \
		"$Z_MANIFEST_SHA256" "$Z_BOOT_SHA256"
	printf 'z_initramfs_sha256=%s\nz_dtb_sha256=%s\n' \
		"$Z_INITRAMFS_SHA256" "$Z_DTB_SHA256"
	printf 'kernel_package=byte-exact-candidate-z\nkernel_field=byte-exact-candidate-z\n'
	printf 'dtb_lineage=byte-exact-candidate-z\nconfig_lineage=byte-exact-candidate-z\n'
	printf 'candidate_initramfs_sha256=%s\ncandidate_sha256=%s\ncandidate_size=%s\n' \
		"$aa_initramfs_sha256" "$aa_boot_sha256" "$aa_boot_size"
	printf 'initramfs_delta=init,bin/local-shell,bin/x-record,+bin/console-keymap-verify:0755,+bin/console-unicode-mode:0755,+etc/gemini-us.bkeymap:0444\n'
	printf 'keymap_source_sha256=%s\nkeymap_sha256=%s\n' \
		"$DEFKEYMAP_SHA256" "$KEYMAP_SHA256"
	printf 'unicode_helper_source_sha256=%s\nunicode_helper_sha256=%s\n' \
		"$UNICODE_SOURCE_SHA256" "$unicode_helper_sha256"
	printf 'keymap_verifier_source_sha256=%s\nkeymap_verifier_sha256=%s\n' \
		"$VERIFIER_SOURCE_SHA256" "$keymap_verifier_sha256"
	printf 'keymap_runtime_gate=sha256-K_UNICODE-existing-KDG-or-preflight-load-KDGKBENT-2048-kernel-entries\n'
	printf 'keyboard_matrix=byte-exact-candidate-z\nreboot_dispatch=byte-exact-candidate-z\n'
	printf 'watchdog_recovery=byte-exact-candidate-z\nwatchdog_ownership=typed-only\n'
	printf 'software_reboot_fallback=none\nclean_tty1_background=yes\n'
	printf 'deterministic_replica=helpers-keymap-initramfs-and-android-v0-byte-identical\n'
	printf 'boot2_capacity=%s\nstorage_access=none\nruntime_networking=none\n' "$BOOT2_CAPACITY"
	printf 'hardware_write=none\nflash=none\nruntime_result=not-tested\n'
} >"$staging/provenance.txt"
rm -rf -- "$inputs"

[[ "$(hash_sources)" == "$source_tree_at_start" ]] || \
	die 'repository inputs changed during Candidate AA construction'
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == "$ANALYZER_SHA256" ]] || \
	die 'LK analyzer changed during Candidate AA construction'
python3 "$baseline_validator" --baseline "$baseline" >/dev/null || \
	die 'Candidate Z baseline changed during Candidate AA construction'
[[ "$(git -C "$repo_root" rev-parse HEAD)" == "$repo_revision" ]] || \
	die 'repository revision changed during Candidate AA construction'

expected_inventory="$(printf '%s\n' Image.gz boot-build.txt boot-validation.txt \
	console-keymap-verify console-unicode-mode gemini-keyboard-console-map-initramfs.img \
	gemini-keyboard-console-map.boot.img gemini-us.bkeymap initramfs-build.txt \
	initramfs-validation.txt input-event-capture input-tree.sha256 keymap-test.txt \
	keymap-validation.txt keymap-verifier-test.txt lk-analysis.txt \
	mt6797-gemini-pda-keyboard-console-map.dtb \
	provenance.txt source-build.json z-baseline-validation.txt)"
actual_inventory="$(find "$staging" -mindepth 1 -maxdepth 1 -type f -printf '%f\n' | sort)"
unexpected="$(find "$staging" -mindepth 1 ! -type f -print -quit)"
[[ -z "$unexpected" && "$actual_inventory" == "$expected_inventory" ]] || \
	die 'Candidate AA output inventory is not exact'
(
	cd "$staging"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$staging/SHA256SUMS"
(cd "$staging" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate AA output manifest failed'
chmod 0600 "$staging"/*
chmod 0755 "$staging/input-event-capture" "$staging/console-unicode-mode" \
	"$staging/console-keymap-verify"

output_name="candidate-AA-keyboard-console-map-final-${aa_boot_sha256:0:8}"
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv --no-clobber --no-target-directory -- "$staging" "$output"
[[ -d "$output" && ! -L "$output" && ! -e "$staging" ]] || \
	die 'atomic Candidate AA output handoff failed'
staging=
trap - EXIT
(cd "$output" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate AA output manifest failed after handoff'
python3 "$final_validator" --artifact "$output" --baseline "$baseline" \
	--defkeymap "$defkeymap" >/dev/null || \
	die 'Candidate AA final artifact failed post-handoff validation'

printf 'validation=candidate-aa-keyboard-console-map\n'
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-keyboard-console-map.boot.img\n' "$output"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$aa_boot_sha256" "$aa_boot_size"
printf 'candidate_initramfs_sha256=%s\n' "$aa_initramfs_sha256"
printf 'kernel_dtb_config=byte-exact-candidate-z\n'
printf 'keymap_sha256=%s\n' "$KEYMAP_SHA256"
printf 'keymap_verifier_sha256=%s\n' "$keymap_verifier_sha256"
printf 'watchdog_recovery=byte-exact-candidate-z\n'
printf 'hardware_write=none\nflash=none\nruntime_result=not-tested\n'
