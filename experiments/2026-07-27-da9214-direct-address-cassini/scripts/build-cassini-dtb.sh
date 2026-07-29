#!/usr/bin/env bash

# Derive exact AO plus only the access-controlled, childless I2C6 adapter.
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --ao-dtb FILE --output FILE\n' "$0" >&2; }
ao_dtb=
output=
while (($#)); do
	case "$1" in
	--ao-dtb|--output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--ao-dtb) ao_dtb=$2 ;;
		--output) output=$2 ;;
		esac
		shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$ao_dtb" && -n "$output" ]] || { usage; exit 2; }
for command in awk dirname fdtget fdtput install mktemp mv python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command missing: $command"
done
[[ -f "$ao_dtb" && ! -L "$ao_dtb" && -s "$ao_dtb" ]] ||
	die 'Candidate AO DT is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] ||
	die 'refusing to overwrite output DT'
output_parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
validator="$script_dir/validate-cassini-dtb.py"
[[ -f "$validator" && ! -L "$validator" && -s "$validator" ]] ||
	die 'Cassini DT validator is missing or unsafe'

readonly AO_DTB_SHA256=de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7
readonly I2C6=/i2c@1100e000
readonly HANDOFF=/dvfsp-handoff@11015000
readonly HANDOFF_PHANDLE=0x2c
readonly DEPENDENCY_PROPERTY=access-controllers
readonly ACCESS_CELLS_PROPERTY='#access-controller-cells'

[[ "$(sha256sum "$ao_dtb" | awk '{print $1}')" == "$AO_DTB_SHA256" ]] ||
	die 'exact Candidate AO DT changed'
[[ "$(fdtget -t s "$ao_dtb" "$I2C6" status)" == disabled ]] ||
	die 'Candidate AO I2C6 boundary changed'
[[ "$(fdtget -t s "$ao_dtb" "$HANDOFF" status)" == okay ]] ||
	die 'Candidate AO handoff supplier is not enabled'
[[ -z "$(fdtget -l "$ao_dtb" "$I2C6")" ]] ||
	die 'Candidate AO I2C6 is not childless'

temporary="$(mktemp "$output_parent/.cassini-dtb.XXXXXX")"
cleanup() { [[ ! -f "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT
install -m 0600 "$ao_dtb" "$temporary"
fdtput -t x "$temporary" "$HANDOFF" "$ACCESS_CELLS_PROPERTY" 0
fdtput -t x "$temporary" "$HANDOFF" phandle "$HANDOFF_PHANDLE"
fdtput -t x "$temporary" "$I2C6" "$DEPENDENCY_PROPERTY" "$HANDOFF_PHANDLE"
fdtput -t s "$temporary" "$I2C6" status okay
python3 "$validator" --ao "$ao_dtb" --candidate "$temporary"
built_sha256="$(sha256sum "$temporary" | awk '{print $1}')"
chmod 0600 "$temporary"
mv --no-clobber --no-target-directory "$temporary" "$output"
temporary=
trap - EXIT

printf 'validation=cassini-childless-i2c6-dtb-built\n'
printf 'sha256=%s\n' "$built_sha256"
printf 'baseline=exact-candidate-ao\n'
printf 'i2c6=enabled-childless\ni2c6_clients=0\n'
printf 'da9214_a72_nodes=absent\ncpu8_cpu9=fail-closed\n'
printf 'device_access=none\nstorage_access=none\n'
