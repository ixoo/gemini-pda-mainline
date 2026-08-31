#!/usr/bin/env bash

# Source-pin the reviewed ABI-2 one-shot trigger without changing its writes.
set -euo pipefail

readonly SOURCE_SHA256=a383de2a047d51e8d2a9f9bbb5d48ab5a7f26dcbb732dba872a96607c351192f
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_trigger="$repo_root/experiments/2026-08-31-mainline-a72-sram-p28-terminal-diagnostic/scripts/remote-trigger.sh"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source trigger changed\n' >&2
	exit 2
}
exec "$source_trigger" "$@"
