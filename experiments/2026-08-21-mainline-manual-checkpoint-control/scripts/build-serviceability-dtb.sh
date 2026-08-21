#!/usr/bin/env bash

# Reuse the exact runtime-proven current-tree serviceability DT derivation.
set -euo pipefail
export LC_ALL=C

readonly SOURCE_SHA256=550527d86331bd5eb037ba60e787dc7f132a136f005c89e8864c58721ed9dc7d

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in bash sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-21-mainline-current-tree-serviceability-control/scripts/build-serviceability-dtb.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'
exec /bin/bash "$source_builder" "$@"
