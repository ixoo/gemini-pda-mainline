#!/usr/bin/env bash

# Materialize the reviewed ABI-5 one-shot trigger. Candidate identity and the
# exact READY frame are revalidated by execute-trigger.sh before this script is
# rendered; the remote program is then bound to the same boot ID.
set -euo pipefail

readonly SOURCE_SHA256=88a0d2d8cc3994a6b95b4c04c832531846e52bf5fff38435b2187ef4dcc161b0
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_trigger="$repo_root/experiments/2026-08-31-mainline-a72-post-capabilities-checkpoints/scripts/remote-trigger.sh"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source trigger changed\n' >&2
	exit 2
}
exec "$source_trigger" "$@"
