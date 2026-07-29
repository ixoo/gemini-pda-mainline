#!/usr/bin/env bash

set -euo pipefail

die() {
	echo "error: $*" >&2
	exit 1
}

usage() {
	echo "Usage: $0 --package DIR --gauss-artifact DIR --output-parent DIR"
}

package=
gauss_artifact=
output_parent=
while [[ "$#" -gt 0 ]]; do
	case "$1" in
	--package) package="${2:-}"; shift 2 ;;
	--gauss-artifact) gauss_artifact="${2:-}"; shift 2 ;;
	--output-parent) output_parent="${2:-}"; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$package" && -n "$gauss_artifact" && -n "$output_parent" ]] || {
	usage >&2
	exit 2
}
for command in awk cmp find grep install mkdir mktemp mv python3 rm sha256sum \
	sort tr truncate wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
gauss_artifact="$(cd -- "$gauss_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$package"|"$package"/*|"$gauss_artifact"|"$gauss_artifact"/*)
	die "output parent must be outside the repository and both inputs"
	;;
esac

readonly GAUSS_DTB=mt6797-gemini-pda-da9214-gauss.dtb
readonly GAUSS_INITRAMFS=gemini-da9214-cassini-initramfs.img
readonly LIFE_DTB=mt6797-gemini-pda-da921x-lifecycle.dtb
readonly LIFE_INITRAMFS=gemini-da921x-lifecycle-initramfs.img
readonly LIFE_BOOT=gemini-mt6797-da921x-lifecycle.boot.img
readonly COMPILED_DTB=dtbs/mediatek/mt6797-gemini-pda.dtb
readonly BOOT2_SIZE=16777216
readonly GAUSS_INITRAMFS_SHA256=e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f

serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
dtb_builder="$script_dir/build-lifecycle-dtb.sh"
static_validator="$script_dir/validate-static.py"
for input in "$serializer" "$analyzer" "$dtb_builder" "$static_validator"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "missing, empty, or unsafe repository input: $input"
done
for input in "$package/Image.gz" "$package/System.map" "$package/kernel.config" \
	"$package/provenance/build.json" "$package/$COMPILED_DTB" \
	"$gauss_artifact/$GAUSS_DTB" "$gauss_artifact/$GAUSS_INITRAMFS"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "missing, empty, or unsafe artifact input: $input"
done
[[ "$(sha256sum "$gauss_artifact/$GAUSS_INITRAMFS" | awk '{print $1}')" == \
	"$GAUSS_INITRAMFS_SHA256" ]] || die "serviceability initramfs changed"
grep -qx 'CONFIG_I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE=y' "$package/kernel.config" ||
	die "lifecycle oracle is not built in"
grep -qx 'CONFIG_REGULATOR_DA9213_LEGACY=y' "$package/kernel.config" ||
	die "legacy identification driver is not built in"
grep -qx '# CONFIG_MTK_MT6797_A72_POWER is not set' "$package/kernel.config" ||
	die "A72 power driver unexpectedly enabled"
grep -q 'maxcpus=8' "$package/kernel.config" || die "maxcpus=8 missing"

workdir="$(mktemp -d "$output_parent/.gate3-lifecycle.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

"$repo_root/scripts/validate-kernel-artifact" "$package" >"$stage/package-validation.txt"
"$static_validator" >"$stage/static-validation.txt"
install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
install -m 0600 "$package/provenance/build.json" "$stage/source-build.json"
install -m 0600 "$gauss_artifact/$GAUSS_INITRAMFS" "$stage/$LIFE_INITRAMFS"
for tool in gemini-us.bkeymap console-keymap-verify console-unicode-mode input-event-capture; do
	mode=0600
	[[ -x "$gauss_artifact/$tool" ]] && mode=0755
	install -m "$mode" "$gauss_artifact/$tool" "$stage/$tool"
done

for destination in "$stage/$LIFE_DTB" "$replica/$LIFE_DTB"; do
	"$dtb_builder" --gauss-dtb "$gauss_artifact/$GAUSS_DTB" \
		--compiled-dtb "$package/$COMPILED_DTB" --output "$destination" \
		>"${destination}.validation"
done
cmp -s "$stage/$LIFE_DTB" "$replica/$LIFE_DTB" ||
	die "two lifecycle DT derivations differ"
mv "$stage/$LIFE_DTB.validation" "$stage/dtb-validation.txt"
rm "$replica/$LIFE_DTB.validation"

boot_cmdline=bootopt=64S3,32N2,64N2
for destination in "$stage/$LIFE_BOOT" "$replica/$LIFE_BOOT"; do
	python3 "$serializer" --kernel "$stage/Image.gz" \
		--ramdisk "$stage/$LIFE_INITRAMFS" --dtb "$stage/$LIFE_DTB" \
		--output "$destination" --name gemini-life --cmdline "$boot_cmdline" \
		--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
		--second-addr 0x40f00000 --tags-addr 0x44000000 \
		--lk-android8 >"${destination}.serializer"
done
cmp -s "$stage/$LIFE_BOOT" "$replica/$LIFE_BOOT" ||
	die "two lifecycle boot-container assemblies differ"
grep -v '^output=' "$stage/$LIFE_BOOT.serializer" >"$stage/serializer.txt"
rm "$stage/$LIFE_BOOT.serializer" "$replica/$LIFE_BOOT.serializer"

python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/$LIFE_INITRAMFS" \
	--expected-dtb "$stage/$LIFE_DTB" --expected-name gemini-life \
	--expected-cmdline "$boot_cmdline" "$stage/$LIFE_BOOT" >"$stage/analysis.txt"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] ||
	die "LK analyzer did not emit exactly 32 gates"

candidate_size="$(wc -c <"$stage/$LIFE_BOOT" | tr -d ' ')"
(( candidate_size <= BOOT2_SIZE )) || die "candidate exceeds boot2"
install -m 0600 "$stage/$LIFE_BOOT" "$stage/boot2-padded.img"
truncate -s "$BOOT2_SIZE" "$stage/boot2-padded.img"
candidate_sha256="$(sha256sum "$stage/$LIFE_BOOT" | awk '{print $1}')"
padded_sha256="$(sha256sum "$stage/boot2-padded.img" | awk '{print $1}')"
dtb_sha256="$(sha256sum "$stage/$LIFE_DTB" | awk '{print $1}')"
{
	printf 'experiment=2026-07-29-da921x-legacy-lifecycle\n'
	printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$candidate_sha256" "$candidate_size"
	printf 'padded_sha256=%s\npadded_size=%s\n' "$padded_sha256" "$BOOT2_SIZE"
	printf 'dtb_sha256=%s\n' "$dtb_sha256"
	printf 'initramfs_sha256=%s\n' "$GAUSS_INITRAMFS_SHA256"
	printf 'serviceability_baseline=exact-candidate-Gauss-initramfs-and-boot-DT\n'
	printf 'kernel_profile=da921x-legacy-lifecycle\n'
	printf 'maxcpus=8\nregulator_provider=absent\na72_consumer=absent\n'
	printf 'device_access=none\nflash=none\nruntime_result=not-tested\n'
	} >"$stage/provenance.txt"

(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die "candidate manifest failed"
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" "$stage/console-unicode-mode" \
	"$stage/input-event-capture"

output_name="candidate-Gate3-da921x-lifecycle-${candidate_sha256:0:8}"
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
printf 'validation=gate3-lifecycle-candidate\n'
printf 'artifact=%s\ncandidate=%s/%s\n' "$output" "$output" "$LIFE_BOOT"
printf 'candidate_sha256=%s\npadded_sha256=%s\n' "$candidate_sha256" "$padded_sha256"
printf 'dtb_sha256=%s\nruntime_result=not-tested\n' "$dtb_sha256"
