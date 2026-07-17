#!/usr/bin/env bash

set -euo pipefail

export LC_ALL=C
umask 077

usage() {
	cat >&2 <<'EOF'
usage: build-display-lk-candidate.sh --package DIR --output DIR

Build a private, non-flashing LK candidate with the retained framebuffer
handoff and a tty0/fbcon initramfs.
EOF
}

die() {
	echo "error: $*" >&2
	exit 2
}

package=
output=
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
		-h|--help)
			usage
			exit 0
			;;
		*)
			usage
			die "unknown argument: $1"
			;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die "run inside the Linux development VM"
[[ "$(uname -m)" == aarch64 ]] || die "expected an aarch64 development VM"
[[ -n "$package" && -d "$package" ]] || die "--package must be a package directory"
[[ -n "$output" && ! -e "$output" ]] || die "--output must be a new directory"

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
experiment_dir=$(cd -- "$script_dir/.." && pwd -P)
repo_root=$(cd -- "$experiment_dir/../.." && pwd -P)
validator="$repo_root/scripts/validate-kernel-artifact"
initramfs_builder="$script_dir/build-display-initramfs.sh"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
package=$(cd -- "$package" && pwd -P)
package_id=$(basename "$package")
image_gz="$package/Image.gz"
dtb="$package/dtbs/mediatek/mt6797-gemini-pda.dtb"
[[ -s "$image_gz" ]] || die "missing Image.gz: $image_gz"
[[ -s "$dtb" ]] || die "missing Gemini DTB: $dtb"

mkdir -p "$output"
initramfs="$output/${package_id}-display-initramfs.img"
candidate="$output/${package_id}-display.boot.img"
provenance="$output/provenance.txt"
SOURCE_DATE_EPOCH=0 "$initramfs_builder" --output "$initramfs" >/dev/null
"$validator" "$package" >/dev/null
cmdline='bootopt=64S3,32N2,64N2 console=tty0 root=/dev/ram0 rw'
python3 "$serializer" \
	--kernel "$image_gz" \
	--ramdisk "$initramfs" \
	--dtb "$dtb" \
	--output "$candidate" \
	--name gemini-display \
	--cmdline "$cmdline" \
	--lk-android8 >/dev/null
parser_output=$(mktemp)
cleanup() {
	rm -f "$parser_output" "$provenance.tmp"
}
trap cleanup EXIT
python3 "$analyzer" "$candidate" > "$parser_output"
{
	printf 'validation=private-display-lk-candidate-wrapper\n'
	printf 'package=%s\n' "$package_id"
	printf 'cmdline=%s\n' "$cmdline"
	printf 'initramfs=%s\n' "$initramfs"
	printf 'candidate=%s\n' "$candidate"
	printf 'initramfs_sha256=%s\n' "$(sha256sum "$initramfs" | awk '{print $1}')"
	printf 'candidate_sha256=%s\n' "$(sha256sum "$candidate" | awk '{print $1}')"
	printf 'hardware_write=none\n'
	printf 'flash=none\n\n[lk_parser]\n'
	cat "$parser_output"
} > "$provenance.tmp"
mv "$provenance.tmp" "$provenance"
chmod 0600 "$initramfs" "$candidate" "$provenance"

printf 'validation=private-display-lk-candidate-wrapper\npackage=%s\ncandidate=%s\ncandidate_sha256=%s\n' \
	"$package_id" "$candidate" "$(sha256sum "$candidate" | awk '{print $1}')"
