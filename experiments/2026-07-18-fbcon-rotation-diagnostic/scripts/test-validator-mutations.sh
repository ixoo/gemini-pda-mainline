#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() {
	echo "error: $*" >&2
	exit 2
}

usage() {
	cat >&2 <<'EOF'
usage: test-validator-mutations.sh --baseline DIR

Run positive and mutation-rejection regression tests for Candidate P's
Android-v0 boot validator. DIR must be the exact Candidate O artifact. The
test synthesizes temporary kernel-payload derivatives, needs no Candidate P
artifact, and has no device or hardware-write interface.
EOF
}

baseline_dir=
while (($#)); do
	case "$1" in
		--baseline)
			(($# >= 2)) || die "--baseline requires DIR"
			baseline_dir=$2
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

[[ -n "$baseline_dir" && -d "$baseline_dir" ]] || \
	die "--baseline must name the exact Candidate O artifact directory"
for command in awk cp grep mktemp python3 rm sha256sum wc; do
	command -v "$command" >/dev/null 2>&1 || \
		die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
validator="${script_dir}/validate-boot-delta.py"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
for input in "$validator" "$serializer"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

baseline_dir="$(cd -- "$baseline_dir" && pwd -P)"
baseline_boot="${baseline_dir}/gemini-a53-sweep.boot.img"
dtb="${baseline_dir}/mt6797-gemini-pda-a53-sweep.dtb"
initramfs="${baseline_dir}/gemini-a53-sweep-initramfs.img"
for input in "$baseline_boot" "$dtb" "$initramfs"; do
	[[ -s "$input" ]] || die "Candidate O input is missing: $input"
done

readonly BASELINE_BOOT_SHA256=4376579c3b1a9ddfbec485eb62ba6cfc0af38183527924b5a250246345cb2146
readonly BASELINE_IMAGE_GZ_SHA256=0c0d0e22c78b5b0d89b7a7363be55850b3f3474d3b4e7f922946747efbe164d3
readonly DTB_SHA256=c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379
readonly INITRAMFS_SHA256=3f19afd81632fbe654c024b9f865180b42caf61163bb26ea26211884271a11d8
readonly ZERO_SHA256=0000000000000000000000000000000000000000000000000000000000000000

sha256() {
	sha256sum "$1" | awk '{print $1}'
}

[[ "$(sha256 "$baseline_boot")" == "$BASELINE_BOOT_SHA256" ]] || \
	die "baseline boot image is not exact Candidate O"
[[ "$(sha256 "$dtb")" == "$DTB_SHA256" ]] || \
	die "baseline DTB is not exact Candidate O"
[[ "$(sha256 "$initramfs")" == "$INITRAMFS_SHA256" ]] || \
	die "baseline initramfs is not exact Candidate O"

workdir="$(mktemp -d)"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

baseline_image_gz="${workdir}/candidate-o.Image.gz"
python3 -c '
import pathlib
import struct
import sys

boot = pathlib.Path(sys.argv[1]).read_bytes()
dtb = pathlib.Path(sys.argv[2]).read_bytes()
output = pathlib.Path(sys.argv[3])
kernel_size = struct.unpack_from("<I", boot, 8)[0]
page_size = struct.unpack_from("<I", boot, 36)[0]
if page_size != 2048 or kernel_size <= len(dtb):
    raise SystemExit("invalid Candidate O kernel layout")
kernel = boot[page_size : page_size + kernel_size]
if not kernel.endswith(dtb):
    raise SystemExit("Candidate O kernel segment does not end with the explicit DTB")
output.write_bytes(kernel[: -len(dtb)])
' "$baseline_boot" "$dtb" "$baseline_image_gz"
[[ "$(sha256 "$baseline_image_gz")" == "$BASELINE_IMAGE_GZ_SHA256" ]] || \
	die "extracted Image.gz is not exact Candidate O"

make_boot() {
	local image_gz=$1
	local boot_dtb=$2
	local ramdisk=$3
	local output=$4
	python3 "$serializer" \
		--kernel "$image_gz" \
		--ramdisk "$ramdisk" \
		--dtb "$boot_dtb" \
		--output "$output" \
		--name gemini-obs-L \
		--cmdline 'bootopt=64S3,32N2,64N2' \
		--kernel-addr 0x40200000 \
		--ramdisk-addr 0x45000000 \
		--second-addr 0x40f00000 \
		--tags-addr 0x44000000 \
		--lk-android8 >/dev/null
}

run_validator() {
	local candidate_boot=$1
	local candidate_image_gz=$2
	local expected_candidate_boot=$3
	local expected_candidate_image_gz=$4
	local expected_baseline_boot=${5:-$BASELINE_BOOT_SHA256}
	python3 "$validator" \
		--baseline "$baseline_boot" \
		--candidate "$candidate_boot" \
		--baseline-image-gz "$baseline_image_gz" \
		--candidate-image-gz "$candidate_image_gz" \
		--dtb "$dtb" \
		--initramfs "$initramfs" \
		--expected-baseline-sha256 "$expected_baseline_boot" \
		--expected-candidate-sha256 "$expected_candidate_boot" \
		--expected-baseline-image-gz-sha256 "$BASELINE_IMAGE_GZ_SHA256" \
		--expected-candidate-image-gz-sha256 "$expected_candidate_image_gz" \
		--expected-dtb-sha256 "$DTB_SHA256" \
		--expected-initramfs-sha256 "$INITRAMFS_SHA256"
}

expect_reject() {
	local expected=$1
	shift
	if "$@" >"${workdir}/reject.out" 2>"${workdir}/reject.err"; then
		die "validator accepted a mutation expected to fail: $expected"
	fi
	grep -Fq -- "$expected" "${workdir}/reject.err" || {
		cat "${workdir}/reject.err" >&2
		die "validator rejected for an unexpected reason; wanted: $expected"
	}
}

mutate_byte() {
	local source=$1
	local destination=$2
	local offset=$3
	python3 -c '
import pathlib
import sys

data = bytearray(pathlib.Path(sys.argv[1]).read_bytes())
offset = int(sys.argv[3])
if offset < 0:
    offset += len(data)
if offset < 0 or offset >= len(data):
    raise SystemExit("mutation offset outside file")
data[offset] ^= 1
pathlib.Path(sys.argv[2]).write_bytes(data)
' "$source" "$destination" "$offset"
}

# Positive synthetic P derivative with a changed kernel-segment size. The
# package validator, not this container validator, establishes kernel semantics.
candidate_image_gz="${workdir}/candidate-p.Image.gz"
python3 -c '
import gzip
import pathlib
import sys

source = pathlib.Path(sys.argv[1]).read_bytes()
image = gzip.decompress(source)
for repeat in range(1, 33):
    candidate = gzip.compress(
        image + b"candidate-p-validator-mutation" * repeat,
        compresslevel=9,
        mtime=0,
    )
    if len(candidate) != len(source):
        pathlib.Path(sys.argv[2]).write_bytes(candidate)
        break
else:
    raise SystemExit("could not synthesize a size-changing gzip stream")
' "$baseline_image_gz" "$candidate_image_gz"
candidate_boot="${workdir}/candidate-p.boot.img"
make_boot "$candidate_image_gz" "$dtb" "$initramfs" "$candidate_boot"
candidate_image_gz_sha256="$(sha256 "$candidate_image_gz")"
candidate_boot_sha256="$(sha256 "$candidate_boot")"
run_validator \
	"$candidate_boot" "$candidate_image_gz" \
	"$candidate_boot_sha256" "$candidate_image_gz_sha256" >/dev/null

# A bytewise-new, same-size Image.gz exercises the ID-only header-delta path.
same_size_image_gz="${workdir}/candidate-p-same-size.Image.gz"
# Gzip byte 9 is the informational OS field; changing it preserves the single
# valid stream and decompressed ARM64 Image while changing the container bytes.
mutate_byte "$baseline_image_gz" "$same_size_image_gz" 9
same_size_boot="${workdir}/candidate-p-same-size.boot.img"
make_boot "$same_size_image_gz" "$dtb" "$initramfs" "$same_size_boot"
run_validator \
	"$same_size_boot" "$same_size_image_gz" \
	"$(sha256 "$same_size_boot")" "$(sha256 "$same_size_image_gz")" >/dev/null

expect_reject "Candidate P boot SHA-256 is not pinned" \
	run_validator \
	"$candidate_boot" "$candidate_image_gz" \
	"$ZERO_SHA256" "$candidate_image_gz_sha256"
expect_reject "Candidate P Image.gz SHA-256 is not pinned" \
	run_validator \
	"$candidate_boot" "$candidate_image_gz" \
	"$candidate_boot_sha256" "$ZERO_SHA256"
expect_reject "expected Candidate O boot SHA-256 is not exact Candidate O" \
	run_validator \
	"$candidate_boot" "$candidate_image_gz" \
	"$candidate_boot_sha256" "$candidate_image_gz_sha256" "$ZERO_SHA256"

unchanged_boot="${workdir}/unchanged-kernel.boot.img"
make_boot "$baseline_image_gz" "$dtb" "$initramfs" "$unchanged_boot"
expect_reject "compiled kernel payload did not change" \
	run_validator \
	"$unchanged_boot" "$baseline_image_gz" \
	"$(sha256 "$unchanged_boot")" "$BASELINE_IMAGE_GZ_SHA256"

mutated_dtb="${workdir}/mutated.dtb"
mutate_byte "$dtb" "$mutated_dtb" -1
mutated_dtb_boot="${workdir}/mutated-dtb.boot.img"
make_boot "$candidate_image_gz" "$mutated_dtb" "$initramfs" "$mutated_dtb_boot"
expect_reject "kernel segment is not its new Image.gz plus exact-O DTB" \
	run_validator \
	"$mutated_dtb_boot" "$candidate_image_gz" \
	"$(sha256 "$mutated_dtb_boot")" "$candidate_image_gz_sha256"

mutated_initramfs="${workdir}/mutated-initramfs.img"
mutate_byte "$initramfs" "$mutated_initramfs" -1
mutated_initramfs_boot="${workdir}/mutated-initramfs.boot.img"
make_boot "$candidate_image_gz" "$dtb" "$mutated_initramfs" \
	"$mutated_initramfs_boot"
expect_reject "boot image ramdisk is not exact Candidate O initramfs" \
	run_validator \
	"$mutated_initramfs_boot" "$candidate_image_gz" \
	"$(sha256 "$mutated_initramfs_boot")" "$candidate_image_gz_sha256"

mutated_name_boot="${workdir}/mutated-name.boot.img"
mutate_byte "$candidate_boot" "$mutated_name_boot" 48
expect_reject "header name is not exact Candidate O" \
	run_validator \
	"$mutated_name_boot" "$candidate_image_gz" \
	"$(sha256 "$mutated_name_boot")" "$candidate_image_gz_sha256"

mutated_cmdline_boot="${workdir}/mutated-cmdline.boot.img"
mutate_byte "$candidate_boot" "$mutated_cmdline_boot" 64
expect_reject "primary header cmdline is not exact Candidate O" \
	run_validator \
	"$mutated_cmdline_boot" "$candidate_image_gz" \
	"$(sha256 "$mutated_cmdline_boot")" "$candidate_image_gz_sha256"

mutated_address_boot="${workdir}/mutated-address.boot.img"
mutate_byte "$candidate_boot" "$mutated_address_boot" 12
expect_reject "unexpected Android-v0 field changes" \
	run_validator \
	"$mutated_address_boot" "$candidate_image_gz" \
	"$(sha256 "$mutated_address_boot")" "$candidate_image_gz_sha256"

mutated_id_boot="${workdir}/mutated-id.boot.img"
mutate_byte "$candidate_boot" "$mutated_id_boot" 576
expect_reject "Candidate P has a noncanonical Android-v0 ID" \
	run_validator \
	"$mutated_id_boot" "$candidate_image_gz" \
	"$(sha256 "$mutated_id_boot")" "$candidate_image_gz_sha256"

kernel_padding_offset="$(python3 -c '
import pathlib
import struct
import sys

boot = pathlib.Path(sys.argv[1]).read_bytes()
kernel_size = struct.unpack_from("<I", boot, 8)[0]
page_size = struct.unpack_from("<I", boot, 36)[0]
kernel_end = page_size + kernel_size
padding_end = (kernel_end + page_size - 1) // page_size * page_size
if kernel_end >= padding_end:
    raise SystemExit("synthetic candidate unexpectedly has no kernel padding")
print(kernel_end)
' "$candidate_boot")"
mutated_padding_boot="${workdir}/mutated-padding.boot.img"
mutate_byte "$candidate_boot" "$mutated_padding_boot" "$kernel_padding_offset"
expect_reject "Candidate P boot image has nonzero kernel padding" \
	run_validator \
	"$mutated_padding_boot" "$candidate_image_gz" \
	"$(sha256 "$mutated_padding_boot")" "$candidate_image_gz_sha256"

printf 'validation=candidate-p-boot-validator-mutation-regression\n'
printf 'positive_changed-size-kernel-delta=passed\n'
printf 'positive_same-size-kernel-delta=passed\n'
printf 'candidate_hash_pins=enforced\n'
printf 'exact_candidate_o_baseline_pins=enforced\n'
printf 'unchanged_kernel=rejected\n'
printf 'changed_dtb_or_initramfs=rejected\n'
printf 'changed_name_cmdline_or_address=rejected\n'
printf 'noncanonical_id=rejected\n'
printf 'nonzero_payload_padding=rejected\n'
printf 'temporary_mutations_only=yes\n'
printf 'hardware_write=none\n'
