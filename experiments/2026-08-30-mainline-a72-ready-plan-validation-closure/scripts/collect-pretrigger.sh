#!/usr/bin/env bash

# Source-pin the proven read-only collector and retarget it to the exact
# post-0437 READY-plan candidate. This script never sends a trigger token.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=c1e0ecb7e0f10b3c9fd1824b0111b9c641097b61c695ff53121246f87b901c2e
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-30-mainline-a72-provenance-serviceability-composition/scripts/collect-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-ready-plan-closure.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", "726b622ab503e844e2faddb33fe357250df329510d5b3ab5877687f4db7bfcb0", 1),
    ("5826658d983313d2ddb7b032dc80f8a7a3844076aaf346e36f852702e7cec010", "5693fdf485f03b1fc4ed4157bb884e73853b4d07b6d4fae67bac6c5cc1692dc5", 1),
    ("3a728b7fb16c9d9c58580311d5e80f29d17a92d8f69c849d5e5c33d81cb8477d", "8f56cf2b7d55db5b8f34702a939b3be593532a98a5de55d606f5ae82e4972471", 1),
    ("c617550e84260388144e702bb3361d44291ed62f0ef0bb425b80b08555705406", "1691eefd2ca679bc1f9dea043910254d801c5aa6b0e934bd11831b7baa8a5c5d", 1),
    ("a72-provenance-serviceability-pretrigger-attempt-1", "a72-ready-plan-closure-pretrigger-attempt-1", 1),
    (".derived-collect-a72-provenance-pretrigger.XXXXXXXX", ".derived-collect-a72-ready-plan-closure-inner.XXXXXXXX", 1),
    (".gemini-a72-provenance-probe.XXXXXXXX", ".gemini-a72-ready-plan-closure-probe.XXXXXXXX", 1),
    (".gemini-a72-provenance-command.XXXXXXXX", ".gemini-a72-ready-plan-closure-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe READY-plan collector derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
