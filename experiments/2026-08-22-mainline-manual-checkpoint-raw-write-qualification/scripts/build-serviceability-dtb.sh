#!/usr/bin/env bash

# Reuse the exact source-pinned, runtime-proven serviceability DT derivation.
set -euo pipefail
export LC_ALL=C

readonly SOURCE_SHA256=6da5815213e2b1269ae264545fba80dfcd0b60617df91f794daa2fceb3a3d5db

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in bash sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-22-mainline-manual-checkpoint-map-control/scripts/build-serviceability-dtb.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'
exec /bin/bash "$source_builder" "$@"
