#!/usr/bin/env bash

set -euo pipefail

die() {
	echo "error: $*" >&2
	exit 1
}

usage() {
	echo "Usage: $0 --gate3-artifact DIR --output-parent DIR"
}

gate3_artifact=
output_parent=
while [[ "$#" -gt 0 ]]; do
	case "$1" in
	--gate3-artifact) gate3_artifact="${2:-}"; shift 2 ;;
	--output-parent) output_parent="${2:-}"; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$gate3_artifact" && -n "$output_parent" ]] || {
	usage >&2
	exit 2
}
for command in awk chmod cmp find grep install mkdir mktemp mv python3 rm \
	sha256sum sort truncate wc xargs; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
gate3_artifact="$(cd -- "$gate3_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$gate3_artifact"|"$gate3_artifact"/*)
	die "output parent must be outside the repository and input artifact"
	;;
esac

readonly GATE3_MANIFEST_SHA256=cd519406994e89f291ce7fba6bfa5bc37c517bfd8a10d1b1b888d7fe43ca03f6
readonly IMAGE_SHA256=7061a1f14a9d84b85424936b2ca75b0af14d9664b9c2f0714acc9f406501d995
readonly INITRAMFS_SHA256=e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f
readonly CONFIG_SHA256=fdbc40dfa2dbcf71012203005a3170d77bce0ff05d457fb9ffad30457993ec57
readonly GATE3_DTB=mt6797-gemini-pda-da921x-lifecycle.dtb
readonly GATE3_DTB_SHA256=7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806
readonly INITRAMFS=gemini-da921x-lifecycle-initramfs.img
readonly OUTPUT_DTB=mt6797-gemini-pda-da921x-probe-disabled.dtb
readonly OUTPUT_BOOT=gemini-mt6797-da921x-probe-disabled.boot.img
readonly BOOT2_SIZE=16777216
readonly SERIALIZER_SHA256=569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95

serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
dtb_builder="$script_dir/build-isolation-dtb.sh"
for input in "$serializer" "$analyzer" "$dtb_builder" \
	"$gate3_artifact/SHA256SUMS" "$gate3_artifact/Image.gz" \
	"$gate3_artifact/$INITRAMFS" "$gate3_artifact/kernel.config" \
	"$gate3_artifact/$GATE3_DTB"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "missing, empty, or unsafe input: $input"
done
[[ "$(sha256sum "$serializer" | awk '{print $1}')" == "$SERIALIZER_SHA256" ]] ||
	die "Android-v0 serializer changed"
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == "$ANALYZER_SHA256" ]] ||
	die "LK analyzer changed"
[[ "$(sha256sum "$gate3_artifact/SHA256SUMS" | awk '{print $1}')" == \
	"$GATE3_MANIFEST_SHA256" ]] || die "Gate 3 artifact manifest changed"
(cd "$gate3_artifact" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die "Gate 3 artifact manifest validation failed"
[[ "$(sha256sum "$gate3_artifact/Image.gz" | awk '{print $1}')" == "$IMAGE_SHA256" ]] ||
	die "Gate 3 Image.gz changed"
[[ "$(sha256sum "$gate3_artifact/$INITRAMFS" | awk '{print $1}')" == \
	"$INITRAMFS_SHA256" ]] || die "Gate 3 initramfs changed"
[[ "$(sha256sum "$gate3_artifact/kernel.config" | awk '{print $1}')" == \
	"$CONFIG_SHA256" ]] || die "Gate 3 configuration changed"
[[ "$(sha256sum "$gate3_artifact/$GATE3_DTB" | awk '{print $1}')" == \
	"$GATE3_DTB_SHA256" ]] || die "Gate 3 DT changed"

workdir="$(mktemp -d "$output_parent/.probe-isolation.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

for file in Image.gz "$INITRAMFS" kernel.config System.map source-build.json; do
	install -m 0600 "$gate3_artifact/$file" "$stage/$file"
done
for destination in "$stage/$OUTPUT_DTB" "$replica/$OUTPUT_DTB"; do
	"$dtb_builder" --gate3-dtb "$gate3_artifact/$GATE3_DTB" \
		--output "$destination" >"${destination}.validation"
done
cmp -s "$stage/$OUTPUT_DTB" "$replica/$OUTPUT_DTB" ||
	die "two DT derivations differ"
mv "$stage/$OUTPUT_DTB.validation" "$stage/dtb-validation.txt"
rm "$replica/$OUTPUT_DTB.validation"

boot_cmdline=bootopt=64S3,32N2,64N2
for destination in "$stage/$OUTPUT_BOOT" "$replica/$OUTPUT_BOOT"; do
	python3 "$serializer" --kernel "$stage/Image.gz" \
		--ramdisk "$stage/$INITRAMFS" --dtb "$stage/$OUTPUT_DTB" \
		--output "$destination" --name gemini-life --cmdline "$boot_cmdline" \
		--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
		--second-addr 0x40f00000 --tags-addr 0x44000000 \
		--lk-android8 >"${destination}.serializer"
done
cmp -s "$stage/$OUTPUT_BOOT" "$replica/$OUTPUT_BOOT" ||
	die "two boot-container assemblies differ"
grep -v '^output=' "$stage/$OUTPUT_BOOT.serializer" >"$stage/serializer.txt"
rm "$stage/$OUTPUT_BOOT.serializer" "$replica/$OUTPUT_BOOT.serializer"

python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/$INITRAMFS" --expected-dtb "$stage/$OUTPUT_DTB" \
	--expected-name gemini-life --expected-cmdline "$boot_cmdline" \
	"$stage/$OUTPUT_BOOT" >"$stage/analysis.txt"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] ||
	die "LK analyzer did not emit exactly 32 gates"

candidate_size="$(wc -c <"$stage/$OUTPUT_BOOT" | tr -d ' ')"
(( candidate_size <= BOOT2_SIZE )) || die "candidate exceeds boot2"
install -m 0600 "$stage/$OUTPUT_BOOT" "$stage/boot2-padded.img"
truncate -s "$BOOT2_SIZE" "$stage/boot2-padded.img"
candidate_sha256="$(sha256sum "$stage/$OUTPUT_BOOT" | awk '{print $1}')"
padded_sha256="$(sha256sum "$stage/boot2-padded.img" | awk '{print $1}')"
dtb_sha256="$(sha256sum "$stage/$OUTPUT_DTB" | awk '{print $1}')"
{
	printf 'experiment=2026-07-29-da921x-probe-isolation\n'
	printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$candidate_sha256" "$candidate_size"
	printf 'padded_sha256=%s\npadded_size=%s\n' "$padded_sha256" "$BOOT2_SIZE"
	printf 'dtb_sha256=%s\n' "$dtb_sha256"
	printf 'gate3_image_sha256=%s\n' "$IMAGE_SHA256"
	printf 'gate3_config_sha256=%s\n' "$CONFIG_SHA256"
	printf 'gate3_initramfs_sha256=%s\n' "$INITRAMFS_SHA256"
	printf 'gate3_dtb_sha256=%s\n' "$GATE3_DTB_SHA256"
	printf 'sole_semantic_delta=/i2c@1100e000/regulator@68-status-disabled\n'
	printf 'automatic_da921x_probe=prevented\n'
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

output_name="candidate-Gate3-probe-disabled-${candidate_sha256:0:8}"
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
printf 'validation=da921x-probe-isolation-candidate\n'
printf 'artifact=%s\ncandidate=%s/%s\n' "$output" "$output" "$OUTPUT_BOOT"
printf 'candidate_sha256=%s\npadded_sha256=%s\n' "$candidate_sha256" "$padded_sha256"
printf 'dtb_sha256=%s\nruntime_result=not-tested\n' "$dtb_sha256"
