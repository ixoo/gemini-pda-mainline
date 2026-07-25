#!/usr/bin/env bash

# Derive the exact AL collector from the hardware-passed AH collector, then run
# it once. candidate_al.py must have complete two-build artifact calibration.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --interface IFACE --output FILE --installed-full-sha256 SHA256\n' "$0" >&2
}

interface=
output=
installed_full_sha256=
while (($#)); do
	case "$1" in
	--interface|--output|--installed-full-sha256)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--interface) [[ -z "$interface" ]] || die '--interface duplicated'; interface=$2 ;;
		--output) [[ -z "$output" ]] || die '--output duplicated'; output=$2 ;;
		--installed-full-sha256) [[ -z "$installed_full_sha256" ]] || die '--installed-full-sha256 duplicated'; installed_full_sha256=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage >&2; die "unknown option: $1" ;;
	esac
done
[[ "$interface" =~ ^[A-Za-z0-9]+$ && -n "$output" ]] || { usage >&2; exit 2; }
[[ "$installed_full_sha256" =~ ^[0-9a-f]{64}$ ]] || \
	die 'installed checksum must be one lowercase SHA-256 value'
for command in awk chmod mktemp python3 rm shasum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
identity="$script_dir/candidate_al.py"
deriver="$script_dir/derive-runtime-collector.py"
validator="$script_dir/validate-runtime.py"
foundation="$repo_root/experiments/2026-07-22-ad-contract-af-kernel-split/scripts/collect-runtime.sh"
for input in "$identity" "$deriver" "$validator" "$foundation"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || \
		die "runtime collector input missing or unsafe: $input"
done
[[ "$(shasum -a 256 "$foundation" | awk '{ print $1 }')" == \
	13f27efd9de671759c900639f9541a3851b6d13aebdddf5270e91f37f044ddd4 ]] || \
	die 'source-pinned Candidate AH runtime collector changed'

pinned_full_sha256="$(python3 - "$identity" <<'PY'
import importlib.util
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("candidate_al_collector_pins", path)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load Candidate AL identity")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.require_artifact_pins()
print(module.PADDED_SHA256)
PY
)" || die 'Candidate AL production artifact pins are unresolved or invalid'
[[ "$installed_full_sha256" == "$pinned_full_sha256" ]] || \
	die 'installed full-partition checksum is not Candidate AL'

# TMPDIR is canonical on macOS, where /tmp itself is a symlink to /private/tmp.
temporary_root=${TMPDIR:-/tmp}
temporary="$(mktemp "${temporary_root%/}/candidate-al-runtime-collector.XXXXXX")"
rm -f -- "$temporary"
cleanup() { [[ ! -e "${temporary:-}" && ! -L "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT
python3 "$deriver" --source "$foundation" --validator "$validator" \
	--output "$temporary" >/dev/null
chmod 0700 "$temporary"
"$temporary" --interface "$interface" --output "$output" \
	--installed-full-sha256 "$installed_full_sha256"
