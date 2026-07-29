#!/usr/bin/env bash

# Assemble storage-inert Candidate Cassini. This builder never accesses a
# device, selects a slot, or writes a partition.
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
export SOURCE_DATE_EPOCH=0
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package DIR --ao-artifact DIR --output-parent DIR\n' "$0" >&2
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
		shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$package" && -n "$ao_artifact" && -n "$output_parent" ]] ||
	{ usage; exit 2; }
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] ||
	die 'run in the Linux AArch64 recovery VM'
for directory in "$package" "$ao_artifact" "$output_parent"; do
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
ao_artifact="$(cd -- "$ao_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$package"|"$package"/*|\
"$ao_artifact"|"$ao_artifact"/*)
	die 'output parent must be outside the repository and selected inputs' ;;
esac

value() {
	PYTHONPATH="$script_dir" python3 -c \
		'import candidate_cassini as c,sys; print(getattr(c,sys.argv[1]))' "$1"
}
AO_NAME="$(value AO_ARTIFACT_DIR)"
AO_DTB="$(value AO_DTB_MEMBER)"
AO_INITRAMFS="$(value AO_INITRAMFS_MEMBER)"
BOOT_MEMBER="$(value BOOT_MEMBER)"
DTB_MEMBER="$(value DTB_MEMBER)"
INITRAMFS_MEMBER="$(value INITRAMFS_MEMBER)"
PROBE_MEMBER="$(value PROBE_MEMBER)"
readonly AO_NAME AO_DTB AO_INITRAMFS BOOT_MEMBER DTB_MEMBER INITRAMFS_MEMBER \
	PROBE_MEMBER

package_validator="$script_dir/validate-package-cassini.py"
probe_builder="$script_dir/build-cassini-probe.sh"
probe_validator="$script_dir/validate-cassini-probe.py"
initramfs_builder="$script_dir/build-cassini-initramfs.sh"
dtb_builder="$script_dir/build-cassini-dtb.sh"
source_file="$experiment_dir/initramfs/cassini-probe.c"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
normalizer="$repo_root/experiments/2026-07-24-mt6797-dvfsp-i2c6-consumer/scripts/normalize-build-json.py"
standard_validator="$repo_root/scripts/validate-kernel-artifact"
for input in "$package_validator" "$probe_builder" "$probe_validator" \
	"$initramfs_builder" "$dtb_builder" "$source_file" "$serializer" \
	"$analyzer" "$normalizer" "$standard_validator"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "repository input missing or unsafe: $input"
done
[[ "$(sha256sum "$serializer" | awk '{print $1}')" == \
	"$(value SERIALIZER_SHA256)" ]] || die 'Android-v0 serializer changed'
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == \
	"$(value ANALYZER_SHA256)" ]] || die 'LK analyzer changed'
[[ "$(sha256sum "$normalizer" | awk '{print $1}')" == \
	"$(value NORMALIZER_SHA256)" ]] || die 'provenance normalizer changed'

[[ "$(basename -- "$ao_artifact")" == "$AO_NAME" ]] ||
	die 'wrong Candidate AO artifact'
for member in SHA256SUMS "$AO_DTB" "$AO_INITRAMFS" gemini-us.bkeymap \
	console-unicode-mode console-keymap-verify input-event-capture; do
	[[ -f "$ao_artifact/$member" && ! -L "$ao_artifact/$member" ]] ||
		die "Candidate AO member missing: $member"
done
(cd "$ao_artifact" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'Candidate AO manifest failed'
[[ "$(sha256sum "$ao_artifact/SHA256SUMS" | awk '{print $1}')" == \
	"$(value AO_MANIFEST_SHA256)" ]] || die 'Candidate AO manifest changed'
[[ "$(sha256sum "$ao_artifact/$AO_DTB" | awk '{print $1}')" == \
	"$(value AO_DTB_SHA256)" ]] || die 'Candidate AO DT changed'
[[ "$(sha256sum "$ao_artifact/$AO_INITRAMFS" | awk '{print $1}')" == \
	"$(value AO_INITRAMFS_SHA256)" ]] || die 'Candidate AO initramfs changed'
[[ "$(sha256sum "$ao_artifact/gemini-us.bkeymap" | awk '{print $1}')" == \
	"$(value AO_KEYMAP_SHA256)" ]] || die 'Candidate AO keymap changed'

workdir="$(mktemp -d "$output_parent/.candidate-cassini.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

"$standard_validator" "$package" >"$stage/standard-package-validation.raw"
sed -e "s|$package|@PACKAGE@|g" -e "s|$repo_root|@REPOSITORY@|g" \
	"$stage/standard-package-validation.raw" \
	>"$stage/standard-package-validation.txt"
rm "$stage/standard-package-validation.raw"
python3 "$package_validator" --repository "$repo_root" --package "$package" \
	>"$stage/package-validation.txt"

install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
python3 "$normalizer" --input "$package/provenance/build.json" \
	--output "$stage/source-build.json"

bash "$probe_builder" "$source_file" "$stage/$PROBE_MEMBER" \
	>"$stage/probe-build.txt"
bash "$probe_builder" "$source_file" "$replica/$PROBE_MEMBER" >/dev/null
cmp -s "$stage/$PROBE_MEMBER" "$replica/$PROBE_MEMBER" ||
	die 'independent Cassini helper builds differ'
python3 "$probe_validator" --source "$source_file" \
	--binary "$stage/$PROBE_MEMBER" >"$stage/probe-validation.txt"
install -m 0600 "$source_file" "$stage/cassini-probe.c"

bash "$initramfs_builder" "$ao_artifact/$AO_INITRAMFS" "$source_file" \
	"$stage/$PROBE_MEMBER" "$stage/$INITRAMFS_MEMBER" \
	>"$stage/initramfs-validation.txt"
bash "$initramfs_builder" "$ao_artifact/$AO_INITRAMFS" "$source_file" \
	"$replica/$PROBE_MEMBER" "$replica/$INITRAMFS_MEMBER" >/dev/null
cmp -s "$stage/$INITRAMFS_MEMBER" "$replica/$INITRAMFS_MEMBER" ||
	die 'independent Cassini initramfs derivations differ'

bash "$dtb_builder" --ao-dtb "$ao_artifact/$AO_DTB" \
	--output "$stage/$DTB_MEMBER" >"$stage/dtb-validation.txt"
bash "$dtb_builder" --ao-dtb "$ao_artifact/$AO_DTB" \
	--output "$replica/$DTB_MEMBER" >/dev/null
cmp -s "$stage/$DTB_MEMBER" "$replica/$DTB_MEMBER" ||
	die 'independent Cassini DT derivations differ'

install -m 0600 "$ao_artifact/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$ao_artifact/console-unicode-mode" \
	"$stage/console-unicode-mode"
install -m 0755 "$ao_artifact/console-keymap-verify" \
	"$stage/console-keymap-verify"
install -m 0755 "$ao_artifact/input-event-capture" \
	"$stage/input-event-capture"

boot_cmdline=bootopt=64S3,32N2,64N2
for output in "$stage/$BOOT_MEMBER" "$replica/$BOOT_MEMBER"; do
	python3 "$serializer" --kernel "$stage/Image.gz" \
		--ramdisk "$stage/$INITRAMFS_MEMBER" --dtb "$stage/$DTB_MEMBER" \
		--output "$output" --name gemini-cassini \
		--cmdline "$boot_cmdline" --kernel-addr 0x40200000 \
		--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
		--tags-addr 0x44000000 --lk-android8 >"${output}.serializer"
done
cmp -s "$stage/$BOOT_MEMBER" "$replica/$BOOT_MEMBER" ||
	die 'independent Cassini Android-v0 assemblies differ'
grep -v '^output=' "$stage/$BOOT_MEMBER.serializer" >"$stage/serializer.txt"
rm "$stage/$BOOT_MEMBER.serializer" "$replica/$BOOT_MEMBER.serializer"
python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/$INITRAMFS_MEMBER" \
	--expected-dtb "$stage/$DTB_MEMBER" --expected-name gemini-cassini \
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
	die 'Cassini image does not fit boot2'
padded="$workdir/boot2-padded.img"
dd if=/dev/zero of="$padded" bs=16M count=1 status=none
dd if="$stage/$BOOT_MEMBER" of="$padded" bs=4M conv=notrunc,fsync status=none
padded_sha256="$(sha256sum "$padded" | awk '{print $1}')"
install -m 0600 "$padded" "$stage/boot2-padded.img"

cat >"$stage/provenance.txt" <<EOF
experiment=$(value EXPERIMENT)
candidate=Cassini
kernel_profile=$(value PROFILE)
patch_series=$(value SERIES)
boot_container=canonical-android-v0-lk-android8
candidate_raw_sha256=$raw_sha256
candidate_raw_size=$raw_size
candidate_padded_boot2_sha256=$padded_sha256
predecessor_pioneer_padded_sha256=$(value PIONEER_PADDED_SHA256)
final_dtb_sha256=$(sha256sum "$stage/$DTB_MEMBER" | awk '{print $1}')
initramfs_sha256=$(sha256sum "$stage/$INITRAMFS_MEMBER" | awk '{print $1}')
probe_source_sha256=$(value PROBE_SOURCE_SHA256)
probe_binary_sha256=$(sha256sum "$stage/$PROBE_MEMBER" | awk '{print $1}')
adapter=/i2c@1100e000
i2c6=enabled-childless
probe=manual-post-usb-only-0x69-05-06-47-twice
page_con_access=none
cpu8_cpu9=fail-closed-unrequested
storage_access=none
hardware_write=none
runtime_result=not-tested
EOF

expected="$(printf '%s\n' Image.gz System.map analysis.txt boot2-padded.img \
	cassini-probe cassini-probe.c console-keymap-verify console-unicode-mode \
	dtb-validation.txt gemini-us.bkeymap initramfs-validation.txt \
	input-event-capture kernel.config package-validation.txt probe-build.txt \
	probe-validation.txt provenance.txt serializer.txt source-build.json \
	standard-package-validation.txt "$BOOT_MEMBER" "$DTB_MEMBER" \
	"$INITRAMFS_MEMBER" | sort)"
actual="$(find "$stage" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)"
[[ "$actual" == "$expected" ]] || die 'Cassini output inventory changed'
(cd "$stage" && find . -type f ! -name SHA256SUMS -print0 |
	sort -z | xargs -0 sha256sum) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'Cassini artifact manifest failed'
chmod 0600 "$stage"/*
chmod 0755 "$stage/cassini-probe" "$stage/console-keymap-verify" \
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

printf 'validation=candidate-cassini-assembled\n'
printf 'artifact=%s\nraw_sha256=%s\nraw_size=%s\n' \
	"$output" "$raw_sha256" "$raw_size"
printf 'padded_boot2_sha256=%s\n' "$padded_sha256"
printf 'predecessor_pioneer_padded_sha256=%s\n' \
	"$(value PIONEER_PADDED_SHA256)"
printf 'device_access=none\nruntime_result=not-tested\n'
