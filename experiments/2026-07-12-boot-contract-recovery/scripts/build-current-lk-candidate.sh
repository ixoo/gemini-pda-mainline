#!/usr/bin/env bash

# Build a private, non-flashing Planet LK candidate from one packaged kernel.
# This script deliberately has no device, partition, fastboot, or flashing
# interface. It is intended to run inside the Linux development VM.

set -euo pipefail

export LC_ALL=C
umask 077

usage() {
	cat >&2 <<'EOF'
usage: build-current-lk-candidate.sh [options]

Build a private Android v0 gzip+appended-DTB candidate for the retained
Planet Gemini LK contract.

options:
  --package DIR   packaged kernel directory (default: newest guest package)
  --output DIR    guest output directory (default: ~/artifacts/boot-candidates/<package>)
  --name NAME     Android image name, at most 15 ASCII bytes (default: gemini-mainline)
  --cmdline TEXT  explicit boot-image command line
  --source-date-epoch N  initramfs metadata epoch (default: 0)
  -h, --help      show this help

The output directory must not already exist. The command never writes a device.
EOF
}

die() {
	echo "error: $*" >&2
	exit 2
}

[[ "$(uname -s)" == Linux ]] || die "run inside the Linux development VM"
[[ "$(uname -m)" == aarch64 ]] || die "expected an aarch64 development VM"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "${script_dir}/../../.." && pwd -P)"
validator="${repo_root}/scripts/validate-kernel-artifact"
initramfs_builder="${script_dir}/build-minimal-initramfs.sh"
serializer="${script_dir}/build-android-boot-v0.py"
analyzer="${script_dir}/analyze-lk-boot-image.py"

package=
output=
image_name=gemini-mainline
cmdline='bootopt=64S3,32N2,64N2 console=ttyS0,921600n8 earlycon=uart8250,mmio32,0x11002000 root=/dev/ram0 rw'
source_date_epoch=${SOURCE_DATE_EPOCH:-0}

while (($#)); do
	case "$1" in
		--package)
			(($# >= 2)) || die "--package requires DIR"
			package=$2
			shift 2
			;;
		--output)
			(($# >= 2)) || die "--output requires DIR"
			output=$2
			shift 2
			;;
		--name)
			(($# >= 2)) || die "--name requires NAME"
			image_name=$2
			shift 2
			;;
		--cmdline)
			(($# >= 2)) || die "--cmdline requires TEXT"
			cmdline=$2
			shift 2
			;;
		--source-date-epoch)
			(($# >= 2)) || die "--source-date-epoch requires N"
			source_date_epoch=$2
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			usage
			die "unknown option: $1"
			;;
	esac
done

[[ -x "$validator" ]] || die "kernel validator is missing: $validator"
[[ -x "$initramfs_builder" ]] || die "initramfs builder is missing: $initramfs_builder"
[[ -r "$serializer" ]] || die "boot serializer is missing: $serializer"
[[ -r "$analyzer" ]] || die "LK image analyzer is missing: $analyzer"

if [[ -z "$package" ]]; then
	artifact_root="${GEMINI_ARTIFACT_ROOT:-${HOME}/artifacts/gemini-pda}"
	[[ -d "$artifact_root" ]] || die "artifact root does not exist: $artifact_root"
	package_record="$(find "$artifact_root" -mindepth 1 -maxdepth 1 \
		-type d -name 'linux-*-gemini-*' -printf '%T@ %p\n' \
		| sort -n | tail -n 1)"
	package="${package_record#* }"
	[[ -n "$package" && "$package" != "$package_record" ]] || \
		die "no packaged kernel found below $artifact_root"
fi

[[ -d "$package" ]] || die "package directory does not exist: $package"
package="$(cd -- "$package" && pwd -P)"
package_id="$(basename "$package")"

if [[ -z "$output" ]]; then
	output="${HOME}/artifacts/boot-candidates/${package_id}"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite existing output: $output"

[[ "$image_name" != *[![:ascii:]]* ]] || die "--name must contain ASCII only"
(( ${#image_name} > 0 && ${#image_name} < 16 )) || \
	die "--name must be between 1 and 15 ASCII bytes"
[[ -n "$cmdline" ]] || die "--cmdline must not be empty"
[[ "$source_date_epoch" =~ ^[0-9]+$ ]] || \
	die "--source-date-epoch must be a non-negative integer"

image_gz="$package/Image.gz"
dtb="$package/dtbs/mediatek/mt6797-gemini-pda.dtb"
[[ -s "$image_gz" ]] || die "missing Image.gz: $image_gz"
[[ -s "$dtb" ]] || die "missing Gemini DTB: $dtb"

validation_log="$(mktemp)"
serializer_log="$(mktemp)"
analysis_log="$(mktemp)"
cleanup() {
	rm -f "$validation_log" "$serializer_log" "$analysis_log"
}
trap cleanup EXIT

"$validator" "$package" >"$validation_log"

mkdir -p "$output"
initramfs="$output/${package_id}-uart-initramfs.img"
candidate="$output/${package_id}.boot.img"
provenance="$output/provenance.txt"

SOURCE_DATE_EPOCH="$source_date_epoch" "$initramfs_builder" --output "$initramfs" >/dev/null
python3 "$serializer" \
	--kernel "$image_gz" \
	--ramdisk "$initramfs" \
	--dtb "$dtb" \
	--output "$candidate" \
	--name "$image_name" \
	--cmdline "$cmdline" \
	--lk-android8 >"$serializer_log"
python3 "$analyzer" "$candidate" >"$analysis_log"

{
	printf 'validation=private-lk-candidate-wrapper\n'
	printf 'source_revision=7.1.3\n'
	printf 'package=%s\n' "$package_id"
	printf 'package_path=%s\n' "$package"
	printf 'image_name=%s\n' "$image_name"
	printf 'cmdline=%s\n' "$cmdline"
	printf 'source_date_epoch=%s\n' "$source_date_epoch"
	printf 'validator=passed\n'
	printf 'initramfs=%s\n' "$initramfs"
	printf 'candidate=%s\n' "$candidate"
	printf 'initramfs_sha256=%s\n' "$(sha256sum "$initramfs" | awk '{print $1}')"
	printf 'candidate_sha256=%s\n' "$(sha256sum "$candidate" | awk '{print $1}')"
	printf 'image_gz_sha256=%s\n' "$(sha256sum "$image_gz" | awk '{print $1}')"
	printf 'gemini_dtb_sha256=%s\n' "$(sha256sum "$dtb" | awk '{print $1}')"
	printf 'hardware_write=none\n'
	printf 'flash=none\n'
	printf '\n[lk_parser]\n'
	cat "$analysis_log"
} >"$provenance"

chmod 0600 "$initramfs" "$candidate" "$provenance"

printf 'validation=private-lk-candidate-wrapper\n'
printf 'package=%s\n' "$package_id"
printf 'candidate=%s\n' "$candidate"
printf 'candidate_sha256=%s\n' "$(sha256sum "$candidate" | awk '{print $1}')"
printf 'initramfs=%s\n' "$initramfs"
printf 'initramfs_sha256=%s\n' "$(sha256sum "$initramfs" | awk '{print $1}')"
printf 'provenance=%s\n' "$provenance"
printf 'hardware_write=none\n'
printf 'flash=none\n'
