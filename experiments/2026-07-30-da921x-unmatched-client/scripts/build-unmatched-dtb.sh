#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { echo "usage: $0 --gate3-dtb FILE --output FILE"; }
gate3_dtb=
output=
while (($#)); do
	case "$1" in
	--gate3-dtb) gate3_dtb=${2:-}; shift 2 ;;
	--output) output=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage >&2; die "unknown argument: $1" ;;
	esac
done
[[ -n "$gate3_dtb" && -n "$output" ]] || { usage >&2; exit 2; }
for command in awk dirname fdtget fdtput install mkdir mktemp rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command missing: $command"
done
[[ -f "$gate3_dtb" && ! -L "$gate3_dtb" && -s "$gate3_dtb" ]] ||
	die 'enabled input DT is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mkdir -p -- "$(dirname -- "$output")"

readonly INPUT_DTB_SHA256=7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806
readonly CHILD=/i2c@1100e000/regulator@68
readonly INPUT_COMPATIBLE=dlg,da9214-legacy
readonly OUTPUT_COMPATIBLE=dlg,da9214-unbound
[[ "$(sha256sum "$gate3_dtb" | awk '{print $1}')" == "$INPUT_DTB_SHA256" ]] ||
	die 'enabled input DT changed'
[[ "$(fdtget -ts "$gate3_dtb" "$CHILD" compatible)" == "$INPUT_COMPATIBLE" ]] ||
	die 'input compatible changed'
[[ "$(fdtget -tx "$gate3_dtb" "$CHILD" reg)" == "68 69" ]] ||
	die 'input address tuple changed'
[[ "$(fdtget -ts "$gate3_dtb" "$CHILD" reg-names)" == "primary page2" ]] ||
	die 'input tuple names changed'
if fdtget -ts "$gate3_dtb" "$CHILD" status >/dev/null 2>&1; then
	die 'enabled input unexpectedly has a status property'
fi

temporary="$(mktemp "$(dirname -- "$output")/.unmatched-client-dtb.XXXXXX")"
# ShellCheck cannot infer that this function is invoked by the EXIT trap.
# shellcheck disable=SC2317
cleanup() { rm -f -- "${temporary:-}"; }
trap cleanup EXIT
install -m 0600 "$gate3_dtb" "$temporary"
fdtput -t s "$temporary" "$CHILD" compatible "$OUTPUT_COMPATIBLE"
[[ "$(fdtget -ts "$temporary" "$CHILD" compatible)" == "$OUTPUT_COMPATIBLE" ]] ||
	die 'diagnostic compatible was not installed'
[[ "$(fdtget -tx "$temporary" "$CHILD" reg)" == "68 69" ]] ||
	die 'derived address tuple changed'
[[ "$(fdtget -ts "$temporary" "$CHILD" reg-names)" == "primary page2" ]] ||
	die 'derived tuple names changed'
if fdtget -ts "$temporary" "$CHILD" status >/dev/null 2>&1; then
	die 'derived enabled child unexpectedly has a status property'
fi
[[ "$(sha256sum "$gate3_dtb" | awk '{print $1}')" == "$INPUT_DTB_SHA256" ]] ||
	die 'input DT changed during derivation'
install -m 0600 "$temporary" "$output"
printf 'validation=da921x-unmatched-compatible-dtb\n'
printf 'input_dtb_sha256=%s\n' "$INPUT_DTB_SHA256"
printf 'output_dtb_sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'sole_semantic_delta=%s-compatible-%s-to-%s\n' \
	"$CHILD" "$INPUT_COMPATIBLE" "$OUTPUT_COMPATIBLE"
printf 'driver_match=none\nmodule_load=forbidden\n'
