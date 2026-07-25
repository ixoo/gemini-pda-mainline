#!/usr/bin/env bash

# Deterministically transform the exact hardware-passed AH final DT. This does
# not select a package DT and does not compile or enable an A72 power provider.

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
[[ -n "$ah_dtb" && -n "$output" ]] || { usage >&2; exit 2; }
for command in awk chmod dirname fdtget fdtput install mktemp mv python3 rm \
	sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -f "$ah_dtb" && ! -L "$ah_dtb" && -s "$ah_dtb" ]] || \
	die 'Candidate AH DT is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output DT'
output_parent="$(dirname -- "$output")"
[[ -d "$output_parent" && ! -L "$output_parent" ]] || die 'output parent is unsafe'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
validator="$script_dir/validate-dtb-delta.py"
[[ -f "$validator" && ! -L "$validator" && -s "$validator" ]] || \
	die 'Candidate AL DT validator is missing or unsafe'

readonly AH_DTB_SHA256=27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845
readonly I2C6=/i2c@1100e000
readonly I2C6_PINS=/pinctrl@10005000/i2c6-pins
readonly DA9214=$I2C6/regulator@68
[[ "$(sha256sum "$ah_dtb" | awk '{ print $1 }')" == "$AH_DTB_SHA256" ]] || \
	die 'exact hardware-passed Candidate AH DT changed'
[[ "$(fdtget -t s "$ah_dtb" "$I2C6" status)" == disabled ]] || \
	die 'Candidate AH I2C6 boundary changed'
if fdtget "$ah_dtb" "$I2C6_PINS" phandle >/dev/null 2>&1; then
	die 'Candidate AH I2C6 pin group unexpectedly has a phandle'
fi
if fdtget -l "$ah_dtb" "$I2C6" | awk '$0 == "regulator@68" { found++ } END { exit found != 0 }'; then
	:
else
	die 'Candidate AH unexpectedly contains a DA9214 child'
fi

temporary="$(mktemp "$output_parent/.candidate-al-dtb.XXXXXX")"
cleanup() { [[ ! -f "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT
install -m 0600 "$ah_dtb" "$temporary"

# Preserve every existing AH phandle. 0x2c is the first unused value after
# AH's exact contiguous 0x01--0x2b allocation.
fdtput -t x "$temporary" "$I2C6_PINS" phandle 0x2c
fdtput -t x "$temporary" "$I2C6" clock-frequency 0x33e140
fdtput -t x "$temporary" "$I2C6" mediatek,use-push-pull
fdtput -t s "$temporary" "$I2C6" pinctrl-names default
fdtput -t x "$temporary" "$I2C6" pinctrl-0 0x2c
fdtput -t s "$temporary" "$I2C6" status okay

fdtput -c "$temporary" "$DA9214"
fdtput -t s "$temporary" "$DA9214" compatible dlg,da9214
fdtput -t x "$temporary" "$DA9214" reg 0x68
fdtput -c "$temporary" "$DA9214/regulators"
# fdtput prepends children, so create BUCKB first to retain patch 0089's
# BUCKA-then-BUCKB tree order. The semantic validator does not rely on order.
fdtput -c "$temporary" "$DA9214/regulators/BUCKB"
fdtput -t s "$temporary" "$DA9214/regulators/BUCKB" regulator-name vproc-big
fdtput -c "$temporary" "$DA9214/regulators/BUCKA"
fdtput -t s "$temporary" "$DA9214/regulators/BUCKA" regulator-name da9214-bucka

python3 "$validator" --ah "$ah_dtb" --candidate "$temporary"
built_sha256="$(sha256sum "$temporary" | awk '{ print $1 }')"
chmod 0600 "$temporary"
mv -n "$temporary" "$output"
[[ -f "$output" && ! -L "$output" && ! -e "$temporary" ]] || \
	die 'exclusive Candidate AL DT publication failed'
temporary=
trap - EXIT
printf 'validation=candidate-al-dtb-built\n'
printf 'output=%s\nsha256=%s\n' "$output" "$built_sha256"
printf 'baseline=exact-candidate-ah-final-dtb\n'
printf 'semantic_delta=patch-0089-i2c6-da9214-only\n'
printf 'a72_power_node=absent\ncpu8_cpu9_request=none\n'
printf 'device_access=none\n'
