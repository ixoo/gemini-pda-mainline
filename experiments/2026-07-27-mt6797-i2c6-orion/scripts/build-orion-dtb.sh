#!/usr/bin/env bash

# Derive exact Hubble plus only Orion's standalone I2C6 compatible.
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --hubble-dtb FILE --output FILE\n' "$0" >&2; }
hubble_dtb=
output=
while (($#)); do
	case "$1" in
	--hubble-dtb|--output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--hubble-dtb) hubble_dtb=$2 ;;
		--output) output=$2 ;;
		esac
		shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$hubble_dtb" && -n "$output" ]] || { usage; exit 2; }
for command in awk dirname fdtget fdtput install mktemp mv python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command missing: $command"
done
[[ -f "$hubble_dtb" && ! -L "$hubble_dtb" && -s "$hubble_dtb" ]] ||
	die 'Candidate Hubble DT is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] ||
	die 'refusing to overwrite output DT'
output_parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
validator="$script_dir/validate-orion-dtb.py"
[[ -f "$validator" && ! -L "$validator" && -s "$validator" ]] ||
	die 'Orion DT validator is missing or unsafe'

readonly HUBBLE_DTB_SHA256=8faee2918ce72b08907affa73bfbaf1c5bbbffafde0f4f4c2693977468291768
readonly I2C6=/i2c@1100e000
readonly SPECIAL=mediatek,mt6797-idvfs-i2c

[[ "$(sha256sum "$hubble_dtb" | awk '{print $1}')" == \
	"$HUBBLE_DTB_SHA256" ]] || die 'exact Candidate Hubble DT changed'
[[ "$(fdtget -t s "$hubble_dtb" "$I2C6" status)" == okay ]] ||
	die 'Candidate Hubble I2C6 is not enabled'
[[ "$(fdtget -t s "$hubble_dtb" "$I2C6" compatible)" == \
	"mediatek,mt6797-i2c mediatek,mt6577-i2c" ]] ||
	die 'Candidate Hubble I2C6 compatible changed'
[[ -z "$(fdtget -l "$hubble_dtb" "$I2C6")" ]] ||
	die 'Candidate Hubble I2C6 is not childless'

temporary="$(mktemp "$output_parent/.orion-dtb.XXXXXX")"
cleanup() { [[ ! -f "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT
install -m 0600 "$hubble_dtb" "$temporary"
fdtput -t s "$temporary" "$I2C6" compatible "$SPECIAL"
python3 "$validator" --hubble "$hubble_dtb" --candidate "$temporary"
built_sha256="$(sha256sum "$temporary" | awk '{print $1}')"
chmod 0600 "$temporary"
mv --no-clobber --no-target-directory "$temporary" "$output"
temporary=
trap - EXIT

printf 'validation=orion-dtb-built\n'
printf 'sha256=%s\n' "$built_sha256"
printf 'baseline=exact-candidate-hubble\n'
printf 'changed_property=/i2c@1100e000:compatible\n'
printf 'i2c6_compatible=%s\n' "$SPECIAL"
printf 'i2c6=enabled-childless\n'
printf 'da9214_a72_nodes=absent\ncpu8_cpu9=fail-closed\n'
printf 'device_access=none\nstorage_access=none\n'
