#!/usr/bin/env bash

# Source-pin the reviewed P27 one-shot trigger; the held-result repair changes
# only the kernel-side acquire-result contract, not the boot-bound trigger.
set -euo pipefail

readonly SOURCE_SHA256=d8016c61216d16a64d35850eb6ec95a4dd011b1dae62afedd7345de2a41caa81
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_trigger="$repo_root/experiments/2026-08-30-mainline-a72-p27-runtime-attribution/scripts/remote-trigger.sh"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source trigger changed\n' >&2
	exit 2
}
exec "$source_trigger" "$@"
