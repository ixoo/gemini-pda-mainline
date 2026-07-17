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
usage: build-observability-dtb.sh --base DTB --output DTB

Derive Candidate L's LK-compatible DTB from an explicit observability-profile
Gemini DTB. The mandatory LK, USB gadget, simplefb, DISP_PWM and MM-root
transformations are reused from their independently validated builders. This
command has no device or flashing interface.
EOF
}

base=
output=
while (($#)); do
	case "$1" in
		--base)
			(($# >= 2)) || die "--base requires DTB"
			base=$2
			shift 2
			;;
		--output)
			(($# >= 2)) || die "--output requires DTB"
			output=$2
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

[[ -n "$base" ]] || die "--base is required"
[[ -n "$output" ]] || die "--output is required"
[[ -s "$base" ]] || die "base DTB is missing or empty: $base"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
for command in awk cat dirname install mkdir mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
screen_builder="${repo_root}/experiments/2026-07-16-screen-marker-diagnostic/scripts/build-screen-marker-dtb.sh"
clock_builder="${repo_root}/experiments/2026-07-16-screen-clock-retention-diagnostic/scripts/build-clock-retention-dtb.sh"
mm_builder="${repo_root}/experiments/2026-07-16-simplefb-mm-root-retention/scripts/build-mm-root-dtb.sh"
validator="${script_dir}/validate-observability-dtb.py"
mandatory_overlay="${repo_root}/experiments/2026-07-16-lk-handoff-alignment/dts/lk-handoff.dtso"
usb_overlay="${repo_root}/experiments/2026-07-16-usb-gadget-diagnostic/dts/usb-gadget.dtso"
simplefb_overlay="${repo_root}/experiments/2026-07-16-lk-handoff-alignment/dts/lk-simplefb.dtso"
lk_validator="${repo_root}/experiments/2026-07-16-lk-handoff-alignment/scripts/validate-lk-compatible-dtb.py"
clock_validator="${repo_root}/experiments/2026-07-16-screen-clock-retention-diagnostic/scripts/validate-simplefb-clock-delta.py"
mm_validator="${repo_root}/experiments/2026-07-16-simplefb-mm-root-retention/scripts/validate-simplefb-mm-root-delta.py"
inputs=(
	"$screen_builder"
	"$clock_builder"
	"$mm_builder"
	"$validator"
	"$mandatory_overlay"
	"$usb_overlay"
	"$simplefb_overlay"
	"$lk_validator"
	"$clock_validator"
	"$mm_validator"
)
for input in "${inputs[@]}"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-observability-dtb.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

screen_dtb="${workdir}/screen.dtb"
clock_dtb="${workdir}/screen-clock.dtb"
final_dtb="${workdir}/observability.dtb"
"$screen_builder" --base "$base" --output "$screen_dtb" \
	>"${workdir}/screen-validation.txt"
"$clock_builder" --baseline "$screen_dtb" --output "$clock_dtb" \
	>"${workdir}/clock-validation.txt"
"$mm_builder" --baseline "$clock_dtb" --output "$final_dtb" \
	>"${workdir}/mm-validation.txt"
python3 "$validator" --base "$base" --candidate "$final_dtb" \
	>"${workdir}/observability-validation.txt"

mkdir -p "$(dirname -- "$output")"
install -m 0600 "$final_dtb" "$output"
cat "${workdir}/observability-validation.txt"
printf 'output=%s\n' "$output"
printf 'base_sha256=%s\n' "$(sha256sum "$base" | awk '{print $1}')"
printf 'output_sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'transformation_chain=mandatory-lk,usb-gadget,simplefb,DISP_PWM,MM-root\n'
for input in "${inputs[@]}"; do
	printf 'input_sha256[%s]=%s\n' \
		"${input#"$repo_root"/}" "$(sha256sum "$input" | awk '{print $1}')"
done
printf 'build_hardware_write=none\nflash=none\n'
