#!/usr/bin/env bash

# Source-pin the proven read-only pre-trigger collector and retarget only the
# exact READY-token repair candidate, support tools, and private evidence name.
# This script never sends the trigger token.
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

derived=$(mktemp "$script_dir/.derived-collect-a72-ready-contract-pretrigger.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", "a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", 1),
    ("5826658d983313d2ddb7b032dc80f8a7a3844076aaf346e36f852702e7cec010", "147463c13a5dc38d633f75ab2770067386c725d462a03133040c083d5b7ff5a4", 1),
    ("3a728b7fb16c9d9c58580311d5e80f29d17a92d8f69c849d5e5c33d81cb8477d", "ee6c566007a785285bfdbf021ffa3bf2ed62f625ba08233335fe7a1f963ce800", 1),
    ("c617550e84260388144e702bb3361d44291ed62f0ef0bb425b80b08555705406", "8feeb6e8c562278c0e76c284a757c8849dcc0d1e5eff705fee3434229c82eb52", 1),
    ("a72-provenance-serviceability-pretrigger-attempt-1", "a72-ready-token-contract-repair-pretrigger-attempt-1", 1),
    (".gemini-a72-provenance-probe.XXXXXXXX", ".gemini-a72-ready-contract-probe.XXXXXXXX", 1),
    (".gemini-a72-provenance-command.XXXXXXXX", ".gemini-a72-ready-contract-command.XXXXXXXX", 1),
    ("unsafe provenance pre-trigger collector derivation", "unsafe READY-contract pre-trigger collector derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe READY-contract pre-trigger collector derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
