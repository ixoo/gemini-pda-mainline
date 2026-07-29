#!/usr/bin/env bash

# Assemble storage-inert Candidate Orion from a validated kernel package and
# the exact Hubble serviceability base. This script never accesses a device.
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
export SOURCE_DATE_EPOCH=0
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package DIR --cassini-package DIR --hubble-artifact DIR --output-parent DIR\n' \
		"$0" >&2
}
package=
cassini_package=
hubble_artifact=
output_parent=
while (($#)); do
	case "$1" in
	--package|--cassini-package|--hubble-artifact|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--cassini-package) cassini_package=$2 ;;
		--hubble-artifact) hubble_artifact=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$package" && -n "$cassini_package" && -n "$hubble_artifact" && -n "$output_parent" ]] ||
	{ usage; exit 2; }
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] ||
	die 'run in the Linux AArch64 recovery VM'
for directory in "$package" "$cassini_package" "$hubble_artifact" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] ||
		die "unsafe or missing directory: $directory"
done
for command in awk bash chmod cmp cut dd find grep install mkdir mktemp mv \
	python3 rm rmdir sed sha256sum sort tr wc xargs; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
cassini_package="$(cd -- "$cassini_package" && pwd -P)"
hubble_artifact="$(cd -- "$hubble_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$package"|"$package"/*|\
"$cassini_package"|"$cassini_package"/*|\
"$hubble_artifact"|"$hubble_artifact"/*)
	die 'output parent must be outside the repository and selected inputs' ;;
esac

value() {
	PYTHONPATH="$script_dir" python3 -c \
		'import candidate_orion as c,sys; print(getattr(c,sys.argv[1]))' "$1"
}
HUBBLE_NAME="$(value HUBBLE_ARTIFACT_DIR)"
HUBBLE_DTB="$(value HUBBLE_DTB_MEMBER)"
HUBBLE_INITRAMFS="$(value HUBBLE_INITRAMFS_MEMBER)"
BOOT_MEMBER="$(value BOOT_MEMBER)"
DTB_MEMBER="$(value DTB_MEMBER)"
INITRAMFS_MEMBER="$(value INITRAMFS_MEMBER)"
PADDED_MEMBER="$(value PADDED_MEMBER)"
readonly HUBBLE_NAME HUBBLE_DTB HUBBLE_INITRAMFS
readonly BOOT_MEMBER DTB_MEMBER INITRAMFS_MEMBER PADDED_MEMBER

package_validator="$script_dir/validate-package-orion.py"
dtb_builder="$script_dir/build-orion-dtb.sh"
dtb_validator="$script_dir/validate-orion-dtb.py"
dtb_lineage_validator="$script_dir/validate-orion-dtb-lineage.py"
hubble_validator="$repo_root/experiments/2026-07-27-da9214-transient-probe-hubble/scripts/validate-hubble-artifact.py"
hubble_pins="$repo_root/experiments/2026-07-27-da9214-transient-probe-hubble/scripts/candidate_hubble.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
normalizer="$repo_root/experiments/2026-07-24-mt6797-dvfsp-i2c6-consumer/scripts/normalize-build-json.py"
standard_validator="$repo_root/scripts/validate-kernel-artifact"
for input in "$package_validator" "$dtb_builder" "$dtb_validator" \
	"$dtb_lineage_validator" \
	"$hubble_validator" "$hubble_pins" "$serializer" "$analyzer" \
	"$normalizer" "$standard_validator"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "repository input missing or unsafe: $input"
done
[[ "$(sha256sum "$hubble_validator" | awk '{print $1}')" == \
	"$(value HUBBLE_VALIDATOR_SHA256)" ]] ||
	die 'Hubble artifact validator changed'
[[ "$(sha256sum "$hubble_pins" | awk '{print $1}')" == \
	"$(value HUBBLE_PINS_SHA256)" ]] || die 'Hubble pins changed'
[[ "$(sha256sum "$serializer" | awk '{print $1}')" == \
	"$(value SERIALIZER_SHA256)" ]] || die 'Android-v0 serializer changed'
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == \
	"$(value ANALYZER_SHA256)" ]] || die 'LK analyzer changed'
[[ "$(sha256sum "$normalizer" | awk '{print $1}')" == \
	"$(value NORMALIZER_SHA256)" ]] || die 'provenance normalizer changed'
[[ "$(sha256sum "$dtb_lineage_validator" | awk '{print $1}')" == \
	"$(value DTB_LINEAGE_VALIDATOR_SHA256)" ]] ||
	die 'Orion DT lineage validator changed'

[[ "$(basename -- "$hubble_artifact")" == "$HUBBLE_NAME" ]] ||
	die 'wrong Candidate Hubble artifact'
for member in SHA256SUMS "$HUBBLE_DTB" "$HUBBLE_INITRAMFS" \
	gemini-us.bkeymap console-unicode-mode console-keymap-verify \
	input-event-capture; do
	[[ -f "$hubble_artifact/$member" && ! -L "$hubble_artifact/$member" ]] ||
		die "Candidate Hubble member missing: $member"
done
[[ "$(sha256sum "$hubble_artifact/SHA256SUMS" | awk '{print $1}')" == \
	"$(value HUBBLE_MANIFEST_SHA256)" ]] ||
	die 'exact Candidate Hubble manifest changed'
[[ "$(sha256sum "$hubble_artifact/$HUBBLE_DTB" | awk '{print $1}')" == \
	"$(value HUBBLE_DTB_SHA256)" ]] || die 'exact Hubble DT changed'
[[ "$(sha256sum "$hubble_artifact/$HUBBLE_INITRAMFS" | awk '{print $1}')" == \
	"$(value HUBBLE_INITRAMFS_SHA256)" ]] ||
	die 'exact Hubble initramfs changed'

workdir="$(mktemp -d "$output_parent/.candidate-orion.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

"$standard_validator" "$package" >"$stage/standard-package-validation.raw"
[[ "$(grep -c '^generated_utc=' "$stage/standard-package-validation.raw")" == 1 ]] ||
	die 'standard package validator timestamp contract changed'
sed -e "s|$package|@PACKAGE@|g" -e "s|$repo_root|@REPOSITORY@|g" \
	"$stage/standard-package-validation.raw" \
	| grep -v '^generated_utc=' >"$stage/standard-package-validation.txt"
rm "$stage/standard-package-validation.raw"
python3 "$package_validator" --repository "$repo_root" --package "$package" \
	>"$stage/package-validation.txt"
python3 "$hubble_validator" --artifact "$hubble_artifact" \
	--expected-name hubble >"$stage/hubble-validation.raw"
sed -e "s|$hubble_artifact|@HUBBLE@|g" \
	"$stage/hubble-validation.raw" >"$stage/hubble-validation.txt"
rm "$stage/hubble-validation.raw"
compiled_dtb="$package/dtbs/mediatek/mt6797-gemini-pda.dtb"
[[ -f "$compiled_dtb" && ! -L "$compiled_dtb" && -s "$compiled_dtb" ]] ||
	die 'compiled Gemini DT is missing, empty, or unsafe'
install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
python3 "$normalizer" --input "$package/provenance/build.json" \
	--output "$stage/source-build.json"

bash "$dtb_builder" --hubble-dtb "$hubble_artifact/$HUBBLE_DTB" \
	--output "$stage/$DTB_MEMBER" >"$stage/dtb-validation.txt"
bash "$dtb_builder" --hubble-dtb "$hubble_artifact/$HUBBLE_DTB" \
	--output "$replica/$DTB_MEMBER" >/dev/null
cmp -s "$stage/$DTB_MEMBER" "$replica/$DTB_MEMBER" ||
	die 'independent Orion DT derivations differ'
PYTHONPATH="$script_dir" python3 "$dtb_lineage_validator" \
	--cassini-package "$cassini_package" --orion-package "$package" \
	--hubble-dtb "$hubble_artifact/$HUBBLE_DTB" \
	--derived-dtb "$stage/$DTB_MEMBER" \
	>"$stage/dtb-lineage-validation.txt"
install -m 0600 "$hubble_artifact/$HUBBLE_INITRAMFS" \
	"$stage/$INITRAMFS_MEMBER"
install -m 0600 "$hubble_artifact/$HUBBLE_INITRAMFS" \
	"$replica/$INITRAMFS_MEMBER"
cmp -s "$stage/$INITRAMFS_MEMBER" "$replica/$INITRAMFS_MEMBER" ||
	die 'retained Hubble initramfs changed'

install -m 0600 "$hubble_artifact/gemini-us.bkeymap" \
	"$stage/gemini-us.bkeymap"
install -m 0755 "$hubble_artifact/console-unicode-mode" \
	"$stage/console-unicode-mode"
install -m 0755 "$hubble_artifact/console-keymap-verify" \
	"$stage/console-keymap-verify"
install -m 0755 "$hubble_artifact/input-event-capture" \
	"$stage/input-event-capture"

boot_cmdline=bootopt=64S3,32N2,64N2
for output in "$stage/$BOOT_MEMBER" "$replica/$BOOT_MEMBER"; do
	python3 "$serializer" --kernel "$stage/Image.gz" \
		--ramdisk "$stage/$INITRAMFS_MEMBER" --dtb "$stage/$DTB_MEMBER" \
		--output "$output" --name gemini-orion \
		--cmdline "$boot_cmdline" --kernel-addr 0x40200000 \
		--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
		--tags-addr 0x44000000 --lk-android8 >"${output}.serializer"
done
cmp -s "$stage/$BOOT_MEMBER" "$replica/$BOOT_MEMBER" ||
	die 'independent Orion Android-v0 assemblies differ'
grep -v '^output=' "$stage/$BOOT_MEMBER.serializer" >"$stage/serializer.txt"
rm "$stage/$BOOT_MEMBER.serializer" "$replica/$BOOT_MEMBER.serializer"
python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/$INITRAMFS_MEMBER" \
	--expected-dtb "$stage/$DTB_MEMBER" --expected-name gemini-orion \
	--expected-cmdline "$boot_cmdline" "$stage/$BOOT_MEMBER" \
	>"$stage/analysis.raw"
sed -e "s|$workdir|@WORK@|g" -e "s|$repo_root|@REPOSITORY@|g" \
	"$stage/analysis.raw" >"$stage/analysis.txt"
rm "$stage/analysis.raw"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] ||
	die 'LK analyzer did not emit exactly 32 gates'

raw_sha256="$(sha256sum "$stage/$BOOT_MEMBER" | awk '{print $1}')"
raw_size="$(wc -c <"$stage/$BOOT_MEMBER" | tr -d ' ')"
((raw_size > 0 && raw_size <= 16 * 1024 * 1024)) ||
	die 'Orion image does not fit boot2'
padded="$workdir/$PADDED_MEMBER"
dd if=/dev/zero of="$padded" bs=16M count=1 status=none
dd if="$stage/$BOOT_MEMBER" of="$padded" bs=4M conv=notrunc,fsync status=none
padded_sha256="$(sha256sum "$padded" | awk '{print $1}')"
install -m 0600 "$padded" "$stage/$PADDED_MEMBER"

cat >"$stage/provenance.txt" <<EOF
experiment=$(value EXPERIMENT)
candidate=Orion
kernel_profile=$(value PROFILE)
patch_series=$(value SERIES)
boot_container=canonical-android-v0-lk-android8
candidate_raw_sha256=$raw_sha256
candidate_raw_size=$raw_size
candidate_padded_boot2_sha256=$padded_sha256
hubble_raw_sha256=$(value HUBBLE_RAW_SHA256)
hubble_padded_sha256=$(value HUBBLE_PADDED_SHA256)
compiled_package_dtb_sha256=$(sha256sum "$compiled_dtb" | awk '{print $1}')
final_dtb_sha256=$(sha256sum "$stage/$DTB_MEMBER" | awk '{print $1}')
cassini_normalized_provenance_sha256=$(value CASSINI_PROVENANCE_SHA256)
cassini_compiled_dtb_sha256=$(value CASSINI_COMPILED_DTB_SHA256)
compiled_dtb_delta=exact-cassini-compiled-plus-only-i2c6-compatible
boot_dtb_delta=exact-hubble-plus-only-i2c6-compatible
cross_lineage_i2c6_resource_contract=exact
initramfs_sha256=$(sha256sum "$stage/$INITRAMFS_MEMBER" | awk '{print $1}')
adapter=/i2c@1100e000
i2c6=enabled-childless-standalone-idvfs-compatible
diagnostic=fixed-root-only-one-shot
mode_order=packed-fifo,packed-dma,aux-dma
adapter_retries=temporarily-zero-and-restored
i2c6_apdma_fifo_channel=must-remain-unstarted
shared_ap_dma_clock=available-not-a-runtime-gate
i2c_chardev=absent
da9214_provider=absent
cpu8_cpu9=fail-closed-unrequested
storage_access=none
hardware_write=none
runtime_result=not-tested
EOF

expected="$(printf '%s\n' Image.gz System.map analysis.txt "$PADDED_MEMBER" \
	console-keymap-verify console-unicode-mode dtb-lineage-validation.txt \
	dtb-validation.txt \
	gemini-us.bkeymap hubble-validation.txt input-event-capture \
	kernel.config package-validation.txt provenance.txt serializer.txt \
	source-build.json standard-package-validation.txt "$BOOT_MEMBER" \
	"$DTB_MEMBER" "$INITRAMFS_MEMBER" | sort)"
actual="$(find "$stage" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)"
[[ "$actual" == "$expected" ]] || die 'Orion output inventory changed'
(cd "$stage" && find . -type f ! -name SHA256SUMS -print0 |
	sort -z | xargs -0 sha256sum) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'Orion artifact manifest failed'
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" \
	"$stage/console-unicode-mode" "$stage/input-event-capture"

short_sha="$(printf '%s' "$raw_sha256" | cut -c1-8)"
artifact="$workdir/$(value ARTIFACT_PREFIX)$short_sha"
mv -n "$stage" "$artifact"
stage=
output="$output_parent/$(basename "$artifact")"
[[ ! -e "$output" && ! -L "$output" ]] ||
	die "refusing to overwrite $output"
mv -n "$artifact" "$output"
rm -f -- "$padded"
rm -rf -- "$replica"
rmdir "$workdir"
workdir=
trap - EXIT

printf 'validation=candidate-orion-assembled\n'
printf 'artifact=%s\nraw_sha256=%s\nraw_size=%s\n' \
	"$output" "$raw_sha256" "$raw_size"
printf 'padded_boot2_sha256=%s\n' "$padded_sha256"
printf 'device_access=none\nruntime_result=not-tested\n'
