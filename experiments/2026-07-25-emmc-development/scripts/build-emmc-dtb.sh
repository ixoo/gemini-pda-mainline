#!/usr/bin/env bash

# Deterministically enable the MT6797 I2C6 controller on exact Candidate AO,
# link it to AO's validated one-way handoff access controller, and add only the
# exact legacy DA9214 read-only probe contract. No A72 consumer or rail policy
# is introduced.

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
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$ao_dtb" && -n "$output" ]] || { usage; exit 2; }

for command in awk chmod dirname fdtget fdtput install mktemp mv python3 rm \
	sha256sum; do
	command -v "$command" >/dev/null 2>&1 || \
		die "required command missing: $command"
done

[[ -f "$ao_dtb" && ! -L "$ao_dtb" && -s "$ao_dtb" ]] || \
	die 'Candidate AO DT is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || \
	die 'refusing to overwrite output DT'
output_parent="$(dirname -- "$output")"
[[ -d "$output_parent" && ! -L "$output_parent" ]] || \
	die 'output parent is unsafe'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
validator="$script_dir/validate-dtb-delta-emmc.py"
[[ -f "$validator" && ! -L "$validator" && -s "$validator" ]] || \
	die 'Candidate AT DT validator is missing or unsafe'

readonly AO_DTB_SHA256=de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7
readonly I2C6=/i2c@1100e000
readonly I2C6_PINS=/pinctrl@10005000/i2c6-pins
readonly HANDOFF=/dvfsp-handoff@11015000
readonly HANDOFF_PHANDLE=0x2c
readonly I2C6_PINS_PHANDLE=0x2d
readonly DEPENDENCY_PROPERTY=access-controllers
readonly ACCESS_CELLS_PROPERTY='#access-controller-cells'
readonly DA9214=$I2C6/regulator@68

[[ "$(sha256sum "$ao_dtb" | awk '{ print $1 }')" == "$AO_DTB_SHA256" ]] || \
	die 'exact hardware-passed Candidate AO DT changed'
[[ "$(fdtget -t s "$ao_dtb" "$I2C6" status)" == disabled ]] || \
	die 'Candidate AO I2C6 boundary changed'
[[ "$(fdtget -t s "$ao_dtb" "$HANDOFF" status)" == okay ]] || \
	die 'Candidate AO handoff supplier is not enabled'
for property in "$DEPENDENCY_PROPERTY" clock-frequency \
	mediatek,use-push-pull pinctrl-names pinctrl-0; do
	if fdtget "$ao_dtb" "$I2C6" "$property" >/dev/null 2>&1; then
		die "Candidate AO I2C6 unexpectedly contains $property"
	fi
done
if fdtget "$ao_dtb" "$HANDOFF" phandle >/dev/null 2>&1; then
	die 'Candidate AO handoff unexpectedly has a phandle'
fi
if fdtget "$ao_dtb" "$HANDOFF" "$ACCESS_CELLS_PROPERTY" >/dev/null 2>&1; then
	die "Candidate AO handoff unexpectedly has $ACCESS_CELLS_PROPERTY"
fi
if [[ -n "$(fdtget -l "$ao_dtb" "$I2C6")" ]]; then
	die 'Candidate AO I2C6 is not childless'
fi

temporary="$(mktemp "$output_parent/.candidate-at-dtb.XXXXXX")"
cleanup() { [[ ! -f "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT
install -m 0600 "$ao_dtb" "$temporary"

# AO has the exact contiguous phandle allocation 0x01..0x2b. AT adds the
# handoff access-controller declaration/phandle, the I2C6 pin-group phandle,
# and the exact legacy DA9214 read-only probe contract.
fdtput -t x "$temporary" "$HANDOFF" "$ACCESS_CELLS_PROPERTY" 0
fdtput -t x "$temporary" "$HANDOFF" phandle "$HANDOFF_PHANDLE"
fdtput -t x "$temporary" "$I2C6_PINS" phandle "$I2C6_PINS_PHANDLE"
fdtput -t x "$temporary" "$I2C6" "$DEPENDENCY_PROPERTY" "$HANDOFF_PHANDLE"
fdtput -t x "$temporary" "$I2C6" clock-frequency 0x33e140
fdtput -t x "$temporary" "$I2C6" mediatek,use-push-pull
fdtput -t s "$temporary" "$I2C6" pinctrl-names default
fdtput -t x "$temporary" "$I2C6" pinctrl-0 "$I2C6_PINS_PHANDLE"
fdtput -t s "$temporary" "$I2C6" status okay

fdtput -c "$temporary" "$DA9214"
fdtput -t s "$temporary" "$DA9214" compatible dlg,da9214
fdtput -t x "$temporary" "$DA9214" reg 0x68
fdtput -c "$temporary" "$DA9214/regulators"
fdtput -c "$temporary" "$DA9214/regulators/BUCKB"
fdtput -t s "$temporary" "$DA9214/regulators/BUCKB" regulator-name vproc-big
fdtput -c "$temporary" "$DA9214/regulators/BUCKA"
fdtput -t s "$temporary" "$DA9214/regulators/BUCKA" regulator-name da9214-bucka

python3 "$validator" --ao "$ao_dtb" --candidate "$temporary"
built_sha256="$(sha256sum "$temporary" | awk '{ print $1 }')"
chmod 0600 "$temporary"
mv -n "$temporary" "$output"
[[ -f "$output" && ! -L "$output" && ! -e "$temporary" ]] || \
	die 'exclusive Candidate AT DT publication failed'
temporary=
trap - EXIT

printf 'validation=candidate-at-dtb-built\n'
printf 'output=%s\nsha256=%s\n' "$output" "$built_sha256"
printf 'baseline=exact-hardware-passed-candidate-ao-final-dtb\n'
printf 'handoff_phandle=0x2c\n'
printf 'handoff_access_controller_cells=0\n'
printf 'i2c6_dependency_property=%s\n' "$DEPENDENCY_PROPERTY"
printf 'i2c6=enabled-with-legacy-da9214-child\n'
printf 'i2c6_pinctrl_frequency_push_pull=3400000-push-pull\n'
printf 'da9214_regulators=BUCKA,BUCKB\n'
printf 'added_nodes=4\nadded_properties=10\nchanged_properties=1\n'
printf 'device_access=none\nstorage_access=none\n'
