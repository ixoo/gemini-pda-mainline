#!/usr/bin/env bash

# The cleanup function is invoked indirectly by the EXIT trap.
# shellcheck disable=SC2317

set -euo pipefail
export LC_ALL=C
umask 077

readonly PLACEHOLDER_PREFIX=REPLACE_AFTER_CALIBRATION_
readonly Y_RAW_SHA256=94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee
readonly Y_RAW_SIZE=6866944
readonly Y_PADDED_SHA256=dab4a5217ddffe32062819febc3160f0a12eb97ac8afbf0bc4f068ce3c72cb17
readonly EXPECTED_CURRENT_X_PADDED_SHA256=e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855
readonly X_INSTALLER_SHA256=2ae4e2a3ee4741bff80b87f8b32fef44bdfefdc1a870c876d0ea95feb247a79e

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

# This gate intentionally precedes repository inspection, SSH, sudo, device
# discovery, backup creation, and every possible hardware write.
for name in Y_RAW_SHA256 Y_RAW_SIZE Y_PADDED_SHA256; do
	value=${!name}
	[[ "$value" != "$PLACEHOLDER_PREFIX"* ]] || \
		die "calibration placeholder remains: $name"
done
for name in Y_RAW_SHA256 Y_PADDED_SHA256; do
	value=${!name}
	[[ "$value" =~ ^[0-9a-f]{64}$ ]] || die "invalid calibrated SHA-256: $name"
done
[[ "$Y_RAW_SIZE" =~ ^[1-9][0-9]*$ && "$Y_RAW_SIZE" -le 16777216 ]] || \
	die 'invalid or oversized calibrated Y_RAW_SIZE'
[[ "$Y_PADDED_SHA256" != "$EXPECTED_CURRENT_X_PADDED_SHA256" ]] || \
	die 'Candidate Y padded hash unexpectedly equals the Candidate X predecessor'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
x_installer="$repo_root/experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/install-candidate-x-boot2.sh"
deriver="$script_dir/derive-installer.py"
for input in "$x_installer" "$deriver"; do
	[[ -f "$input" && ! -L "$input" ]] || die "installer foundation missing or unsafe: $input"
done
for command in awk bash mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ "$(sha256sum "$x_installer" | awk '{print $1}')" == "$X_INSTALLER_SHA256" ]] || \
	die 'calibrated Candidate X installer changed'

workdir="$(mktemp -d /tmp/candidate-y-installer.XXXXXX)"
cleanup() { rm -rf -- "$workdir"; }
trap cleanup EXIT
adapted="$workdir/install-candidate-y-boot2.sh"
python3 "$deriver" --source "$x_installer" --output "$adapted" \
	--raw-sha256 "$Y_RAW_SHA256" --raw-size "$Y_RAW_SIZE" \
	--padded-sha256 "$Y_PADDED_SHA256"
bash -n "$adapted" || die 'derived Candidate Y installer failed syntax validation'
export GEMINI_REPO_ROOT="$repo_root"
set +e
"$adapted" "$@"
status=$?
set -e
exit "$status"
