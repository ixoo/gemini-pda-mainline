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
usage: test-package-validator-mutations.sh \
       --baseline-package DIR --candidate-package DIR

Run positive and mutation-rejection tests for Candidate P's package-delta
validator. DIR arguments must be the exact Candidate O and Candidate P kernel
packages. Every mutation remains below a private temporary directory; this
script has no device, flashing, or other hardware interface.
EOF
}

baseline_package=
candidate_package=
while (($#)); do
	case "$1" in
		--baseline-package)
			(($# >= 2)) || die "--baseline-package requires DIR"
			baseline_package=$2
			shift 2
			;;
		--candidate-package)
			(($# >= 2)) || die "--candidate-package requires DIR"
			candidate_package=$2
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
[[ -n "$baseline_package" && -d "$baseline_package" ]] || \
	die "--baseline-package must name the exact Candidate O kernel package"
[[ -n "$candidate_package" && -d "$candidate_package" ]] || \
	die "--candidate-package must name the exact Candidate P kernel package"
for command in cp grep mktemp python3 rm; do
	command -v "$command" >/dev/null 2>&1 || \
		die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
validator="${script_dir}/validate-package-delta.py"
manifest="${repo_root}/kernel/manifest.json"
rotation_fragment="${repo_root}/configs/gemini-fbcon-rotation.fragment"
for input in "$validator" "$manifest" "$rotation_fragment"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

baseline_package="$(cd -- "$baseline_package" && pwd -P)"
candidate_package="$(cd -- "$candidate_package" && pwd -P)"
[[ "$baseline_package" != "$candidate_package" ]] || \
	die "baseline and candidate packages must be distinct"

readonly BASELINE_IMAGE_SHA256=91f0ba20a161afd379aa483ef5de2b4d66ff495a23614beaaba1530f459ad2a3
readonly BASELINE_IMAGE_GZ_SHA256=0c0d0e22c78b5b0d89b7a7363be55850b3f3474d3b4e7f922946747efbe164d3
readonly CANDIDATE_IMAGE_SHA256=695eff12f7fb3b210b2d9814cc1cf0ea2250d1e8277bb552fb695c87782a1a4b
readonly CANDIDATE_IMAGE_GZ_SHA256=7f9421e41eca296cc757c18c7cce0203fb53bbe9b5afa9eb890314a5ce1dea69
readonly CANDIDATE_CONFIG_SHA256=0759fdb25abf25008ecf967736316a2d16d227c80c6835dad5875e8a612ef424

workdir="$(mktemp -d)"
cleanup() {
	rm -rf -- "$workdir"
}
trap cleanup EXIT

run_validator() {
	local baseline=$1
	local candidate=$2
	python3 "$validator" \
		--baseline-package "$baseline" \
		--candidate-package "$candidate" \
		--current-manifest "$manifest" \
		--rotation-fragment "$rotation_fragment" \
		--expected-baseline-image-sha256 "$BASELINE_IMAGE_SHA256" \
		--expected-baseline-image-gz-sha256 "$BASELINE_IMAGE_GZ_SHA256" \
		--expected-candidate-image-sha256 "$CANDIDATE_IMAGE_SHA256" \
		--expected-candidate-image-gz-sha256 "$CANDIDATE_IMAGE_GZ_SHA256" \
		--expected-candidate-config-sha256 "$CANDIDATE_CONFIG_SHA256"
}

expect_reject() {
	local label=$1
	local expected=$2
	shift 2
	if "$@" >"${workdir}/${label}.out" 2>"${workdir}/${label}.err"; then
		die "validator accepted the ${label} mutation"
	fi
	grep -Fq -- "$expected" "${workdir}/${label}.err" || {
		cat "${workdir}/${label}.err" >&2
		die "${label} was rejected for an unexpected reason; wanted: $expected"
	}
}

replace_exact() {
	local path=$1
	local old=$2
	local new=$3
	python3 -c '
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
old = sys.argv[2]
new = sys.argv[3]
data = path.read_text(encoding="utf-8")
if data.count(old) != 1:
    raise SystemExit(f"expected exactly one mutation target in {path}")
path.write_text(data.replace(old, new, 1), encoding="utf-8")
' "$path" "$old" "$new"
}

mutate_last_byte() {
	local path=$1
	python3 -c '
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data = bytearray(path.read_bytes())
if not data:
    raise SystemExit(f"cannot mutate empty file: {path}")
data[-1] ^= 1
path.write_bytes(data)
' "$path"
}

mutated_candidate="${workdir}/candidate"
mutated_baseline="${workdir}/baseline"

fresh_candidate() {
	rm -rf -- "$mutated_candidate"
	cp -a -- "$candidate_package" "$mutated_candidate"
}

fresh_pair() {
	rm -rf -- "$mutated_baseline" "$mutated_candidate"
	cp -a -- "$baseline_package" "$mutated_baseline"
	cp -a -- "$candidate_package" "$mutated_candidate"
}

run_validator "$baseline_package" "$candidate_package" >"${workdir}/positive.out"
grep -Fqx 'validation=observability-fbcon-rotation-package-delta' \
	"${workdir}/positive.out" || die "positive validation emitted the wrong identity"
grep -Fqx 'two_resolved_config_deltas=passed' "${workdir}/positive.out" || \
	die "positive validation did not prove the exact two-line delta"
grep -Fqx 'hardware_write=none' "${workdir}/positive.out" || \
	die "positive validation did not preserve the no-hardware boundary"

fresh_candidate
replace_exact "${mutated_candidate}/kernel.config" \
	'CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=y' \
	'# CONFIG_FRAMEBUFFER_CONSOLE_ROTATION is not set'
expect_reject omitted_rotation_config 'resolved config has 1 differing lines' \
	run_validator "$baseline_package" "$mutated_candidate"

fresh_candidate
replace_exact "${mutated_candidate}/kernel.config" \
	'CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=y' \
	'CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=m'
expect_reject wrong_rotation_config \
	'resolved config delta is not exact rotation plus command-line append' \
	run_validator "$baseline_package" "$mutated_candidate"

fresh_candidate
replace_exact "${mutated_candidate}/kernel.config" \
	' fbcon=rotate:3"' ' fbcon=rotate:1"'
expect_reject wrong_fbcon_rotate_value \
	'resolved config delta is not exact rotation plus command-line append' \
	run_validator "$baseline_package" "$mutated_candidate"

fresh_candidate
replace_exact "${mutated_candidate}/kernel.config" \
	' fbcon=rotate:3"' '"'
expect_reject omitted_fbcon_cmdline_token \
	'resolved config has 1 differing lines' \
	run_validator "$baseline_package" "$mutated_candidate"

fresh_candidate
replace_exact "${mutated_candidate}/kernel.config" \
	'CONFIG_CMDLINE_FORCE=y' '# CONFIG_CMDLINE_FORCE is not set'
expect_reject extra_resolved_config_change \
	'resolved config has 3 differing lines' \
	run_validator "$baseline_package" "$mutated_candidate"

fresh_pair
replace_exact "${mutated_baseline}/kernel.config" \
	'CONFIG_FONT_8x16=y' '# CONFIG_FONT_8x16 is not set'
replace_exact "${mutated_candidate}/kernel.config" \
	'CONFIG_FONT_8x16=y' '# CONFIG_FONT_8x16 is not set'
expect_reject font_8x16_change \
	'required unchanged config line is missing: CONFIG_FONT_8x16=y' \
	run_validator "$mutated_baseline" "$mutated_candidate"

fresh_pair
replace_exact "${mutated_baseline}/kernel.config" \
	'CONFIG_LOCALVERSION="-gemini-observability-L"' \
	'CONFIG_LOCALVERSION="-gemini-observability-P-mutation"'
replace_exact "${mutated_candidate}/kernel.config" \
	'CONFIG_LOCALVERSION="-gemini-observability-L"' \
	'CONFIG_LOCALVERSION="-gemini-observability-P-mutation"'
expect_reject localversion_change \
	'required unchanged config line is missing: CONFIG_LOCALVERSION="-gemini-observability-L"' \
	run_validator "$mutated_baseline" "$mutated_candidate"

fresh_candidate
replace_exact \
	"${mutated_candidate}/provenance/configs/gemini-fbcon-rotation.fragment" \
	'fbcon=rotate:3' 'fbcon=rotate:1'
expect_reject packaged_rotation_fragment_mutation \
	'candidate fbcon-rotation fragment is not exact' \
	run_validator "$baseline_package" "$mutated_candidate"

fresh_candidate
mutate_last_byte \
	"${mutated_candidate}/dtbs/mediatek/mt6797-gemini-pda.dtb"
expect_reject dtb_mutation \
	'DTB tree changed despite config-only kernel delta' \
	run_validator "$baseline_package" "$mutated_candidate"

printf 'validation=candidate-p-package-validator-mutation-regression\n'
printf 'positive_package_delta=passed\n'
printf 'omitted_rotation_config=rejected\n'
printf 'wrong_rotation_config=rejected\n'
printf 'wrong_fbcon_rotate_value=rejected\n'
printf 'omitted_fbcon_cmdline_token=rejected\n'
printf 'extra_resolved_config_change=rejected\n'
printf 'font_8x16_change=rejected\n'
printf 'localversion_change=rejected\n'
printf 'packaged_rotation_fragment_mutation=rejected\n'
printf 'dtb_mutation=rejected\n'
printf 'temporary_mutations_only=yes\n'
printf 'hardware_write=none\n'
