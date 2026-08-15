#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --bundle DIR --active-boot FILE --ac-artifact DIR --output-parent DIR\n' "$0"
}

bundle=
active_boot=
ac_artifact=
output_parent=
while (($#)); do
	case "$1" in
	--bundle|--active-boot|--ac-artifact|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--bundle) bundle=$2 ;;
		--active-boot) active_boot=$2 ;;
		--ac-artifact) ac_artifact=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage >&2; die "unknown argument: $1" ;;
	esac
done
[[ -n "$bundle" && -n "$active_boot" && -n "$ac_artifact" && -n "$output_parent" ]] ||
	{ usage >&2; exit 2; }

for command in awk chmod cmp cp dirname find mkdir mktemp mv python3 rm sha256sum \
	sort tail truncate wc xargs dd; do
	command -v "$command" >/dev/null 2>&1 || die "missing command: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
bundle="$(cd -- "$bundle" && pwd -P)"
active_boot="$(cd -- "$(dirname -- "$active_boot")" && pwd -P)/$(basename -- "$active_boot")"
ac_artifact="$(cd -- "$ac_artifact" && pwd -P)"
mkdir -p "$output_parent"
output_parent="$(cd -- "$output_parent" && pwd -P)"
init_builder="$script_dir/build-diagnostic-initramfs.py"
assembler="$script_dir/assemble-diagnostic.py"
ac_initramfs="$ac_artifact/gemini-usb-gadget-ethernet-initramfs.img"
kernel="$bundle/outputs/Image.gz-dtb"

readonly INIT_BUILDER_SHA256=0abe8a8b02ec3767c21fc018c69cc7e2db5ddb475a00e443247474a582f29f38
readonly ASSEMBLER_SHA256=66b5617e1aee8befdaf3d064b0966a6d2cebe256e0e8092e19fb10b34c2fa0f2
readonly AC_MANIFEST_SHA256=d95fd92cd173f0c93c2d4197d81ffba6aef1cbe40bfe2777a68acfe3acb24370
readonly AC_INITRAMFS_SHA256=166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3
readonly PACKAGE_MANIFEST_SHA256=4ed3b81a09f992bb0c80e66d35aa0f9a91bab72b9a14f288f284648abcb76821
readonly ACTIVE_BOOT_SHA256=1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513
readonly KERNEL_SHA256=d49d03911837af1519efc3089018e505e2a213f4682dd7cb25a751e65f8cdb7d
readonly INITRAMFS_SHA256=86a112ef29fecdb8f47b003cbfb08b77b478c4f511cba46acd987af09c921358
readonly RAW_SHA256=1d303dda10b47248f51a1fb2c8f3b1a7b8098522536f4f54ff763c17e75ff310
readonly PADDED_SHA256=ea603c1b1a64d4f1aa9cac3e53957a3e858a7ce04127f1aef36d4b0e8173cb02

for input in "$init_builder" "$assembler" "$active_boot" "$ac_initramfs" "$kernel" \
	"$ac_artifact/SHA256SUMS" "$bundle/SHA256SUMS"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || die "unsafe input: $input"
done
[[ "$(sha256sum "$init_builder" | awk '{print $1}')" == "$INIT_BUILDER_SHA256" ]] || die 'initramfs builder changed'
[[ "$(sha256sum "$assembler" | awk '{print $1}')" == "$ASSEMBLER_SHA256" ]] || die 'diagnostic assembler changed'
[[ "$(sha256sum "$ac_artifact/SHA256SUMS" | awk '{print $1}')" == "$AC_MANIFEST_SHA256" ]] || die 'AC manifest changed'
[[ "$(sha256sum "$bundle/SHA256SUMS" | awk '{print $1}')" == "$PACKAGE_MANIFEST_SHA256" ]] || die 'Buildbox manifest changed'
(cd "$ac_artifact" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'AC artifact validation failed'
(cd "$bundle" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'Buildbox artifact validation failed'
[[ "$(sha256sum "$active_boot" | awk '{print $1}')" == "$ACTIVE_BOOT_SHA256" ]] || die 'active boot changed'
[[ "$(sha256sum "$ac_initramfs" | awk '{print $1}')" == "$AC_INITRAMFS_SHA256" ]] || die 'AC initramfs changed'
[[ "$(sha256sum "$kernel" | awk '{print $1}')" == "$KERNEL_SHA256" ]] || die 'observer kernel changed'

workdir="$(mktemp -d "$output_parent/.provenance-diagnostic.XXXXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"
for root in "$stage" "$replica"; do
	python3 "$init_builder" --baseline "$ac_initramfs" --output "$root/diagnostic-initramfs.img" >"$root/initramfs.txt"
	python3 "$assembler" --active-boot "$active_boot" --kernel-field "$kernel" \
		--ramdisk "$root/diagnostic-initramfs.img" --output "$root/provenance-observer-vendor-rndis.boot.img" \
		>"$root/assembly.txt"
done
cmp -s "$stage/diagnostic-initramfs.img" "$replica/diagnostic-initramfs.img" || die 'initramfs replicas differ'
cmp -s "$stage/provenance-observer-vendor-rndis.boot.img" "$replica/provenance-observer-vendor-rndis.boot.img" || die 'raw replicas differ'

cp "$stage/provenance-observer-vendor-rndis.boot.img" "$stage/boot2-padded.img"
truncate -s 16777216 "$stage/boot2-padded.img"
dd if=/dev/zero of="$replica/boot2-padded.img" bs=1048576 count=16 status=none
dd if="$replica/provenance-observer-vendor-rndis.boot.img" of="$replica/boot2-padded.img" \
	bs=1048576 conv=notrunc status=none
cmp -s "$stage/boot2-padded.img" "$replica/boot2-padded.img" || die 'padding constructions differ'
raw_size="$(wc -c <"$stage/provenance-observer-vendor-rndis.boot.img" | tr -d ' ')"
tail_size=$((16777216 - raw_size))
tail -c "$tail_size" "$stage/boot2-padded.img" | cmp -n "$tail_size" - /dev/zero >/dev/null || die 'padding is nonzero'
[[ "$(sha256sum "$stage/diagnostic-initramfs.img" | awk '{print $1}')" == "$INITRAMFS_SHA256" ]] || die 'diagnostic initramfs identity changed'
[[ "$(sha256sum "$stage/provenance-observer-vendor-rndis.boot.img" | awk '{print $1}')" == "$RAW_SHA256" ]] || die 'raw identity changed'
[[ "$(sha256sum "$stage/boot2-padded.img" | awk '{print $1}')" == "$PADDED_SHA256" ]] || die 'padded identity changed'

grep -v '^output=' "$stage/initramfs.txt" >"$stage/initramfs-analysis.txt"
grep -v '^output=' "$stage/assembly.txt" >"$stage/container-analysis.txt"
rm "$stage/initramfs.txt" "$stage/assembly.txt" "$replica/initramfs.txt" "$replica/assembly.txt"
{
	printf 'experiment=2026-08-14-mt6797-runtime-provenance-observer\n'
	printf 'derivative=vendor-rndis-independent-observation-path\n'
	printf 'kernel_sha256=%s\nactive_boot_sha256=%s\n' "$KERNEL_SHA256" "$ACTIVE_BOOT_SHA256"
	printf 'ac_initramfs_sha256=%s\ndiagnostic_initramfs_sha256=%s\n' "$AC_INITRAMFS_SHA256" "$INITRAMFS_SHA256"
	printf 'raw_sha256=%s\nraw_size=%s\npadded_sha256=%s\npadded_size=16777216\n' "$RAW_SHA256" "$raw_size" "$PADDED_SHA256"
	printf 'kernel_dtb_config_identical_to_attempt_1=yes\nramdisk_observation_path_changed=yes\n'
	printf 'device_storage_access=none\ndvfsp_hardware_write=none\n'
	printf 'usb_transport=legacy-android-rndis-only\nautomatic_reboot=none\n'
	printf 'device_access=none\nruntime_result=not-tested\n'
} >"$stage/provenance.txt"
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum >SHA256SUMS
)
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'output manifest failed'
chmod 0600 "$stage"/*

output_name="gemian-runtime-provenance-observer-rndis-${RAW_SHA256:0:12}"
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv "$stage" "$output"
stage=
rm -rf -- "$replica"
rmdir "$workdir"
workdir=
trap - EXIT HUP INT TERM
printf 'validation=provenance-observer-vendor-rndis-container\n'
printf 'artifact=%s\nraw_sha256=%s\npadded_sha256=%s\n' "$output" "$RAW_SHA256" "$PADDED_SHA256"
printf 'kernel_dtb_config_identical_to_attempt_1=yes\ndevice_access=none\n'
