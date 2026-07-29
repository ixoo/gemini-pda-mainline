#!/usr/bin/env bash

set -euo pipefail

die() {
	echo "error: $*" >&2
	exit 1
}

usage() {
	echo "Usage: $0 --gauss-dtb FILE --compiled-dtb FILE --output FILE"
}

gauss_dtb=
compiled_dtb=
output=
while [[ "$#" -gt 0 ]]; do
	case "$1" in
	--gauss-dtb) gauss_dtb="${2:-}"; shift 2 ;;
	--compiled-dtb) compiled_dtb="${2:-}"; shift 2 ;;
	--output) output="${2:-}"; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done

[[ -n "$gauss_dtb" && -n "$compiled_dtb" && -n "$output" ]] || {
	usage >&2
	exit 2
}
for command in awk dirname fdtget fdtput install mkdir mktemp rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done
for input in "$gauss_dtb" "$compiled_dtb"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "missing, empty, or unsafe input: $input"
done
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mkdir -p -- "$(dirname -- "$output")"

readonly GAUSS_DTB_SHA256=e189b4741806432af456a2f9a4aa7e250f3e629dcad41726bf221bf2611ccae7
readonly I2C6=/i2c@1100e000
readonly I2C6_PINS=/pinctrl@10005000/i2c6-pins
readonly DA9214="$I2C6/regulator@68"
[[ "$(sha256sum "$gauss_dtb" | awk '{print $1}')" == "$GAUSS_DTB_SHA256" ]] ||
	die "Gauss boot-DT baseline changed"

[[ "$(fdtget -ts "$compiled_dtb" "$DA9214" compatible)" == "dlg,da9214-legacy" ]] ||
	die "compiled lifecycle DT lacks the legacy-only DA9214 node"
[[ "$(fdtget -tx "$compiled_dtb" "$DA9214" reg)" == "68 69" ]] ||
	die "compiled lifecycle DT changed the fixed direct-address tuple"
[[ "$(fdtget -ts "$compiled_dtb" "$DA9214" reg-names)" == "primary page2" ]] ||
	die "compiled lifecycle DT changed the tuple names"

temporary="$(mktemp "$(dirname -- "$output")/.lifecycle-dtb.XXXXXX")"
cleanup() { rm -f -- "${temporary:-}"; }
trap cleanup EXIT
install -m 0600 "$gauss_dtb" "$temporary"

# 0x2c remains the established DVFSP handoff phandle in the Gauss DT.
# 0x2d is unused there and is assigned only to the existing I2C6 pin group.
[[ "$(fdtget -tx "$temporary" "$I2C6" access-controllers)" == "2c" ]] ||
	die "Gauss I2C6 handoff dependency changed"
if fdtget -tx "$temporary" "$I2C6_PINS" phandle >/dev/null 2>&1; then
	die "Gauss I2C6 pin group unexpectedly already has a phandle"
fi
fdtput -t x "$temporary" "$I2C6_PINS" phandle 0x2d
fdtput -t x "$temporary" "$I2C6" clock-frequency 0x33e140
fdtput -t x "$temporary" "$I2C6" mediatek,use-push-pull
fdtput -t s "$temporary" "$I2C6" pinctrl-names default
fdtput -t x "$temporary" "$I2C6" pinctrl-0 0x2d
fdtput -c "$temporary" "$DA9214"
fdtput -t s "$temporary" "$DA9214" compatible dlg,da9214-legacy
fdtput -t x "$temporary" "$DA9214" reg 0x68 0x69
fdtput -t s "$temporary" "$DA9214" reg-names primary page2

[[ "$(fdtget -tx "$temporary" "$I2C6" clock-frequency)" == "33e140" ]] ||
	die "final I2C6 clock changed"
[[ "$(fdtget -tx "$temporary" "$I2C6" pinctrl-0)" == "2d" ]] ||
	die "final I2C6 pinctrl reference changed"
[[ "$(fdtget -ts "$temporary" "$DA9214" compatible)" == "dlg,da9214-legacy" ]] ||
	die "final DA9214 compatible changed"
[[ "$(fdtget -tx "$temporary" "$DA9214" reg)" == "68 69" ]] ||
	die "final DA9214 tuple changed"
[[ "$(fdtget -ts "$temporary" "$DA9214" reg-names)" == "primary page2" ]] ||
	die "final DA9214 tuple names changed"

install -m 0600 "$temporary" "$output"
printf 'validation=gate3-lifecycle-dtb\n'
printf 'gauss_dtb_sha256=%s\n' "$GAUSS_DTB_SHA256"
printf 'output_dtb_sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'i2c6_access_controller=0x2c\n'
printf 'i2c6_pinctrl_phandle=0x2d\n'
printf 'da9214_tuple=0x68,0x69\n'
printf 'regulator_provider=absent\n'
printf 'a72_consumer=absent\n'
