#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	echo "usage: $0 --package DIR --module FILE --gate3-artifact DIR --output-parent DIR"
}

package=
module=
gate3_artifact=
output_parent=
while (($#)); do
	case "$1" in
	--package) package=${2:-}; shift 2 ;;
	--module) module=${2:-}; shift 2 ;;
	--gate3-artifact) gate3_artifact=${2:-}; shift 2 ;;
	--output-parent) output_parent=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage >&2; die "unknown argument: $1" ;;
	esac
done
[[ -n "$package" && -n "$module" && -n "$gate3_artifact" &&
	-n "$output_parent" ]] ||
	{ usage >&2; exit 2; }
for command in awk cmp grep install jq mkdir mktemp modinfo mv nm python3 rm \
	sha256sum sort truncate wc xargs; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
[[ -f "$module" && ! -L "$module" && -s "$module" ]] ||
	die "module is missing, empty, or unsafe"
module="$(cd -- "$(dirname -- "$module")" && pwd -P)/$(basename -- "$module")"
gate3_artifact="$(cd -- "$gate3_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$package"|"$package"/*|"$gate3_artifact"|"$gate3_artifact"/*)
	die "output parent must be outside the repository and inputs"
	;;
esac

readonly GATE3_MANIFEST_SHA256=cd519406994e89f291ce7fba6bfa5bc37c517bfd8a10d1b1b888d7fe43ca03f6
readonly GATE3_INITRAMFS=gemini-da921x-lifecycle-initramfs.img
readonly GATE3_INITRAMFS_SHA256=e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f
readonly GATE3_DTB=mt6797-gemini-pda-da921x-lifecycle.dtb
readonly GATE3_DTB_SHA256=7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806
readonly OUTPUT_INITRAMFS=gemini-da921x-post-serviceability-module-initramfs.img
readonly OUTPUT_BOOT=gemini-mt6797-da921x-post-serviceability-module.boot.img
readonly BOOT2_SIZE=16777216
readonly SERIALIZER_SHA256=569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95

serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
initramfs_builder="$script_dir/build-initramfs.sh"
for input in "$serializer" "$analyzer" "$initramfs_builder" \
	"$package/Image.gz" "$package/System.map" "$package/kernel.config" \
	"$package/provenance/build.json" "$gate3_artifact/SHA256SUMS" \
	"$gate3_artifact/$GATE3_INITRAMFS" "$gate3_artifact/$GATE3_DTB"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "input is missing, empty, or unsafe: $input"
done
[[ "$(sha256sum "$serializer" | awk '{print $1}')" == "$SERIALIZER_SHA256" ]] ||
	die "Android-v0 serializer changed"
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == "$ANALYZER_SHA256" ]] ||
	die "LK analyzer changed"
[[ "$(sha256sum "$gate3_artifact/SHA256SUMS" | awk '{print $1}')" == \
	"$GATE3_MANIFEST_SHA256" ]] || die "Gate 3 manifest changed"
(cd "$gate3_artifact" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die "Gate 3 artifact validation failed"
[[ "$(sha256sum "$gate3_artifact/$GATE3_INITRAMFS" | awk '{print $1}')" == \
	"$GATE3_INITRAMFS_SHA256" ]] || die "Gate 3 initramfs changed"
[[ "$(sha256sum "$gate3_artifact/$GATE3_DTB" | awk '{print $1}')" == \
	"$GATE3_DTB_SHA256" ]] || die "Gate 3 DT changed"
grep -qx 'CONFIG_MODULES=y' "$package/kernel.config" ||
	die "module support is not built in"
grep -qx 'CONFIG_REGULATOR_DA9213_LEGACY=m' "$package/kernel.config" ||
	die "DA921x driver is not a module"
grep -qx '# CONFIG_MTK_MT6797_A72_POWER is not set' "$package/kernel.config" ||
	die "A72 power driver unexpectedly enabled"
grep -q 'maxcpus=8' "$package/kernel.config" || die "maxcpus=8 missing"

[[ "$(modinfo -F name "$module")" == da9213_legacy_regulator ]] ||
	die "module identity changed"
release="$(modinfo -F vermagic "$module" | awk '{print $1}')"
[[ "$release" == 7.1.3-gemini-da921x-mod ]] ||
	die "module kernel release changed"
[[ "$(jq -er '.kernel_release' "$package/provenance/build.json")" == "$release" ]] ||
	die "module release does not match packaged kernel"
[[ "$(modinfo -F vermagic "$module")" == "$release "* ]] ||
	die "module vermagic is malformed"
[[ -z "$(modinfo -F depends "$module")" ]] ||
	die "module unexpectedly has loadable-module dependencies"
[[ "$(nm -u "$module" | awk '{print $2}' | sort -u | wc -l)" -gt 0 ]] ||
	die "module has no undefined kernel imports"

workdir="$(mktemp -d "$output_parent/.da921x-module-candidate.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

"$repo_root/scripts/validate-kernel-artifact" "$package" \
	>"$stage/package-validation.txt"
install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
install -m 0600 "$package/provenance/build.json" "$stage/source-build.json"
install -m 0600 "$module" "$stage/da9213-legacy-regulator.ko"
install -m 0600 "$gate3_artifact/$GATE3_DTB" "$stage/$GATE3_DTB"
for destination in "$stage/$OUTPUT_INITRAMFS" "$replica/$OUTPUT_INITRAMFS"; do
	"$initramfs_builder" "$gate3_artifact/$GATE3_INITRAMFS" "$module" \
		"$destination" >"${destination}.validation"
done
cmp -s "$stage/$OUTPUT_INITRAMFS" "$replica/$OUTPUT_INITRAMFS" ||
	die "two initramfs builds differ"
mv "$stage/$OUTPUT_INITRAMFS.validation" "$stage/initramfs-validation.txt"
rm "$replica/$OUTPUT_INITRAMFS.validation"

boot_cmdline=bootopt=64S3,32N2,64N2
for destination in "$stage/$OUTPUT_BOOT" "$replica/$OUTPUT_BOOT"; do
	python3 "$serializer" --kernel "$stage/Image.gz" \
		--ramdisk "$stage/$OUTPUT_INITRAMFS" \
		--dtb "$stage/$GATE3_DTB" --output "$destination" \
		--name gemini-mod --cmdline "$boot_cmdline" \
		--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
		--second-addr 0x40f00000 --tags-addr 0x44000000 \
		--lk-android8 >"${destination}.serializer"
done
cmp -s "$stage/$OUTPUT_BOOT" "$replica/$OUTPUT_BOOT" ||
	die "two boot-container assemblies differ"
grep -v '^output=' "$stage/$OUTPUT_BOOT.serializer" >"$stage/serializer.txt"
rm "$stage/$OUTPUT_BOOT.serializer" "$replica/$OUTPUT_BOOT.serializer"
python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/$OUTPUT_INITRAMFS" \
	--expected-dtb "$stage/$GATE3_DTB" --expected-name gemini-mod \
	--expected-cmdline "$boot_cmdline" "$stage/$OUTPUT_BOOT" \
	>"$stage/analysis.txt"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] ||
	die "LK analyzer did not emit exactly 32 gates"

candidate_size="$(wc -c <"$stage/$OUTPUT_BOOT" | tr -d ' ')"
(( candidate_size <= BOOT2_SIZE )) || die "candidate exceeds boot2"
install -m 0600 "$stage/$OUTPUT_BOOT" "$stage/boot2-padded.img"
truncate -s "$BOOT2_SIZE" "$stage/boot2-padded.img"
candidate_sha256="$(sha256sum "$stage/$OUTPUT_BOOT" | awk '{print $1}')"
padded_sha256="$(sha256sum "$stage/boot2-padded.img" | awk '{print $1}')"
initramfs_sha256="$(sha256sum "$stage/$OUTPUT_INITRAMFS" | awk '{print $1}')"
module_sha256="$(sha256sum "$module" | awk '{print $1}')"
{
	printf 'experiment=2026-07-29-da921x-post-serviceability-module\n'
	printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$candidate_sha256" "$candidate_size"
	printf 'padded_sha256=%s\npadded_size=%s\n' "$padded_sha256" "$BOOT2_SIZE"
	printf 'gate3_dtb_sha256=%s\n' "$GATE3_DTB_SHA256"
	printf 'gate3_initramfs_sha256=%s\n' "$GATE3_INITRAMFS_SHA256"
	printf 'module_sha256=%s\ninitramfs_sha256=%s\n' "$module_sha256" "$initramfs_sha256"
	printf 'kernel_profile=da921x-post-serviceability-module\n'
	printf 'automatic_module_load=absent\nmanual_module_load=post-serviceability-only\n'
	printf 'provider=absent\na72_request=absent\n'
	printf 'device_access=none\nflash=none\nruntime_result=not-tested\n'
} >"$stage/provenance.txt"
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die "candidate manifest failed"
chmod 0600 "$stage"/*

output_name="candidate-Gate3-da921x-module-${candidate_sha256:0:8}"
artifact="$workdir/$output_name"
mv -n "$stage" "$artifact"
stage=
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv -n "$artifact" "$output"
rm -rf -- "$replica"
rmdir "$workdir"
workdir=
trap - EXIT
printf 'validation=da921x-post-serviceability-module-candidate\n'
printf 'artifact=%s\ncandidate=%s/%s\n' "$output" "$output" "$OUTPUT_BOOT"
printf 'candidate_sha256=%s\npadded_sha256=%s\n' "$candidate_sha256" "$padded_sha256"
printf 'module_sha256=%s\nruntime_result=not-tested\n' "$module_sha256"
