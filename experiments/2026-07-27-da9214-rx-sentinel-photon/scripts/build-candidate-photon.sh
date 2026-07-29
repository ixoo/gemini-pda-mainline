#!/usr/bin/env bash

# Assemble storage-inert Candidate Photon from exact runtime-tested Cassini.
# This builder never accesses a device, selects a slot, or writes a partition.
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
export SOURCE_DATE_EPOCH=0
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --cassini-artifact DIR --output-parent DIR\n' "$0" >&2
}
cassini_artifact=
output_parent=
while (($#)); do
	case "$1" in
	--cassini-artifact|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--cassini-artifact) cassini_artifact=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$cassini_artifact" && -n "$output_parent" ]] ||
	{ usage; exit 2; }
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] ||
	die 'run in the Linux AArch64 recovery VM'
for directory in "$cassini_artifact" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] ||
		die "unsafe or missing directory: $directory"
done
for command in awk bash chmod cmp cut dd find grep install mkdir mktemp mv \
	python3 rm rmdir sed sha256sum sort stat tr wc xargs; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
cassini_artifact="$(cd -- "$cassini_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$cassini_artifact"|"$cassini_artifact"/*)
	die 'output parent must be outside the repository and Cassini input' ;;
esac

value() {
	PYTHONPATH="$script_dir" python3 -c \
		'import candidate_photon as c,sys; print(getattr(c,sys.argv[1]))' "$1"
}
require_pin_or_unresolved() {
	local actual=$1
	local constant=$2
	local expected
	expected="$(value "$constant")"
	[[ "$expected" == UNRESOLVED || "$actual" == "$expected" ]] ||
		die "calibrated Photon $constant changed: $actual"
}
CASSINI_NAME="$(value CASSINI_ARTIFACT_DIR)"
CASSINI_BOOT="$(value CASSINI_BOOT_MEMBER)"
CASSINI_DTB="$(value CASSINI_DTB_MEMBER)"
CASSINI_INITRAMFS="$(value CASSINI_INITRAMFS_MEMBER)"
BOOT_MEMBER="$(value BOOT_MEMBER)"
DTB_MEMBER="$(value DTB_MEMBER)"
INITRAMFS_MEMBER="$(value INITRAMFS_MEMBER)"
PROBE_MEMBER="$(value PROBE_MEMBER)"
readonly CASSINI_NAME CASSINI_BOOT CASSINI_DTB CASSINI_INITRAMFS
readonly BOOT_MEMBER DTB_MEMBER INITRAMFS_MEMBER PROBE_MEMBER

source_file="$experiment_dir/initramfs/photon-probe.c"
probe_builder="$script_dir/build-photon-probe.sh"
probe_validator="$script_dir/validate-photon-probe.py"
initramfs_builder="$script_dir/build-photon-initramfs.sh"
initramfs_validator="$script_dir/validate-photon-initramfs.py"
direct_builder="$script_dir/replace-cassini-ramdisk.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in "$source_file" "$probe_builder" "$probe_validator" \
	"$initramfs_builder" "$initramfs_validator" "$direct_builder" \
	"$serializer" "$analyzer"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "repository input missing or unsafe: $input"
done
[[ "$(sha256sum "$source_file" | awk '{print $1}')" == \
	"$(value PROBE_SOURCE_SHA256)" ]] || die 'Photon probe source changed'
[[ "$(sha256sum "$serializer" | awk '{print $1}')" == \
	"$(value SERIALIZER_SHA256)" ]] || die 'Android-v0 serializer changed'
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == \
	"$(value ANALYZER_SHA256)" ]] || die 'LK analyzer changed'

[[ "$(basename -- "$cassini_artifact")" == "$CASSINI_NAME" ]] ||
	die 'wrong Candidate Cassini artifact'
[[ "$(stat -c %a "$cassini_artifact")" == 700 ]] ||
	die 'Cassini artifact mode is not 0700'
for member in SHA256SUMS Image.gz System.map kernel.config source-build.json \
	"$CASSINI_BOOT" "$CASSINI_DTB" "$CASSINI_INITRAMFS" boot2-padded.img; do
	[[ -f "$cassini_artifact/$member" && ! -L "$cassini_artifact/$member" ]] ||
		die "Candidate Cassini member missing: $member"
done
(cd "$cassini_artifact" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'Candidate Cassini manifest failed'
[[ "$(sha256sum "$cassini_artifact/SHA256SUMS" | awk '{print $1}')" == \
	"$(value CASSINI_MANIFEST_SHA256)" ]] || die 'Cassini manifest changed'
[[ "$(sha256sum "$cassini_artifact/$CASSINI_BOOT" | awk '{print $1}')" == \
	"$(value CASSINI_BOOT_SHA256)" ]] || die 'Cassini boot changed'
[[ "$(wc -c <"$cassini_artifact/$CASSINI_BOOT" | tr -d ' ')" == \
	"$(value CASSINI_BOOT_SIZE)" ]] || die 'Cassini boot size changed'
[[ "$(sha256sum "$cassini_artifact/boot2-padded.img" | awk '{print $1}')" == \
	"$(value CASSINI_PADDED_SHA256)" ]] || die 'Cassini padded boot changed'
[[ "$(sha256sum "$cassini_artifact/Image.gz" | awk '{print $1}')" == \
	"$(value CASSINI_IMAGE_GZ_SHA256)" ]] || die 'Cassini Image.gz changed'
[[ "$(sha256sum "$cassini_artifact/System.map" | awk '{print $1}')" == \
	"$(value CASSINI_SYSTEM_MAP_SHA256)" ]] || die 'Cassini System.map changed'
[[ "$(sha256sum "$cassini_artifact/kernel.config" | awk '{print $1}')" == \
	"$(value CASSINI_CONFIG_SHA256)" ]] || die 'Cassini config changed'
[[ "$(sha256sum "$cassini_artifact/source-build.json" | awk '{print $1}')" == \
	"$(value CASSINI_SOURCE_BUILD_SHA256)" ]] || die 'Cassini provenance changed'
[[ "$(sha256sum "$cassini_artifact/$CASSINI_DTB" | awk '{print $1}')" == \
	"$(value CASSINI_DTB_SHA256)" ]] || die 'Cassini DTB changed'
[[ "$(sha256sum "$cassini_artifact/$CASSINI_INITRAMFS" | awk '{print $1}')" == \
	"$(value CASSINI_INITRAMFS_SHA256)" ]] || die 'Cassini initramfs changed'

workdir="$(mktemp -d "$output_parent/.candidate-photon.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

install -m 0600 "$cassini_artifact/Image.gz" "$stage/Image.gz"
install -m 0600 "$cassini_artifact/System.map" "$stage/System.map"
install -m 0600 "$cassini_artifact/kernel.config" "$stage/kernel.config"
install -m 0600 "$cassini_artifact/source-build.json" "$stage/source-build.json"
install -m 0600 "$cassini_artifact/$CASSINI_DTB" "$stage/$DTB_MEMBER"
install -m 0600 "$cassini_artifact/SHA256SUMS" \
	"$stage/cassini-foundation.SHA256SUMS"

cat >"$stage/foundation-validation.txt" <<EOF
validation=exact-runtime-tested-cassini-foundation
cassini_artifact=$CASSINI_NAME
cassini_manifest_sha256=$(value CASSINI_MANIFEST_SHA256)
cassini_raw_sha256=$(value CASSINI_BOOT_SHA256)
cassini_padded_sha256=$(value CASSINI_PADDED_SHA256)
image_gz_sha256=$(value CASSINI_IMAGE_GZ_SHA256)
dtb_sha256=$(value CASSINI_DTB_SHA256)
config_sha256=$(value CASSINI_CONFIG_SHA256)
system_map_sha256=$(value CASSINI_SYSTEM_MAP_SHA256)
kernel_dtb_config_change=none
EOF

bash "$probe_builder" "$source_file" "$stage/$PROBE_MEMBER" \
	>"$stage/probe-build.txt"
bash "$probe_builder" "$source_file" "$replica/$PROBE_MEMBER" >/dev/null
cmp -s "$stage/$PROBE_MEMBER" "$replica/$PROBE_MEMBER" ||
	die 'independent Photon helper builds differ'
require_pin_or_unresolved \
	"$(sha256sum "$stage/$PROBE_MEMBER" | awk '{print $1}')" \
	PROBE_BINARY_SHA256
python3 "$probe_validator" --source "$source_file" \
	--binary "$stage/$PROBE_MEMBER" >"$stage/probe-validation.txt"
install -m 0600 "$source_file" "$stage/photon-probe.c"

bash "$initramfs_builder" "$cassini_artifact/$CASSINI_INITRAMFS" \
	"$source_file" "$stage/$PROBE_MEMBER" "$stage/$INITRAMFS_MEMBER" \
	>"$stage/initramfs-validation.txt"
bash "$initramfs_builder" "$cassini_artifact/$CASSINI_INITRAMFS" \
	"$source_file" "$replica/$PROBE_MEMBER" "$replica/$INITRAMFS_MEMBER" \
	>/dev/null
cmp -s "$stage/$INITRAMFS_MEMBER" "$replica/$INITRAMFS_MEMBER" ||
	die 'independent Photon initramfs derivations differ'
require_pin_or_unresolved \
	"$(sha256sum "$stage/$INITRAMFS_MEMBER" | awk '{print $1}')" \
	INITRAMFS_SHA256

python3 "$direct_builder" \
	--cassini-boot "$cassini_artifact/$CASSINI_BOOT" \
	--cassini-initramfs "$cassini_artifact/$CASSINI_INITRAMFS" \
	--photon-initramfs "$stage/$INITRAMFS_MEMBER" \
	--output "$stage/$BOOT_MEMBER.direct" >"$stage/direct-assembly.txt"

python3 "$serializer" --kernel "$stage/Image.gz" \
	--ramdisk "$stage/$INITRAMFS_MEMBER" --dtb "$stage/$DTB_MEMBER" \
	--output "$stage/$BOOT_MEMBER.serializer" --name "$(value BOOT_NAME)" \
	--cmdline "$(value BOOT_CMDLINE)" --kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
	--tags-addr 0x44000000 --lk-android8 \
	>"$stage/serializer.raw"
grep -v '^output=' "$stage/serializer.raw" >"$stage/serializer.txt"
rm "$stage/serializer.raw"
cmp -s "$stage/$BOOT_MEMBER.direct" "$stage/$BOOT_MEMBER.serializer" ||
	die 'direct replacement and independent Android serializer differ'
mv "$stage/$BOOT_MEMBER.direct" "$stage/$BOOT_MEMBER"
rm "$stage/$BOOT_MEMBER.serializer"

python3 "$direct_builder" \
	--cassini-boot "$cassini_artifact/$CASSINI_BOOT" \
	--cassini-initramfs "$cassini_artifact/$CASSINI_INITRAMFS" \
	--photon-initramfs "$replica/$INITRAMFS_MEMBER" \
	--output "$replica/$BOOT_MEMBER"
cmp -s "$stage/$BOOT_MEMBER" "$replica/$BOOT_MEMBER" ||
	die 'independent Photon Android-v0 assemblies differ'

python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/$INITRAMFS_MEMBER" \
	--expected-dtb "$stage/$DTB_MEMBER" \
	--expected-name "$(value BOOT_NAME)" \
	--expected-cmdline "$(value BOOT_CMDLINE)" "$stage/$BOOT_MEMBER" \
	>"$stage/analysis.raw"
sed -e "s|$workdir|@WORK@|g" -e "s|$repo_root|@REPOSITORY@|g" \
	"$stage/analysis.raw" >"$stage/analysis.txt"
rm "$stage/analysis.raw"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] ||
	die 'LK analyzer did not emit exactly 32 gates'

raw_sha256="$(sha256sum "$stage/$BOOT_MEMBER" | awk '{print $1}')"
raw_size="$(wc -c <"$stage/$BOOT_MEMBER" | tr -d ' ')"
((raw_size > 0 && raw_size <= 16 * 1024 * 1024)) ||
	die 'Photon image does not fit boot2'
require_pin_or_unresolved "$raw_sha256" RAW_SHA256
require_pin_or_unresolved "$raw_size" RAW_SIZE
padded="$workdir/boot2-padded.img"
dd if=/dev/zero of="$padded" bs=16M count=1 status=none
dd if="$stage/$BOOT_MEMBER" of="$padded" bs=4M conv=notrunc,fsync status=none
padded_sha256="$(sha256sum "$padded" | awk '{print $1}')"
require_pin_or_unresolved "$padded_sha256" PADDED_SHA256
install -m 0600 "$padded" "$stage/boot2-padded.img"

cat >"$stage/provenance.txt" <<EOF
experiment=$(value EXPERIMENT)
candidate=Photon
candidate_revision=$(value REVISION)
kernel_profile=$(value PROFILE)
patch_series=$(value SERIES)
kernel_dtb_config=byte-exact-Cassini
boot_container=canonical-android-v0-lk-android8
boot_header_identity=gemini-cassini-preserved
candidate_raw_sha256=$raw_sha256
candidate_raw_size=$raw_size
candidate_padded_boot2_sha256=$padded_sha256
predecessor_cassini_padded_sha256=$(value CASSINI_PADDED_SHA256)
final_dtb_sha256=$(sha256sum "$stage/$DTB_MEMBER" | awk '{print $1}')
initramfs_sha256=$(sha256sum "$stage/$INITRAMFS_MEMBER" | awk '{print $1}')
probe_source_sha256=$(value PROBE_SOURCE_SHA256)
probe_binary_sha256=$(sha256sum "$stage/$PROBE_MEMBER" | awk '{print $1}')
initramfs_delta=only-bin/cassini-probe-data
adapter=/i2c@1100e000
i2c6=enabled-childless
probe=manual-post-usb-only-0x69-05-06-47-twice-distinct-rx-sentinels
page_con_access=none
cpu8_cpu9=fail-closed-unrequested
storage_access=none
hardware_write=none
runtime_result=not-tested
EOF

expected="$(printf '%s\n' Image.gz System.map analysis.txt boot2-padded.img \
	cassini-foundation.SHA256SUMS direct-assembly.txt \
	foundation-validation.txt initramfs-validation.txt kernel.config \
	photon-probe photon-probe.c probe-build.txt probe-validation.txt \
	provenance.txt serializer.txt source-build.json "$BOOT_MEMBER" \
	"$DTB_MEMBER" "$INITRAMFS_MEMBER" | sort)"
actual="$(find "$stage" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)"
[[ "$actual" == "$expected" ]] || die 'Photon output inventory changed'
(cd "$stage" && find . -type f ! -name SHA256SUMS -print0 |
	sort -z | xargs -0 sha256sum) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'Photon artifact manifest failed'
require_pin_or_unresolved \
	"$(sha256sum "$stage/SHA256SUMS" | awk '{print $1}')" \
	ARTIFACT_MANIFEST_SHA256
chmod 0600 "$stage"/*
chmod 0755 "$stage/$PROBE_MEMBER"

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

printf 'validation=candidate-photon-assembled\n'
printf 'artifact=%s\nraw_sha256=%s\nraw_size=%s\n' \
	"$output" "$raw_sha256" "$raw_size"
printf 'padded_boot2_sha256=%s\n' "$padded_sha256"
printf 'predecessor_cassini_padded_sha256=%s\n' \
	"$(value CASSINI_PADDED_SHA256)"
printf 'kernel_dtb_config=byte-exact-cassini\n'
printf 'candidate_revision=%s\n' "$(value REVISION)"
printf 'device_access=none\nruntime_result=not-tested\n'
