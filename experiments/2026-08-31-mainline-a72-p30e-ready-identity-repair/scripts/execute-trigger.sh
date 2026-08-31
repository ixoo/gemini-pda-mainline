#!/usr/bin/env bash

# Source-pin the boot-bound executor and retarget only the exact READY-identity
# candidate, corrected ABI-3 tooling identities, and evidence namespace.
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

derived=$(mktemp "$script_dir/.derived-execute-a72-p30e-ready-identity-repair.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743", "459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16", 1),
    ("5a01a7128202b7e1d6c776d38cd594e8c90bf21b94cbf493c3a17dcd05cfe029", "93cee6501a6224b2c3c2e944c3701f7523c029f17ea55de822689cc49423e68d", 1),
    ("1634b5624d43c740cd5d5b14a90286c7ff1bc368b3412da1723d94f50bb84f7a", "6b896c649c7c296a81833d769e763e1964bc359f6e6d002253d063a8d1683e25", 1),
    ("a22f33457be8bae80b32f60ff01026dbe49410368d73c76c1da74a57c21ae04d", "05accc9657be8268b0602216324919efa193243c61ad2ae78bdc2a6e3734304d", 1),
    ("2026-08-31-mainline-a72-sram-selector-mask-contract-repair", "2026-08-31-mainline-a72-p30e-ready-identity-repair", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-sram-selector-mask-contract-repair", 1),', '("a72-isolation-held-result-contract-repair", "a72-p30e-ready-identity-repair", 1),', 1),
    (".derived-execute-a72-selector-mask-repair-inner.XXXXXXXX", ".derived-execute-a72-p30e-ready-identity-repair-inner.XXXXXXXX", 1),
    ("selector-mask repair executor derivation", "P30E READY-identity executor derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E READY-identity executor derivation: expected "
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
