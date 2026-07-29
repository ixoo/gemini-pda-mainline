#!/usr/bin/env bash

set -euo pipefail

die() {
	echo "error: $*" >&2
	exit 1
}

usage() {
	echo "Usage: $0 --gate3-dtb FILE --output FILE"
}

gate3_dtb=
output=
while [[ "$#" -gt 0 ]]; do
	case "$1" in
	--gate3-dtb) gate3_dtb="${2:-}"; shift 2 ;;
	--output) output="${2:-}"; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$gate3_dtb" && -n "$output" ]] || {
	usage >&2
	exit 2
}
for command in awk dirname fdtget fdtput install mkdir mktemp rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command not found: $command"
done
[[ -f "$gate3_dtb" && ! -L "$gate3_dtb" && -s "$gate3_dtb" ]] ||
	die "missing, empty, or unsafe Gate 3 DT"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mkdir -p -- "$(dirname -- "$output")"

readonly GATE3_DTB_SHA256=7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806
readonly CHILD=/i2c@1100e000/regulator@68
[[ "$(sha256sum "$gate3_dtb" | awk '{print $1}')" == "$GATE3_DTB_SHA256" ]] ||
	die "Gate 3 DT baseline changed"
[[ "$(fdtget -ts "$gate3_dtb" "$CHILD" compatible)" == "dlg,da9214-legacy" ]] ||
	die "Gate 3 child compatible changed"
[[ "$(fdtget -tx "$gate3_dtb" "$CHILD" reg)" == "68 69" ]] ||
	die "Gate 3 child address tuple changed"
[[ "$(fdtget -ts "$gate3_dtb" "$CHILD" reg-names)" == "primary page2" ]] ||
	die "Gate 3 child tuple names changed"
if fdtget -ts "$gate3_dtb" "$CHILD" status >/dev/null 2>&1; then
	die "Gate 3 child unexpectedly already has status"
fi

temporary="$(mktemp "$(dirname -- "$output")/.probe-isolation-dtb.XXXXXX")"
cleanup() { rm -f -- "${temporary:-}"; }
trap cleanup EXIT
install -m 0600 "$gate3_dtb" "$temporary"
fdtput -t s "$temporary" "$CHILD" status disabled

[[ "$(fdtget -ts "$temporary" "$CHILD" status)" == "disabled" ]] ||
	die "derived child is not disabled"
[[ "$(fdtget -ts "$temporary" "$CHILD" compatible)" == "dlg,da9214-legacy" ]] ||
	die "derived child compatible changed"
[[ "$(fdtget -tx "$temporary" "$CHILD" reg)" == "68 69" ]] ||
	die "derived child address tuple changed"
[[ "$(fdtget -ts "$temporary" "$CHILD" reg-names)" == "primary page2" ]] ||
	die "derived child tuple names changed"
[[ "$(sha256sum "$gate3_dtb" | awk '{print $1}')" == "$GATE3_DTB_SHA256" ]] ||
	die "Gate 3 DT input changed during derivation"

install -m 0600 "$temporary" "$output"
printf 'validation=da921x-probe-isolation-dtb\n'
printf 'gate3_dtb_sha256=%s\n' "$GATE3_DTB_SHA256"
printf 'output_dtb_sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'sole_semantic_delta=%s-status-disabled\n' "$CHILD"
printf 'automatic_da921x_probe=prevented\n'
printf 'provider=absent\n'
printf 'a72_request=absent\n'
