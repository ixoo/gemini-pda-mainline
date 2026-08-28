#!/usr/bin/env bash

# Source-pin the exact pre-trigger probe and retarget only the installed image.
set -euo pipefail
readonly SOURCE_SHA256=008a8e33cd67654dc4d3632277b6d1600ef9b565ef7e5b763bb481c424229b60
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P); repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-28-mainline-a72-admission-live-trigger/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || { printf 'error: source probe changed\n' >&2; exit 2; }
sed 's/4e0f86885a16df2f8b0c1efb4dd2e67394938bad1ef720adabf70ff4635ec0ef/f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02/' "$source_probe"
