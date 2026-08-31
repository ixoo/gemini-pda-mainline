#!/usr/bin/env bash

# Source-pin the boot-bound executor and retarget only the selector-mask repair
# candidate, tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=7209032acdca01d099436cbfd56c70fe6924868b24108ef0c838219b324fa7ee
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-31-mainline-a72-sram-p28-terminal-diagnostic/scripts/execute-trigger.sh"
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-selector-mask-repair.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3", "cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743", 1),
    ("a383de2a047d51e8d2a9f9bbb5d48ab5a7f26dcbb732dba872a96607c351192f", "5a01a7128202b7e1d6c776d38cd594e8c90bf21b94cbf493c3a17dcd05cfe029", 1),
    ("6f2063d9254ff4d956f30faefe36481392b60011083b4980c5583a2b68ae39f5", "1634b5624d43c740cd5d5b14a90286c7ff1bc368b3412da1723d94f50bb84f7a", 1),
    ("644e0253a08586eed1579e52f865a488912f5b875663fbabfb2417442dd6d54f", "a22f33457be8bae80b32f60ff01026dbe49410368d73c76c1da74a57c21ae04d", 1),
    ("2026-08-31-mainline-a72-sram-p28-terminal-diagnostic", "2026-08-31-mainline-a72-sram-selector-mask-contract-repair", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-sram-p28-terminal-diagnostic", 1),', '("a72-isolation-held-result-contract-repair", "a72-sram-selector-mask-contract-repair", 1),', 1),
    (".derived-execute-a72-sram-p28-terminal-diagnostic-inner.XXXXXXXX", ".derived-execute-a72-selector-mask-repair-inner.XXXXXXXX", 1),
    ("SRAM/P28 diagnostic executor derivation", "selector-mask repair executor derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe selector-mask repair executor derivation: expected "
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
