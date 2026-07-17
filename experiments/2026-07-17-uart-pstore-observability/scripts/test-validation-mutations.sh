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
usage: test-validation-mutations.sh --package DIR --candidate-dir DIR

Prove that Candidate L's exact LK-component gates and the generic package
inventory/provenance gates reject self-consistent or rehashed mutations. The
inputs are read-only; all mutations remain below a temporary directory.
EOF
}

package=
candidate_dir=
while (($#)); do
	case "$1" in
		--package)
			(($# >= 2)) || die "--package requires DIR"
			package=$2
			shift 2
			;;
		--candidate-dir)
			(($# >= 2)) || die "--candidate-dir requires DIR"
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
[[ -d "$package" ]] || die "package does not exist: $package"
[[ -d "$candidate_dir" ]] || die "candidate directory does not exist: $candidate_dir"
for command in cmp cp dirname fdtput find git grep gzip ln mkdir mktemp mv \
	python3 rm sed sha256sum sort uname xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
package_validator="${repo_root}/scripts/validate-kernel-artifact"
image="${package}/Image"
image_gz="${package}/Image.gz"
ramdisk="${candidate_dir}/gemini-lk-observability-initramfs.img"
dtb="${candidate_dir}/mt6797-gemini-pda-lk-observability.dtb"
candidate="${candidate_dir}/gemini-lk-observability.boot.img"
for input in "$serializer" "$analyzer" "$package_validator" "$image" \
	"$image_gz" "$ramdisk" "$dtb" "$candidate"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

temporary="$(mktemp -d "${TMPDIR:-/tmp}/candidate-l-validation.XXXXXX")"
cleanup() {
	case "$temporary" in
		"${TMPDIR:-/tmp}"/candidate-l-validation.*) rm -rf "$temporary" ;;
		*) die "refusing unsafe temporary cleanup: $temporary" ;;
	esac
}
trap cleanup EXIT

bootopt='bootopt=64S3,32N2,64N2'
serialize() {
	local kernel=$1
	local candidate_ramdisk=$2
	local candidate_dtb=$3
	local name=$4
	local cmdline=$5
	local output=$6
	python3 "$serializer" \
		--kernel "$kernel" --ramdisk "$candidate_ramdisk" --dtb "$candidate_dtb" \
		--output "$output" --name "$name" --cmdline "$cmdline" \
		--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
		--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 \
		>/dev/null
}

analyze_exact() {
	python3 "$analyzer" --validate-lk \
		--expected-image-gz "$image_gz" --expected-ramdisk "$ramdisk" \
		--expected-dtb "$dtb" --expected-name gemini-obs-L \
		--expected-cmdline "$bootopt" "$1"
}

expect_analyzer_rejection() {
	local label=$1
	local expected_failure=$2
	local mutated_candidate=$3
	local log="${temporary}/${label}.analysis"
	if analyze_exact "$mutated_candidate" >"$log" 2>&1; then
		die "analyzer accepted ${label} mutation"
	fi
	grep -Fqx 'lk_validation=failed' "$log" || \
		die "${label} did not reach an attributable LK gate failure"
	grep -Fqx "lk_validation_failures=${expected_failure}" "$log" || \
		die "${label} did not fail only ${expected_failure}"
	printf 'analyzer_reject_%s=%s\n' "$label" "$expected_failure"
}

expect_package_rejection() {
	local label=$1
	local expected_text=$2
	local mutated_package=$3
	local log="${temporary}/${label}.package"
	if "$package_validator" "$mutated_package" >"$log" 2>&1; then
		die "package validator accepted ${label} mutation"
	fi
	grep -Fq "$expected_text" "$log" || \
		die "${label} did not produce the expected package rejection"
	printf 'package_reject_%s=yes\n' "$label"
}

analyze_exact "$candidate" >"${temporary}/baseline.analysis"
grep -Fqx 'lk_validation=passed' "${temporary}/baseline.analysis" || \
	die "baseline Candidate L analyzer validation failed"
printf 'analyzer_baseline=passed\n'

gzip -n -1 -c "$image" >"${temporary}/kernel-mutated.gz"
cmp -s "$image_gz" "${temporary}/kernel-mutated.gz" && \
	die "kernel recompression did not change Image.gz"
serialize "${temporary}/kernel-mutated.gz" "$ramdisk" "$dtb" gemini-obs-L \
	"$bootopt" "${temporary}/kernel.boot.img"
expect_analyzer_rejection kernel expected_image_gz_matches \
	"${temporary}/kernel.boot.img"

cp "$ramdisk" "${temporary}/ramdisk-mutated.img"
printf '\0' >>"${temporary}/ramdisk-mutated.img"
serialize "$image_gz" "${temporary}/ramdisk-mutated.img" "$dtb" gemini-obs-L \
	"$bootopt" "${temporary}/ramdisk.boot.img"
expect_analyzer_rejection ramdisk expected_ramdisk_matches \
	"${temporary}/ramdisk.boot.img"

cp "$dtb" "${temporary}/dtb-mutated.dtb"
fdtput -t s "${temporary}/dtb-mutated.dtb" / model \
	'Planet Computers Gemini PDA mutation test'
serialize "$image_gz" "$ramdisk" "${temporary}/dtb-mutated.dtb" gemini-obs-L \
	"$bootopt" "${temporary}/dtb.boot.img"
expect_analyzer_rejection dtb expected_dtb_matches "${temporary}/dtb.boot.img"

serialize "$image_gz" "$ramdisk" "$dtb" gemini-obs-X "$bootopt" \
	"${temporary}/name.boot.img"
expect_analyzer_rejection name expected_name_matches "${temporary}/name.boot.img"

serialize "$image_gz" "$ramdisk" "$dtb" gemini-obs-L \
	'bootopt=64S3,32N2,64N1' "${temporary}/cmdline.boot.img"
expect_analyzer_rejection cmdline expected_cmdline_matches \
	"${temporary}/cmdline.boot.img"

"$package_validator" "$package" >"${temporary}/baseline.package"
printf 'package_baseline=passed\n'

mutated_package="${temporary}/package"
cp -a "$package" "$mutated_package"
: >"${mutated_package}/provenance/SHA256SUMS"
expect_package_rejection nested_sha256sums \
	"SHA256SUMS is not an exact inventory" "$mutated_package"

rm -rf "$mutated_package"
cp -a "$package" "$mutated_package"
sed '1d' "${mutated_package}/SHA256SUMS" >"${temporary}/missing.SHA256SUMS"
mv "${temporary}/missing.SHA256SUMS" "${mutated_package}/SHA256SUMS"
expect_package_rejection missing_manifest_path \
	"SHA256SUMS is not an exact inventory" "$mutated_package"

rm -rf "$mutated_package"
cp -a "$package" "$mutated_package"
printf '\n# mutation test\n' >>"${mutated_package}/kernel.config"
(
	cd "$mutated_package"
	find . -type f ! -path ./SHA256SUMS -print0 | sort -z | \
		xargs -0 sha256sum >"${temporary}/rehashed.SHA256SUMS"
)
mv "${temporary}/rehashed.SHA256SUMS" "${mutated_package}/SHA256SUMS"
expect_package_rejection stale_config_provenance \
	"provenance config_sha256 does not match kernel.config" "$mutated_package"

rm -rf "$mutated_package"
cp -a "$package" "$mutated_package"
ln -s ../Image "${mutated_package}/provenance/image-link"
expect_package_rejection symlink 'artifact tree contains a non-regular entry' \
	"$mutated_package"

rm -rf "$mutated_package"
cp -a "$package" "$mutated_package"
duplicate_line="$(sed -n '1p' "${mutated_package}/SHA256SUMS")"
printf '%s\n' "$duplicate_line" >>"${mutated_package}/SHA256SUMS"
expect_package_rejection duplicate_manifest_path \
	'duplicate SHA256SUMS path' "$mutated_package"

printf 'validation_mutations=passed\n'
printf 'hardware_write=none\n'
