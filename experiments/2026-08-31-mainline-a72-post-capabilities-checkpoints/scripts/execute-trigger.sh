#!/usr/bin/env bash

# Source-pin the boot-bound executor and retarget the exact post-capabilities
# candidate, ABI-5 tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=ba6c042553cf320c85e0989afe8872ee7233a795483a544ea97272a3d71e50c9
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-31-mainline-a72-secondary-entry-checkpoints/scripts/execute-trigger.sh"
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-post-capabilities-checkpoints.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("6d0bf75b55ef981a915ba0b9a8d305d5713476acc4fc2ee95e4201f234b2253f",
     "9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630", 1),
    ("2a203083e9034b04e963f30e6bff557863f41287aff55ca1e3ce43d0152e5777",
     "88a0d2d8cc3994a6b95b4c04c832531846e52bf5fff38435b2187ef4dcc161b0", 1),
    ("39866fc11d957c4e1d2cb9f7e2f58f6ca6659793896a30f23cbfb3a383c9589b",
     "7ab8f0b2267cd337c4711c01c1cc57764f02a98455eac5e6ab7a240424817ecd", 1),
    ("b79bf294e197345061afda682da56afdafaf9540a1dbc3e3db7a2c2e36e4923d",
     "6b2949fddca6c2001ed75cd11321f66ddbff253e4daf520f2554b4cbee26b407", 1),
    ("2026-08-31-mainline-a72-secondary-entry-checkpoints",
     "2026-08-31-mainline-a72-post-capabilities-checkpoints", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-secondary-entry-checkpoints", 1),',
     '("a72-isolation-held-result-contract-repair", "a72-post-capabilities-checkpoints", 1),', 1),
    (".derived-execute-a72-secondary-entry-checkpoints-inner.XXXXXXXX",
     ".derived-execute-a72-post-capabilities-checkpoints-inner.XXXXXXXX", 1),
    ("secondary-entry checkpoint executor derivation",
     "post-capabilities checkpoint executor derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe post-capabilities executor derivation: expected "
            f"{count}, found {actual}: {old}"
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
