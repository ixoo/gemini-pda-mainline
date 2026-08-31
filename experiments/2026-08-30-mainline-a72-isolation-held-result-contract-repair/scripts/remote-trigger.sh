#!/usr/bin/env bash

# Source-pin the reviewed one-shot trigger; this repair changes only the
# kernel-side isolation-result contract, not the boot-bound trigger.
set -euo pipefail

readonly SOURCE_SHA256=eb468b61306d21175d5f758d8c0e682ab549bf8757ccbef0c3955beb4ebbc009
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_trigger="$repo_root/experiments/2026-08-30-mainline-a72-p27-held-result-contract-repair/scripts/remote-trigger.sh"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source trigger changed\n' >&2
	exit 2
}
exec "$source_trigger" "$@"
