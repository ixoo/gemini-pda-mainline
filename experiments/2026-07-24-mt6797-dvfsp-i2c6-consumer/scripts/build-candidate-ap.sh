#!/usr/bin/env bash

# Assemble storage-inert Candidate AP from an exact validated AP kernel package
# and the exact hardware-passed Candidate AO DT/initramfs baseline. This script
# never accesses a device and never selects or writes a partition.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package AP_PACKAGE --ao-artifact AO_ARTIFACT --output-parent DIR\n' "$0" >&2
}

package=
ao_artifact=
output_parent=
while (($#)); do
	case "$1" in
	--package|--ao-artifact|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--ao-artifact) ao_artifact=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die 'run in the Linux recovery VM'
case "$(uname -m)" in aarch64|arm64) ;; *) die 'expected Linux AArch64' ;; esac
for directory in "$package" "$ao_artifact" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] || \
		die "unsafe or missing directory: $directory"
done
for command in awk basename chmod cmp find grep install mkdir mktemp mv \
	python3 rm rmdir sed sha256sum sort tr uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || \
		die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
ao_artifact="$(cd -- "$ao_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$package"|"$package"/*|\
"$ao_artifact"|"$ao_artifact"/*)
	die 'output parent must be outside the repository and selected inputs'
	;;
esac

candidate_module="$script_dir/candidate_ap.py"
[[ -f "$candidate_module" && ! -L "$candidate_module" &&
	-s "$candidate_module" ]] || die 'Candidate AP identity module is unsafe'
candidate_value() {
	PYTHONPATH="$script_dir" python3 -c \
		'import candidate_ap as ap, sys; print(getattr(ap, sys.argv[1]))' "$1"
}

readonly PROFILE="$(candidate_value PROFILE)"
readonly PM_AUDIT_PROFILE="$(candidate_value PM_AUDIT_PROFILE)"
readonly EXPERIMENT="$(candidate_value EXPERIMENT)"
readonly CANDIDATE_LABEL="$(candidate_value CANDIDATE)"
readonly AO_NAME="$(candidate_value AO_ARTIFACT_DIR)"
readonly AO_MANIFEST_SHA256="$(candidate_value AO_MANIFEST_SHA256)"
readonly AO_DTB_SHA256="$(candidate_value AO_DTB_SHA256)"
readonly AO_INITRAMFS_SHA256="$(candidate_value INITRAMFS_SHA256)"
readonly AO_KEYMAP_SHA256="$(candidate_value KEYMAP_SHA256)"
readonly AO_DTB="$(candidate_value AO_DTB_MEMBER)"
readonly AO_INITRAMFS="$(candidate_value AO_INITRAMFS_MEMBER)"
readonly AP_DTB="$(candidate_value DTB_MEMBER)"
readonly AP_INITRAMFS="$(candidate_value INITRAMFS_MEMBER)"
readonly AP_BOOT="$(candidate_value BOOT_MEMBER)"
readonly ARTIFACT_PREFIX="$(candidate_value ARTIFACT_PREFIX)"

if grep -Fq "\"build_profile\": \"$PM_AUDIT_PROFILE\"" \
	"$package/provenance/build.json"; then
	die 'PM-audit package is compile/link evidence only and must never be assembled'
fi

manifest="$repo_root/kernel/manifest.json"
package_validator="$script_dir/validate-package.py"
dtb_builder="$script_dir/build-ap-dtb.sh"
dtb_validator="$script_dir/validate-dtb-delta.py"
boot_validator="$script_dir/validate-boot.py"
handoff_auditor="$script_dir/audit-compiled-handoff.py"
normalizer="$script_dir/normalize-build-json.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
patch_0094="$repo_root/patches/v7.1.3/0094-dt-bindings-soc-mediatek-add-MT6797-DVFSP-handoff-observer.patch"
patch_0095="$repo_root/patches/v7.1.3/0095-soc-mediatek-add-MT6797-DVFSP-handoff-observer.patch"
patch_0097="$repo_root/patches/v7.1.3/0097-dt-bindings-soc-mediatek-add-MT6797-DVFSP-handoff-owner.patch"
patch_0098="$repo_root/patches/v7.1.3/0098-soc-mediatek-add-MT6797-DVFSP-one-way-handoff.patch"
patch_0099="$repo_root/patches/v7.1.3/0099-dt-bindings-mediatek-gate-MT6797-I2C-with-DVFSP-handoff.patch"
patch_0100="$repo_root/patches/v7.1.3/0100-soc-mediatek-require-ready-MT6797-DVFSP-handoff-supplier.patch"
patch_0101="$repo_root/patches/v7.1.3/0101-i2c-mediatek-require-MT6797-DVFSP-handoff.patch"
patch_0102="$repo_root/patches/v7.1.3/0102-arm64-dts-mediatek-enable-childless-Gemini-I2C6-after-handoff.patch"
for input in "$manifest" "$package_validator" "$dtb_builder" "$dtb_validator" \
	"$boot_validator" "$handoff_auditor" "$normalizer" "$serializer" \
		"$analyzer" "$patch_0094" "$patch_0095" "$patch_0097" "$patch_0098" \
		"$patch_0099" "$patch_0100" "$patch_0101" "$patch_0102"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || \
		die "repository input missing or unsafe: $input"
done

require_source_hash() {
	local path=$1
	local expected=$2
	local label=$3
	[[ "$expected" =~ ^[0-9a-f]{64}$ ]] || \
		die "source-pinned $label hash is malformed"
	[[ "$(sha256sum "$path" | awk '{ print $1 }')" == "$expected" ]] || \
		die "source-pinned $label changed"
}
require_source_hash "$serializer" "$(candidate_value SERIALIZER_SHA256)" \
	'Android-v0 serializer'
require_source_hash "$analyzer" "$(candidate_value ANALYZER_SHA256)" \
	'LK analyzer'
require_source_hash "$handoff_auditor" \
	"$(candidate_value COMPILED_HANDOFF_AUDITOR_SHA256)" \
	'compiled handoff auditor'
require_source_hash "$patch_0094" "$(candidate_value PATCH_0094_SHA256)" \
	'patch 0094'
require_source_hash "$patch_0095" "$(candidate_value PATCH_0095_SHA256)" \
	'patch 0095'
require_source_hash "$patch_0097" "$(candidate_value PATCH_0097_SHA256)" \
	'patch 0097'
require_source_hash "$patch_0098" "$(candidate_value PATCH_0098_SHA256)" \
	'patch 0098'
require_source_hash "$patch_0099" "$(candidate_value PATCH_0099_SHA256)" \
	'patch 0099'
require_source_hash "$patch_0100" "$(candidate_value PATCH_0100_SHA256)" \
	'patch 0100'
require_source_hash "$patch_0101" "$(candidate_value PATCH_0101_SHA256)" \
	'patch 0101'
require_source_hash "$patch_0102" "$(candidate_value PATCH_0102_SHA256)" \
	'patch 0102'

[[ "$(basename -- "$ao_artifact")" == "$AO_NAME" ]] || \
	die 'exact Candidate AO artifact basename changed'
for member in SHA256SUMS "$AO_DTB" "$AO_INITRAMFS" gemini-us.bkeymap \
	console-unicode-mode console-keymap-verify input-event-capture; do
	[[ -f "$ao_artifact/$member" && ! -L "$ao_artifact/$member" ]] || \
		die "Candidate AO member missing or unsafe: $member"
done
[[ "$(sha256sum "$ao_artifact/SHA256SUMS" | awk '{ print $1 }')" == \
	"$AO_MANIFEST_SHA256" ]] || die 'exact Candidate AO manifest changed'
(cd "$ao_artifact" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate AO manifest failed'
[[ "$(sha256sum "$ao_artifact/$AO_DTB" | awk '{ print $1 }')" == \
	"$AO_DTB_SHA256" ]] || die 'exact Candidate AO final DT changed'
[[ "$(sha256sum "$ao_artifact/$AO_INITRAMFS" | awk '{ print $1 }')" == \
	"$AO_INITRAMFS_SHA256" ]] || die 'exact Candidate AO initramfs changed'
[[ "$(sha256sum "$ao_artifact/gemini-us.bkeymap" | awk '{ print $1 }')" == \
	"$AO_KEYMAP_SHA256" ]] || die 'exact Candidate AO keymap changed'

workdir="$(mktemp -d "$output_parent/.candidate-AP-i2c6-consumer.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

python3 "$package_validator" --repository "$repo_root" --package "$package" \
	>"$stage/package-validation.raw"
sed -e "s|$repo_root|@REPOSITORY@|g" -e "s|$workdir|@WORK@|g" \
	-e "s|$package|@AP_PACKAGE@|g" \
	-e 's/^calibration_package_manifest_sha256=.*/calibration_package_manifest_sha256=validated-build-specific-generation-manifest/' \
	"$stage/package-validation.raw" >"$stage/package-validation.txt"
rm "$stage/package-validation.raw"

install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
python3 "$normalizer" --input "$package/provenance/build.json" \
	--output "$stage/source-build.json"
install -m 0600 "$ao_artifact/$AO_INITRAMFS" "$stage/$AP_INITRAMFS"
install -m 0600 "$ao_artifact/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$ao_artifact/console-unicode-mode" "$stage/console-unicode-mode"
install -m 0755 "$ao_artifact/console-keymap-verify" \
	"$stage/console-keymap-verify"
install -m 0755 "$ao_artifact/input-event-capture" \
	"$stage/input-event-capture"

bash "$dtb_builder" --ao-dtb "$ao_artifact/$AO_DTB" \
	--output "$stage/$AP_DTB" >"$stage/dtb-validation.raw"
bash "$dtb_builder" --ao-dtb "$ao_artifact/$AO_DTB" \
	--output "$replica/$AP_DTB" >/dev/null
cmp -s "$stage/$AP_DTB" "$replica/$AP_DTB" || \
	die 'two independent Candidate AP final-DT derivations differ'
sed -e "s|$stage/$AP_DTB|@AP_DTB@|g" \
	"$stage/dtb-validation.raw" >"$stage/dtb-validation.txt"
rm "$stage/dtb-validation.raw"

candidate="$stage/$AP_BOOT"
replica_boot="$replica/$AP_BOOT"
boot_cmdline=bootopt=64S3,32N2,64N2
for output in "$candidate" "$replica_boot"; do
	python3 "$serializer" --kernel "$stage/Image.gz" \
		--ramdisk "$stage/$AP_INITRAMFS" --dtb "$stage/$AP_DTB" \
		--output "$output" --name gemini-obs-L --cmdline "$boot_cmdline" \
		--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
		--second-addr 0x40f00000 --tags-addr 0x44000000 \
		--lk-android8 >"${output}.serializer"
done
cmp -s "$candidate" "$replica_boot" || \
	die 'two independent Candidate AP container assemblies differ'
grep -v '^output=' "${candidate}.serializer" >"$stage/serializer.txt"
rm "${candidate}.serializer" "${replica_boot}.serializer"

python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/$AP_INITRAMFS" \
	--expected-dtb "$stage/$AP_DTB" --expected-name gemini-obs-L \
	--expected-cmdline "$boot_cmdline" "$candidate" >"$stage/analysis.raw"
sed -e "s|$workdir|@WORK@|g" -e "s|$repo_root|@REPOSITORY@|g" \
	"$stage/analysis.raw" >"$stage/analysis.txt"
rm "$stage/analysis.raw"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] || \
	die 'LK analyzer did not emit exactly 32 gates'

python3 "$boot_validator" --candidate "$candidate" \
	--image-gz "$stage/Image.gz" --system-map "$stage/System.map" \
	--kernel-config "$stage/kernel.config" --dtb "$stage/$AP_DTB" \
	--ao-dtb "$ao_artifact/$AO_DTB" --initramfs "$stage/$AP_INITRAMFS" \
	>"$stage/boot-validation.txt"

candidate_sha256="$(sha256sum "$candidate" | awk '{ print $1 }')"
candidate_size="$(wc -c <"$candidate" | tr -d ' ')"
image_sha256="$(sha256sum "$stage/Image.gz" | awk '{ print $1 }')"
system_map_sha256="$(sha256sum "$stage/System.map" | awk '{ print $1 }')"
dtb_sha256="$(sha256sum "$stage/$AP_DTB" | awk '{ print $1 }')"
config_sha256="$(sha256sum "$stage/kernel.config" | awk '{ print $1 }')"
source_build_sha256="$(sha256sum "$stage/source-build.json" | awk '{ print $1 }')"
auditor_sha256="$(sha256sum "$handoff_auditor" | awk '{ print $1 }')"
{
	printf 'experiment=%s\n' "$EXPERIMENT"
	printf 'candidate_label=%s\nkernel_profile=%s\n' \
		"$CANDIDATE_LABEL" "$PROFILE"
	printf 'candidate_sha256=%s\ncandidate_size=%s\n' \
		"$candidate_sha256" "$candidate_size"
	printf 'candidate_image_gz_sha256=%s\n' "$image_sha256"
	printf 'candidate_system_map_sha256=%s\n' "$system_map_sha256"
	printf 'candidate_dtb_sha256=%s\n' "$dtb_sha256"
	printf 'candidate_config_sha256=%s\n' "$config_sha256"
	printf 'candidate_source_build_sha256=%s\n' "$source_build_sha256"
	printf 'ao_raw_sha256=%s\n' "$(candidate_value AO_RAW_SHA256)"
	printf 'ao_dtb_sha256=%s\n' "$AO_DTB_SHA256"
	printf 'candidate_initramfs_sha256=%s\n' "$AO_INITRAMFS_SHA256"
	printf 'candidate_keymap_sha256=%s\n' "$AO_KEYMAP_SHA256"
	printf 'patch_0094_sha256=%s\n' "$(candidate_value PATCH_0094_SHA256)"
	printf 'patch_0095_sha256=%s\n' "$(candidate_value PATCH_0095_SHA256)"
	printf 'patch_0097_sha256=%s\n' "$(candidate_value PATCH_0097_SHA256)"
	printf 'patch_0098_sha256=%s\n' "$(candidate_value PATCH_0098_SHA256)"
	printf 'patch_0099_sha256=%s\n' "$(candidate_value PATCH_0099_SHA256)"
	printf 'patch_0100_sha256=%s\n' "$(candidate_value PATCH_0100_SHA256)"
	printf 'patch_0101_sha256=%s\n' "$(candidate_value PATCH_0101_SHA256)"
	printf 'patch_0102_sha256=%s\n' "$(candidate_value PATCH_0102_SHA256)"
	printf 'compiled_handoff_auditor_sha256=%s\n' "$auditor_sha256"
	printf 'functional_baseline=exact-hardware-passed-candidate-ao-contract\n'
	printf 'final_dtb_baseline=exact-candidate-ao-final-dtb\n'
	printf 'final_dtb_delta=access-controller-link-and-childless-i2c6-enable-only\n'
	printf 'initramfs_keyboard_console_usb_reboot=byte-exact-candidate-ao\n'
	printf 'handoff_initial_contract=exact-candidate-ao-ready-late-passed\n'
	printf 'handoff_access_controller=enabled\n'
	printf 'fw_devlink=rpm\n'
	printf 'i2c6=enabled-childless\ni2c6_clients=0\n'
	printf 'i2c6_transfer_start_irq=0\n'
	printf 'installed_suspend=disabled\n'
	printf 'pm_callbacks=separate-noninstalled-compile-audit\n'
	printf 'da9214_node=absent\nregulators=absent\na72_power_node=absent\n'
	printf 'maxcpus=8\na72_power_initcall=blacklisted\n'
	printf 'dvfsp_handoff_initcall=enabled\n'
	printf 'cpu8_cpu9_request=none\ncpu_operation=none\n'
	printf 'regulator_operation=none\nstorage_access=none\n'
	printf 'watchdog_userspace=none\nautomatic_reboot=none\n'
	printf 'artifact_builder_device_access=none\nflash=none\nruntime_result=not-tested\n'
} >"$stage/provenance.txt"

expected_pre_manifest="$(printf '%s\n' Image.gz System.map analysis.txt \
	boot-validation.txt console-keymap-verify console-unicode-mode \
	dtb-validation.txt "$AP_BOOT" "$AP_INITRAMFS" gemini-us.bkeymap \
	input-event-capture kernel.config "$AP_DTB" package-validation.txt \
	provenance.txt serializer.txt source-build.json | sort)"
actual_inventory="$(find "$stage" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)"
[[ "$actual_inventory" == "$expected_pre_manifest" ]] || \
	die 'Candidate AP output inventory changed'
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate AP artifact manifest failed'
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" "$stage/console-unicode-mode" \
	"$stage/input-event-capture"

output_name="${ARTIFACT_PREFIX}${candidate_sha256:0:8}"
artifact="$workdir/$output_name"
mv -n "$stage" "$artifact"
stage=
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || \
	die "refusing to overwrite $output"
mv -n "$artifact" "$output"
[[ -d "$output" && ! -e "$artifact" ]] || \
	die 'exclusive Candidate AP publication failed'
rm -rf -- "$replica"
rmdir "$workdir"
workdir=
trap - EXIT
printf 'validation=candidate-ap-mt6797-dvfsp-i2c6-consumer\n'
printf 'artifact=%s\ncandidate=%s/%s\n' "$output" "$output" "$AP_BOOT"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' \
	"$candidate_sha256" "$candidate_size"
printf 'dtb_sha256=%s\nruntime_result=not-tested\n' "$dtb_sha256"
