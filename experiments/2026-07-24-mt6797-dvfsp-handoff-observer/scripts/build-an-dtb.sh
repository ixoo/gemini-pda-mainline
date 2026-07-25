#!/usr/bin/env bash

# Deterministically add one read-only DVFSP handoff-observer node to the exact
# hardware-passed Candidate AH final DT. This script never accesses a device.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --ah-dtb FILE --output FILE\n' "$0" >&2; }

ah_dtb=
output=
while (($#)); do
	case "$1" in
	--ah-dtb|--output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--ah-dtb) ah_dtb=$2 ;;
		--output) output=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$ah_dtb" && -n "$output" ]] || { usage; exit 2; }

for command in awk chmod dirname fdtget fdtput install mktemp mv python3 rm \
	sha256sum; do
	command -v "$command" >/dev/null 2>&1 || \
		die "required command missing: $command"
done

[[ -f "$ah_dtb" && ! -L "$ah_dtb" && -s "$ah_dtb" ]] || \
	die 'Candidate AH DT is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || \
	die 'refusing to overwrite output DT'
output_parent="$(dirname -- "$output")"
[[ -d "$output_parent" && ! -L "$output_parent" ]] || \
	die 'output parent is unsafe'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
validator="$script_dir/validate-dtb-delta.py"
[[ -f "$validator" && ! -L "$validator" && -s "$validator" ]] || \
	die 'Candidate AN DT validator is missing or unsafe'

readonly AH_DTB_SHA256=27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845
readonly INFRACFG=/syscon@10001000
readonly I2C6=/i2c@1100e000
readonly DA9214=$I2C6/regulator@68
readonly A72_POWER=/a72-power@10222000
readonly LEGACY_DVFSP=/dvfsp@11015000
readonly OBSERVER=/dvfsp-observer@11015000

[[ "$(sha256sum "$ah_dtb" | awk '{ print $1 }')" == "$AH_DTB_SHA256" ]] || \
	die 'exact hardware-passed Candidate AH DT changed'
[[ "$(fdtget -t s "$ah_dtb" "$I2C6" status)" == disabled ]] || \
	die 'Candidate AH I2C6 boundary changed'
for forbidden in "$DA9214" "$A72_POWER" "$LEGACY_DVFSP" "$OBSERVER"; do
	if fdtget -p "$ah_dtb" "$forbidden" >/dev/null 2>&1; then
		die "Candidate AH unexpectedly contains $forbidden"
	fi
done

[[ "$(fdtget -t s "$ah_dtb" "$INFRACFG" compatible)" == \
	"mediatek,mt6797-infracfg syscon" ]] || \
	die 'Candidate AH infracfg identity changed'
infracfg_phandle="$(fdtget -t x "$ah_dtb" "$INFRACFG" phandle)"
[[ "$infracfg_phandle" == 3 ]] || \
	die 'Candidate AH infracfg phandle changed'

temporary="$(mktemp "$output_parent/.candidate-an-dtb.XXXXXX")"
cleanup() { [[ ! -f "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT
install -m 0600 "$ah_dtb" "$temporary"

fdtput -c "$temporary" "$OBSERVER"
fdtput -t s "$temporary" "$OBSERVER" compatible \
	mediatek,mt6797-dvfsp-handoff-observer
fdtput -t x "$temporary" "$OBSERVER" reg 0 0x11015000 0 0x1000
fdtput -t x "$temporary" "$OBSERVER" mediatek,infracfg \
	"$infracfg_phandle"
fdtput -t s "$temporary" "$OBSERVER" status okay

python3 "$validator" --ah "$ah_dtb" --candidate "$temporary"
built_sha256="$(sha256sum "$temporary" | awk '{ print $1 }')"
chmod 0600 "$temporary"
mv -n "$temporary" "$output"
[[ -f "$output" && ! -L "$output" && ! -e "$temporary" ]] || \
	die 'exclusive Candidate AN DT publication failed'
temporary=
trap - EXIT

printf 'validation=candidate-an-dtb-built\n'
printf 'output=%s\nsha256=%s\n' "$output" "$built_sha256"
printf 'baseline=exact-hardware-passed-candidate-ah-final-dtb\n'
printf 'added_node=%s\n' "$OBSERVER"
printf 'added_nodes=1\nadded_properties=4\nchanged_existing_nodes=0\n'
printf 'infracfg_path=%s\ninfracfg_phandle=0x%s\n' \
	"$INFRACFG" "$infracfg_phandle"
printf 'i2c6=disabled\nda9214_node=absent\na72_power_node=absent\n'
printf 'device_access=none\nstorage_access=none\n'
