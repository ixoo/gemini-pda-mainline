#!/usr/bin/env bash

# Source-pin the boot-bound executor and retarget the exact r0p1 candidate,
# ABI-5 tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=de902e40085edb4174900165a305d38e53b247f012ec414ec9a551c54a65d475
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-31-mainline-a72-post-capabilities-checkpoints/scripts/execute-trigger.sh"
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-r0p1-expected-pair-repair.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630",
     "b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d", 1),
    ("88a0d2d8cc3994a6b95b4c04c832531846e52bf5fff38435b2187ef4dcc161b0",
     "1c1a0e8b975276c51866b56831108c785c1f69d4107b0b2808bfa442cfaef348", 1),
    ("7ab8f0b2267cd337c4711c01c1cc57764f02a98455eac5e6ab7a240424817ecd",
     "a237f2d8f251661caa5cdd37aeda97c269129bb1c411f4d44be67f888192f6f0", 1),
    ("6b2949fddca6c2001ed75cd11321f66ddbff253e4daf520f2554b4cbee26b407",
     "c0426f2c197df439ef7108082c12d72a70b0c36722d7828952706bf3de508ab3", 1),
    ("2026-08-31-mainline-a72-post-capabilities-checkpoints",
     "2026-08-31-mainline-a72-r0p1-expected-pair-repair", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-post-capabilities-checkpoints", 1),',
     '("a72-isolation-held-result-contract-repair", "a72-r0p1-expected-pair-repair", 1),', 1),
    (".derived-execute-a72-post-capabilities-checkpoints-inner.XXXXXXXX",
     ".derived-execute-a72-r0p1-expected-pair-repair-inner.XXXXXXXX", 1),
    ("post-capabilities checkpoint executor derivation",
     "r0p1 expected-pair repair executor derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe r0p1 executor derivation: expected {count}, "
            f"found {actual}: {old}"
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
