#!/usr/bin/env bash

# Reconstruct and invoke Candidate AN's exact-MAC one-shot watcher only from
# its source-pinned Candidate AH foundation. The derived watcher makes at most
# one call to AN's bounded read-only runtime collector.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly AH_WATCHER_SHA256=b5664f6d883207af9bcb80c6d731dfc8d568e62d203daa38afc9163ba33ca12a

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk bash mktemp python3 rm shasum stat; do
	command -v "$command" >/dev/null 2>&1 || \
		die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
foundation="$repo_root/experiments/2026-07-22-ad-contract-af-kernel-split/scripts/collect-cycle.sh"
deriver="$script_dir/derive-cycle-watcher.py"
collector="$script_dir/collect-runtime.sh"
identity="$script_dir/candidate_an.py"
readonly script_dir repo_root foundation deriver collector identity

for input in "$foundation" "$deriver" "$collector" "$identity"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || \
		die "cycle watcher input missing or unsafe: $input"
done
[[ -x "$deriver" && -x "$collector" ]] || \
	die 'Candidate AN watcher deriver or runtime collector is not executable'
[[ "$(shasum -a 256 "$foundation" | awk '{ print $1 }')" == \
	"$AH_WATCHER_SHA256" ]] || \
	die 'source-pinned Candidate AH cycle watcher changed'

# The deriver validates all AN artifact pins before publishing a runnable
# watcher. TMPDIR is canonical on macOS, where /tmp points at /private/tmp.
temporary_root=${TMPDIR:-/tmp}
temporary="$(mktemp "${temporary_root%/}/candidate-an-cycle-watcher.XXXXXX")"
rm -f -- "$temporary"
cleanup() {
	[[ ! -e "${temporary:-}" && ! -L "${temporary:-}" ]] || rm -f -- "$temporary"
}
trap cleanup EXIT

python3 "$deriver" --source "$foundation" --repository "$repo_root" \
	--output "$temporary" >/dev/null
[[ -f "$temporary" && ! -L "$temporary" ]] || \
	die 'derived Candidate AN cycle watcher is absent or unsafe'
[[ "$(stat -f '%Lp' "$temporary")" == 700 ]] || \
	die 'derived Candidate AN cycle watcher mode is not 0700'
bash -n "$temporary"
"$temporary" "$@"
