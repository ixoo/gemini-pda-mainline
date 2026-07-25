#!/usr/bin/env bash

# The cleanup function is invoked indirectly by the EXIT trap.
# shellcheck disable=SC2317

set -euo pipefail
export LC_ALL=C
umask 077

readonly PLACEHOLDER_PREFIX=REPLACE_AFTER_CALIBRATION_
readonly Z_RAW_SHA256=985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9
readonly Z_RAW_SIZE=6866944
readonly Z_PADDED_SHA256=ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40
readonly EXPECTED_CURRENT_Y_PADDED_SHA256=dab4a5217ddffe32062819febc3160f0a12eb97ac8afbf0bc4f068ce3c72cb17
readonly Y_DERIVED_INSTALLER_SHA256=923bca5daab72afcf46fbd2de6abd1f81bf3412a990c938aff68ccec3f4a3e67
readonly Y_WRAPPER_SHA256=1a33de1f640650164155ed20555b162a2b9455d2495e46a3065589b2d1759268
readonly Y_DERIVER_SHA256=ac343dc456f90098fbe28062148aa2f79d1b27b436ce7065a71e8a56c13f24e7
readonly X_INSTALLER_SHA256=2ae4e2a3ee4741bff80b87f8b32fef44bdfefdc1a870c876d0ea95feb247a79e

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

# This gate intentionally precedes script-directory resolution, repository
# inspection, SSH, sudo, device discovery, backup creation, and every possible
# hardware write. Candidate Z must stay impossible to install until a built
# artifact has supplied all three exact calibration values.
for name in Z_RAW_SHA256 Z_RAW_SIZE Z_PADDED_SHA256; do
	value=${!name}
	[[ "$value" != "$PLACEHOLDER_PREFIX"* ]] || \
		die "calibration placeholder remains: $name"
done
for name in Z_RAW_SHA256 Z_PADDED_SHA256; do
	value=${!name}
	[[ "$value" =~ ^[0-9a-f]{64}$ ]] || die "invalid calibrated SHA-256: $name"
done
[[ "$Z_RAW_SIZE" =~ ^[1-9][0-9]*$ && "$Z_RAW_SIZE" -le 16777216 ]] || \
	die 'invalid or oversized calibrated Z_RAW_SIZE'
[[ "$Z_PADDED_SHA256" != "$EXPECTED_CURRENT_Y_PADDED_SHA256" ]] || \
	die 'Candidate Z padded hash unexpectedly equals the Candidate Y predecessor'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
y_experiment="$repo_root/experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic"
x_installer="$repo_root/experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/install-candidate-x-boot2.sh"
y_wrapper="$y_experiment/scripts/install-candidate-y-boot2.sh"
y_deriver="$y_experiment/scripts/derive-installer.py"
z_deriver="$script_dir/derive-installer.py"
for input in "$x_installer" "$y_wrapper" "$y_deriver" "$z_deriver"; do
	[[ -f "$input" && ! -L "$input" ]] || die "installer foundation missing or unsafe: $input"
done
for command in awk bash mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
for check in \
	"$x_installer:$X_INSTALLER_SHA256" \
	"$y_wrapper:$Y_WRAPPER_SHA256" \
	"$y_deriver:$Y_DERIVER_SHA256"; do
	path=${check%%:*}
	expected=${check##*:}
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || \
		die "hash-pinned installer foundation changed: $path"
done

workdir="$(mktemp -d /tmp/candidate-z-installer.XXXXXX)"
cleanup() { [[ ! -d "$workdir" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
derived_y="$workdir/install-candidate-y-boot2.sh"
python3 "$y_deriver" --source "$x_installer" --output "$derived_y" \
	--raw-sha256 94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee \
	--raw-size 6866944 \
	--padded-sha256 dab4a5217ddffe32062819febc3160f0a12eb97ac8afbf0bc4f068ce3c72cb17
[[ "$(sha256sum "$derived_y" | awk '{print $1}')" == \
	"$Y_DERIVED_INSTALLER_SHA256" ]] || die 'reconstructed Candidate Y installer changed'

adapted="$workdir/install-candidate-z-boot2.sh"
python3 "$z_deriver" --source "$derived_y" --output "$adapted" \
	--raw-sha256 "$Z_RAW_SHA256" --raw-size "$Z_RAW_SIZE" \
	--padded-sha256 "$Z_PADDED_SHA256"
bash -n "$adapted" || die 'derived Candidate Z installer failed syntax validation'
export GEMINI_REPO_ROOT="$repo_root"
set +e
"$adapted" "$@"
status=$?
set -e
exit "$status"
