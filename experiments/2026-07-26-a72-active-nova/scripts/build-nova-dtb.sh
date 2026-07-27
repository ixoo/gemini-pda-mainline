#!/usr/bin/env bash

# Deterministically derive Candidate Nova's active A72 DTB from the exact
# hardware-tested AO tree.  The provider node and every phandle it consumes
# are added explicitly; no device access or storage access occurs here.
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --ao-dtb FILE --output FILE\n' "$0" >&2; }

ao_dtb=; output=
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

for command in awk chmod dirname fdtget fdtput install mktemp mv python3 rm sha256sum; do
    command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -f "$ao_dtb" && ! -L "$ao_dtb" && -s "$ao_dtb" ]] || die 'Candidate AO DT is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output DT'
output_parent="$(dirname -- "$output")"
[[ -d "$output_parent" && ! -L "$output_parent" ]] || die 'output parent is unsafe'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
validator="$script_dir/validate-nova-dtb.py"
[[ -f "$validator" && ! -L "$validator" && -s "$validator" ]] || die 'Nova DT validator is missing or unsafe'

readonly AO_DTB_SHA256=de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7
readonly I2C6=/i2c@1100e000
readonly I2C6_PINS=/pinctrl@10005000/i2c6-pins
readonly HANDOFF=/dvfsp-handoff@11015000
readonly DA9214=$I2C6/regulator@68
readonly BUCKB=$DA9214/regulators/BUCKB
readonly A72_POWER=/a72-power@10222000
readonly CPU8=/cpus/cpu@200
readonly CPU9=/cpus/cpu@201
readonly SCPSYS=/power-controller@10006000
readonly WATCHDOG=/watchdog@10007000

readonly HANDOFF_PHANDLE=0x2c
readonly I2C6_PINS_PHANDLE=0x2d
readonly CPU8_PHANDLE=0x2e
readonly CPU9_PHANDLE=0x2f
readonly WATCHDOG_PHANDLE=0x30
readonly BUCKB_PHANDLE=0x31

[[ "$(sha256sum "$ao_dtb" | awk '{ print $1 }')" == "$AO_DTB_SHA256" ]] || die 'exact hardware-passed Candidate AO DT changed'
[[ "$(fdtget -t s "$ao_dtb" "$I2C6" status)" == disabled ]] || die 'Candidate AO I2C6 boundary changed'
[[ "$(fdtget -t s "$ao_dtb" "$HANDOFF" status)" == okay ]] || die 'Candidate AO handoff supplier is not enabled'
if [[ -n "$(fdtget -l "$ao_dtb" "$I2C6")" ]]; then
    die 'Candidate AO I2C6 is not childless'
fi
for forbidden in "$DA9214" "$A72_POWER"; do
    if fdtget -p "$ao_dtb" "$forbidden" >/dev/null 2>&1; then
        die "Candidate AO unexpectedly contains $forbidden"
    fi
done

temporary="$(mktemp "$output_parent/.candidate-nova-dtb.XXXXXX")"
cleanup() { [[ ! -f "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT
install -m 0600 "$ao_dtb" "$temporary"

# AO uses the exact contiguous allocation 0x01..0x2b.  Preserve it and append
# deterministic handles for the active provider's CPU, reset, and supply
# references after the existing AS handoff/I2C6 additions.
fdtput -t x "$temporary" "$HANDOFF" '#access-controller-cells' 0
fdtput -t x "$temporary" "$HANDOFF" phandle "$HANDOFF_PHANDLE"
fdtput -t x "$temporary" "$I2C6_PINS" phandle "$I2C6_PINS_PHANDLE"
fdtput -t x "$temporary" "$I2C6" access-controllers "$HANDOFF_PHANDLE"
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
fdtput -t x "$temporary" "$BUCKB" phandle "$BUCKB_PHANDLE"
fdtput -c "$temporary" "$DA9214/regulators/BUCKA"
fdtput -t s "$temporary" "$DA9214/regulators/BUCKA" regulator-name da9214-bucka

fdtput -t x "$temporary" "$CPU8" phandle "$CPU8_PHANDLE"
fdtput -t x "$temporary" "$CPU9" phandle "$CPU9_PHANDLE"
fdtput -t s "$temporary" "$SCPSYS" compatible mediatek,mt6797-scpsys syscon
fdtput -t x "$temporary" "$WATCHDOG" '#reset-cells' 1
fdtput -t x "$temporary" "$WATCHDOG" phandle "$WATCHDOG_PHANDLE"

fdtput -c "$temporary" "$A72_POWER"
fdtput -t s "$temporary" "$A72_POWER" compatible mediatek,mt6797-a72-power
fdtput -t x "$temporary" "$A72_POWER" reg 0 0x10222000 0 0x1000
fdtput -t x "$temporary" "$A72_POWER" mediatek,spm 0x0b
fdtput -t x "$temporary" "$A72_POWER" cpus "$CPU8_PHANDLE" "$CPU9_PHANDLE"
fdtput -t x "$temporary" "$A72_POWER" vproc-big-supply "$BUCKB_PHANDLE"
fdtput -t x "$temporary" "$A72_POWER" resets "$WATCHDOG_PHANDLE" 0xb
fdtput -t s "$temporary" "$A72_POWER" reset-names pwrap
fdtput -t s "$temporary" "$A72_POWER" status okay

python3 "$validator" --ao "$ao_dtb" --candidate "$temporary"
built_sha256="$(sha256sum "$temporary" | awk '{ print $1 }')"
chmod 0600 "$temporary"
mv -n "$temporary" "$output"
[[ -f "$output" && ! -L "$output" && ! -e "$temporary" ]] || die 'exclusive Candidate Nova DT publication failed'
temporary=; trap - EXIT

printf 'validation=candidate-nova-active-a72-dtb-built\n'
printf 'output=%s\nsha256=%s\n' "$output" "$built_sha256"
printf 'baseline=exact-hardware-passed-candidate-ao-final-dtb\n'
printf 'a72_power=%s\nscpsys=%s\nwatchdog=%s\n' "$A72_POWER" "$SCPSYS" "$WATCHDOG"
printf 'cpu8_phandle=0x2e\ncpu9_phandle=0x2f\nwatchdog_phandle=0x30\nbuckb_phandle=0x31\n'
printf 'i2c6=enabled-with-legacy-da9214-child\nprovider=active-one-way-with-late-cpu8-retry\n'
printf 'device_access=none\nstorage_access=none\n'
