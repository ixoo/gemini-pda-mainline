#!/usr/bin/env bash

# Deterministically add the one-way DVFSP handoff receiver to the exact
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
	die 'Candidate AO DT validator is missing or unsafe'

readonly AH_DTB_SHA256=27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845
readonly INFRACFG=/syscon@10001000
readonly I2C6=/i2c@1100e000
readonly DA9214=$I2C6/regulator@68
readonly A72_POWER=/a72-power@10222000
readonly LEGACY_DVFSP=/dvfsp@11015000
readonly OBSERVER=/dvfsp-observer@11015000
readonly HANDOFF=/dvfsp-handoff@11015000

[[ "$(sha256sum "$ah_dtb" | awk '{ print $1 }')" == "$AH_DTB_SHA256" ]] || \
	die 'exact hardware-passed Candidate AH DT changed'
[[ "$(fdtget -t s "$ah_dtb" "$I2C6" status)" == disabled ]] || \
	die 'Candidate AH I2C6 boundary changed'
for forbidden in "$DA9214" "$A72_POWER" "$LEGACY_DVFSP" "$OBSERVER" \
	"$HANDOFF"; do
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
[[ "$(fdtget -t x "$ah_dtb" "$INFRACFG" '#clock-cells')" == 1 ]] || \
	die 'Candidate AH infracfg clock-provider shape changed'

# The handoff receiver must balance the same CCF clock that I2C6 names
# "main". Derive that two-cell reference from AH instead of introducing an
# independently selected clock ID, then pin the known AH result.
i2c6_clock_names="$(fdtget -t s "$ah_dtb" "$I2C6" clock-names)"
[[ "$i2c6_clock_names" == "main dma" ]] || \
	die 'Candidate AH I2C6 clock names changed'
i2c6_clocks="$(fdtget -t x "$ah_dtb" "$I2C6" clocks)"
read -r main_clock_phandle main_clock_id dma_clock_phandle dma_clock_id \
	<<<"$i2c6_clocks"
[[ -n "$main_clock_phandle" && -n "$main_clock_id" &&
	-n "$dma_clock_phandle" && -n "$dma_clock_id" ]] || \
	die 'Candidate AH I2C6 clock list is incomplete'
[[ "$i2c6_clocks" == \
	"$main_clock_phandle $main_clock_id $dma_clock_phandle $dma_clock_id" ]] || \
	die 'Candidate AH I2C6 clock list has an unexpected cell count'
[[ "$main_clock_phandle" == "$infracfg_phandle" &&
	"$main_clock_id" == 36 ]] || \
	die 'Candidate AH I2C6 main clock is not <0x3 0x36>'
[[ "$dma_clock_phandle" == "$infracfg_phandle" &&
	"$dma_clock_id" == 2e ]] || \
	die 'Candidate AH I2C6 DMA clock changed'

temporary="$(mktemp "$output_parent/.candidate-ao-dtb.XXXXXX")"
cleanup() { [[ ! -f "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT
install -m 0600 "$ah_dtb" "$temporary"

fdtput -c "$temporary" "$HANDOFF"
fdtput -t s "$temporary" "$HANDOFF" compatible \
	mediatek,mt6797-dvfsp-handoff
fdtput -t x "$temporary" "$HANDOFF" reg 0 0x11015000 0 0x1000
fdtput -t x "$temporary" "$HANDOFF" clocks \
	"$main_clock_phandle" "$main_clock_id"
fdtput -t s "$temporary" "$HANDOFF" clock-names i2c
fdtput -t x "$temporary" "$HANDOFF" mediatek,infracfg \
	"$infracfg_phandle"
fdtput -t s "$temporary" "$HANDOFF" status okay

python3 "$validator" --ah "$ah_dtb" --candidate "$temporary"
built_sha256="$(sha256sum "$temporary" | awk '{ print $1 }')"
chmod 0600 "$temporary"
mv -n "$temporary" "$output"
[[ -f "$output" && ! -L "$output" && ! -e "$temporary" ]] || \
	die 'exclusive Candidate AO DT publication failed'
temporary=
trap - EXIT

printf 'validation=candidate-ao-dtb-built\n'
printf 'output=%s\nsha256=%s\n' "$output" "$built_sha256"
printf 'baseline=exact-hardware-passed-candidate-ah-final-dtb\n'
printf 'added_node=%s\n' "$HANDOFF"
printf 'added_nodes=1\nadded_properties=6\nchanged_existing_nodes=0\n'
printf 'main_clock_source=%s:clocks[name=main]\n' "$I2C6"
printf 'main_clock_specifier=<0x%s 0x%s>\n' \
	"$main_clock_phandle" "$main_clock_id"
printf 'infracfg_path=%s\ninfracfg_phandle=0x%s\n' \
	"$INFRACFG" "$infracfg_phandle"
printf 'i2c6=byte-exact-disabled-childless\n'
printf 'observer_legacy_dvfsp_da9214_a72_power_nodes=absent\n'
printf 'fdt_header_reservations_phandles=preserved\n'
printf 'device_access=none\nstorage_access=none\n'
