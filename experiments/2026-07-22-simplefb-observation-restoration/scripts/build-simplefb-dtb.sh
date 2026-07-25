#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --af-dtb FILE --ad-dtb FILE --output FILE\n' "$0" >&2
}

af_dtb=
ad_dtb=
output=
while (($#)); do
	case "$1" in
	--af-dtb|--ad-dtb|--output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--af-dtb) af_dtb=$2 ;;
		--ad-dtb) ad_dtb=$2 ;;
		--output) output=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$af_dtb" && -n "$ad_dtb" && -n "$output" ]] || { usage; exit 2; }
for command in awk chmod dirname fdtget fdtput install mkdir mktemp mv \
	python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
for input in "$af_dtb" "$ad_dtb"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || \
		die "input DTB is missing, empty, or unsafe: $input"
done
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output DTB'
output_parent="$(dirname -- "$output")"
[[ -d "$output_parent" && ! -L "$output_parent" ]] || die 'output parent is unsafe'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
validator="$script_dir/validate-dtb-delta.py"
[[ -f "$validator" && ! -L "$validator" && -s "$validator" ]] || \
	die 'DT semantic validator is missing or unsafe'

readonly AF_DTB_SHA256=3f9e6d977ca1c8060ad4170bdca12eed3d40b112009b8ad93b4a08017221643b
readonly AD_DTB_SHA256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
[[ "$(sha256sum "$af_dtb" | awk '{ print $1 }')" == "$AF_DTB_SHA256" ]] || \
	die 'exact Candidate AF DTB changed'
[[ "$(sha256sum "$ad_dtb" | awk '{ print $1 }')" == "$AD_DTB_SHA256" ]] || \
	die 'exact hardware-passed Candidate AD DTB changed'

provider_phandle() {
	local dtb=$1 path=$2 compatible=$3 actual cells phandle
	actual="$(fdtget -t s "$dtb" "$path" compatible)"
	[[ "$actual" == "$compatible" ]] || die "clock provider compatible differs: $path"
	cells="$(fdtget -t x "$dtb" "$path" '#clock-cells')"
	[[ "$cells" == 1 ]] || die "clock provider cell count differs: $path"
	phandle="$(fdtget -t x "$dtb" "$path" phandle)"
	[[ "$phandle" =~ ^[1-9a-f][0-9a-f]*$ ]] || die "clock provider phandle is invalid: $path"
	printf '%s\n' "$phandle"
}

infra_phandle="$(provider_phandle "$af_dtb" /syscon@10001000 \
	'mediatek,mt6797-infracfg syscon')"
top_phandle="$(provider_phandle "$af_dtb" /topckgen@10000000 \
	'mediatek,mt6797-topckgen')"

temporary="$(mktemp "$output_parent/.candidate-ag-simplefb.XXXXXX")"
cleanup() { [[ ! -f "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT
install -m 0600 "$af_dtb" "$temporary"

fdtput -t x "$temporary" /chosen '#address-cells' 2
fdtput -t x "$temporary" /chosen '#size-cells' 2
fdtput -t x "$temporary" /chosen ranges
framebuffer=/chosen/framebuffer@7dfb0000
fdtput -p -t s "$temporary" "$framebuffer" compatible simple-framebuffer
fdtput -t x "$temporary" "$framebuffer" reg 0 7dfb0000 0 1f90000
fdtput -t x "$temporary" "$framebuffer" width 438
fdtput -t x "$temporary" "$framebuffer" height 870
fdtput -t x "$temporary" "$framebuffer" stride 1100
fdtput -t s "$temporary" "$framebuffer" format a8r8g8b8
fdtput -t x "$temporary" "$framebuffer" clocks \
	"$infra_phandle" 2d "$top_phandle" 6

python3 "$validator" --af "$af_dtb" --ad "$ad_dtb" --candidate "$temporary"
built_sha256="$(sha256sum "$temporary" | awk '{ print $1 }')"
[[ "$built_sha256" == 7ea5e8f9edb09f2365a112b29359fed897f306422a26449b1cb8870bb1212512 ]] || \
	die 'DTB serialization differs from the reproduced exact Candidate AG transform'
chmod 0600 "$temporary"
mv -n "$temporary" "$output"
[[ -f "$output" && ! -L "$output" && ! -e "$temporary" ]] || \
	die 'exclusive DTB publication failed'
temporary=
trap - EXIT
printf 'validation=candidate-ag-simplefb-dtb-built\n'
printf 'output=%s\n' "$output"
printf 'sha256=%s\n' "$built_sha256"
printf 'framebuffer_write=none\ndevice_access=none\n'
