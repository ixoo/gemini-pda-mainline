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
usage: test-validator-mutations.sh --baseline-package DIR --package DIR
       --baseline-candidate DIR --candidate DIR

Run positive and mutation-rejection regression tests for Candidate J's package
and Android-v0 validators. All mutations remain below a temporary directory;
the command has no device or hardware-write interface.
EOF
}

baseline_package=
package=
baseline_candidate_dir=
candidate_dir=
while (($#)); do
	case "$1" in
		--baseline-package)
			(($# >= 2)) || die "--baseline-package requires DIR"
			baseline_package=$2
			shift 2
			;;
		--package)
			(($# >= 2)) || die "--package requires DIR"
			package=$2
			shift 2
			;;
		--baseline-candidate)
			(($# >= 2)) || die "--baseline-candidate requires DIR"
			baseline_candidate_dir=$2
			shift 2
			;;
		--candidate)
			(($# >= 2)) || die "--candidate requires DIR"
			candidate_dir=$2
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

[[ "$(uname -s)" == Linux ]] || die "run inside the Linux development VM"
[[ "$(uname -m)" == aarch64 ]] || die "expected an aarch64 development VM"
for value in "$baseline_package" "$package" "$baseline_candidate_dir" "$candidate_dir"; do
	[[ -n "$value" && -d "$value" ]] || die "all four explicit directories are required"
done
for command in awk cp dd grep mktemp mv python3 sed sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
package_validator="${script_dir}/validate-package-delta.py"
boot_validator="${script_dir}/validate-boot-delta.py"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
manifest="${repo_root}/kernel/manifest.json"
clk_fragment="${repo_root}/configs/gemini-clk-ignore-unused.fragment"
for input in "$package_validator" "$boot_validator" "$serializer" "$manifest" "$clk_fragment"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

baseline_boot="${baseline_candidate_dir}/gemini-lk-fbcon-refresh.boot.img"
candidate_boot="${candidate_dir}/gemini-lk-clk-ignore-unused.boot.img"
candidate_dtb="${candidate_dir}/mt6797-gemini-pda-lk-clk-ignore-unused.dtb"
candidate_initramfs="${candidate_dir}/gemini-lk-clk-ignore-unused-initramfs.img"
baseline_image_gz="${baseline_package}/Image.gz"
candidate_image_gz="${package}/Image.gz"
for input in \
	"$baseline_boot" "$candidate_boot" "$candidate_dtb" \
	"$candidate_initramfs" "$baseline_image_gz" "$candidate_image_gz"; do
	[[ -s "$input" ]] || die "required artifact is missing: $input"
done

readonly BASELINE_BOOT_SHA256=92e1a870dad1086f83c777b048d4a684d601a42603157929996769a6ab47a01a
readonly CANDIDATE_BOOT_SHA256=6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4
readonly INVALID_HEADER_ONLY_SHA256=3b87a4f604ab0519290987feec9fdca139d4959b4caa1dbfee9889c4c90d2b6d
readonly BASELINE_IMAGE_SHA256=19592386018c8fd482a5a17fb2483c983d05fc47d65d056211b36beb668512c7
readonly BASELINE_IMAGE_GZ_SHA256=3c001a8950939fdf4e15fb5d94f4c8761e461a2e274f103777c4db97da483a3e
readonly CANDIDATE_IMAGE_SHA256=61d571cbc6853fb2587eabcb96c1f778bf8731034feb0c0fad2a8325a383e2aa
readonly CANDIDATE_IMAGE_GZ_SHA256=fb86a201a4427e71368ea14532213ae4cad104452f28448206fca928d255e318
readonly CANDIDATE_CONFIG_SHA256=283570babf78d9299948a35c8133dfa906b04a0c35a2d0d2997309326d607f0d
readonly CANDIDATE_DTB_SHA256=2054f0affec1ed5edff6b6a7de2a5d97102145c35fd335b4c0fd834571918a34
readonly CANDIDATE_INITRAMFS_SHA256=85059d3128e643deaafc3989c745ed21ec94ec5f24f5002839e0d080d13dfe85

workdir="$(mktemp -d)"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

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

package_args=(
	--baseline-package "$baseline_package"
	--candidate-package "$package"
	--current-manifest "$manifest"
	--clk-fragment "$clk_fragment"
	--expected-baseline-image-sha256 "$BASELINE_IMAGE_SHA256"
	--expected-baseline-image-gz-sha256 "$BASELINE_IMAGE_GZ_SHA256"
	--expected-candidate-image-sha256 "$CANDIDATE_IMAGE_SHA256"
	--expected-candidate-image-gz-sha256 "$CANDIDATE_IMAGE_GZ_SHA256"
	--expected-candidate-config-sha256 "$CANDIDATE_CONFIG_SHA256"
)
python3 "$package_validator" "${package_args[@]}" >/dev/null

mutated_package="${workdir}/mutated-package"
mkdir "$mutated_package"
cp -al "$package"/. "$mutated_package"/
config="${mutated_package}/kernel.config"
cp "$config" "${config}.new"
sed -i 's/ clk_ignore_unused"$/"/' "${config}.new"
mv "${config}.new" "$config"
mutated_package_args=("${package_args[@]}")
mutated_package_args[3]="$mutated_package"
expect_reject "resolved config has 0 differing lines" \
	python3 "$package_validator" "${mutated_package_args[@]}"

boot_args=(
	--baseline "$baseline_boot"
	--candidate "$candidate_boot"
	--baseline-image-gz "$baseline_image_gz"
	--candidate-image-gz "$candidate_image_gz"
	--dtb "$candidate_dtb"
	--initramfs "$candidate_initramfs"
	--expected-baseline-sha256 "$BASELINE_BOOT_SHA256"
	--expected-candidate-sha256 "$CANDIDATE_BOOT_SHA256"
	--expected-baseline-image-gz-sha256 "$BASELINE_IMAGE_GZ_SHA256"
	--expected-candidate-image-gz-sha256 "$CANDIDATE_IMAGE_GZ_SHA256"
	--expected-dtb-sha256 "$CANDIDATE_DTB_SHA256"
	--expected-initramfs-sha256 "$CANDIDATE_INITRAMFS_SHA256"
)
python3 "$boot_validator" "${boot_args[@]}" >/dev/null

mutated_boot="${workdir}/mutated-header.boot.img"
cp "$candidate_boot" "$mutated_boot"
printf c | dd of="$mutated_boot" bs=1 seek=64 conv=notrunc status=none
mutated_boot_sha256="$(sha256sum "$mutated_boot" | awk '{print $1}')"
mutated_boot_args=("${boot_args[@]}")
mutated_boot_args[3]="$mutated_boot"
mutated_boot_args[15]="$mutated_boot_sha256"
expect_reject "primary header cmdline is not exact Candidate I" \
	python3 "$boot_validator" "${mutated_boot_args[@]}"

invalid_boot="${workdir}/rejected-header-only.boot.img"
python3 "$serializer" \
	--kernel "$baseline_image_gz" \
	--ramdisk "$candidate_initramfs" \
	--dtb "$candidate_dtb" \
	--output "$invalid_boot" \
	--name gemini-usbdiag \
	--cmdline 'bootopt=64S3,32N2,64N2 clk_ignore_unused' \
	--kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 \
	--tags-addr 0x44000000 \
	--lk-android8 >/dev/null
[[ "$(sha256sum "$invalid_boot" | awk '{print $1}')" == \
	"$INVALID_HEADER_ONLY_SHA256" ]] || die "reconstructed invalid signature changed"
invalid_boot_args=("${boot_args[@]}")
invalid_boot_args[3]="$invalid_boot"
invalid_boot_args[7]="$baseline_image_gz"
invalid_boot_args[15]="$INVALID_HEADER_ONLY_SHA256"
invalid_boot_args[19]="$BASELINE_IMAGE_GZ_SHA256"
expect_reject "candidate is the rejected header-only no-op artifact" \
	python3 "$boot_validator" "${invalid_boot_args[@]}"

printf 'validation=candidate-j-validator-mutation-regression\n'
printf 'positive_package_delta=passed\n'
printf 'mutated_resolved_config=rejected\n'
printf 'positive_boot_delta=passed\n'
printf 'mutated_android_header_cmdline=rejected\n'
printf 'reconstructed_header_only_noop=rejected\n'
printf 'temporary_mutations_only=yes\n'
printf 'hardware_write=none\n'
