#!/usr/bin/env bash

# Source-pin the boot-bound executor and retarget only the exact P30E
# candidate, ABI-3 tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=28ad37009a504decad82ba23e2dbac42b92c96d601c9e13b9c9cce815bf9a1c7
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-31-mainline-a72-sram-selector-mask-contract-repair/scripts/execute-trigger.sh"
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-p30e-entry-diagnostic.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743", "a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453", 1),
    ("5a01a7128202b7e1d6c776d38cd594e8c90bf21b94cbf493c3a17dcd05cfe029", "f725a6ed0a41f1cc1507f77389d614d375eccf3eb27ae75c89343211cd8786a6", 1),
    ("1634b5624d43c740cd5d5b14a90286c7ff1bc368b3412da1723d94f50bb84f7a", "9173a294fe541462505679f54ff78e03198bdf36592b3dc4ce7c75ab22d7cf1f", 1),
    ("a22f33457be8bae80b32f60ff01026dbe49410368d73c76c1da74a57c21ae04d", "f3f4067fdb365ea0fc5eee7c2b0176ddb45c69c5ddf68ddf886aad64e3995a7f", 1),
    ("2026-08-31-mainline-a72-sram-selector-mask-contract-repair", "2026-08-31-mainline-a72-p30e-entry-diagnostic", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-sram-selector-mask-contract-repair", 1),', '("a72-isolation-held-result-contract-repair", "a72-p30e-entry-diagnostic", 1),', 1),
    (".derived-execute-a72-selector-mask-repair-inner.XXXXXXXX", ".derived-execute-a72-p30e-entry-diagnostic-inner.XXXXXXXX", 1),
    ("selector-mask repair executor derivation", "P30E entry executor derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E executor derivation: expected {count}, found {actual}: {old}"
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
