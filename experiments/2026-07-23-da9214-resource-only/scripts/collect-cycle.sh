#!/usr/bin/env bash

# Reconstruct and invoke the exact-MAC one-shot watcher only after Candidate AL
# artifact calibration is source-pinned.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod mktemp python3 rm shasum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
foundation="$repo_root/experiments/2026-07-22-ad-contract-af-kernel-split/scripts/collect-cycle.sh"
deriver="$script_dir/derive-cycle-collector.py"
collector="$script_dir/collect-runtime.sh"
for input in "$foundation" "$deriver" "$collector" "$script_dir/candidate_al.py"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || \
		die "cycle collector input missing or unsafe: $input"
done
[[ "$(shasum -a 256 "$foundation" | awk '{ print $1 }')" == \
	b5664f6d883207af9bcb80c6d731dfc8d568e62d203daa38afc9163ba33ca12a ]] || \
	die 'source-pinned Candidate AH cycle collector changed'

# The deriver validates all artifact pins before creating a runnable watcher.
# TMPDIR is canonical on macOS, where /tmp itself is a symlink to /private/tmp.
temporary_root=${TMPDIR:-/tmp}
temporary="$(mktemp "${temporary_root%/}/candidate-al-cycle-collector.XXXXXX")"
rm -f -- "$temporary"
cleanup() { [[ ! -e "${temporary:-}" && ! -L "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT
python3 "$deriver" --source "$foundation" --repository "$repo_root" \
	--collector "$collector" --output "$temporary" >/dev/null
chmod 0700 "$temporary"
"$temporary" "$@"
