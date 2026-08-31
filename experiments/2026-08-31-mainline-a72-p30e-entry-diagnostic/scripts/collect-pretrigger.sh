#!/usr/bin/env bash

# Source-pin the bounded read-only collector and retarget only the exact P30E
# candidate, tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=c030ed76c1b052fabbe66c6194fd90331e1e69cc63c450dc67221832a2aada74
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-31-mainline-a72-sram-selector-mask-contract-repair/scripts/collect-pretrigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-p30e-entry-diagnostic.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743", "a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453", 1),
    ("23177682a61122b6055aba518d15e803c207b828f2d4c4d41cc3f332b9dccd14", "742a8322254f617efe07ffff6265720cbeebe647edc3d1f0f77f087a5fb9a685", 1),
    ("1de4be12c413b5b46cc57abc3e54ed0b8bbb286ab3f09959c834e297df8f077e", "af527e6224d68f731534b5d14001c3d10070c62828bc3d59188c55495c992efd", 1),
    ("a22f33457be8bae80b32f60ff01026dbe49410368d73c76c1da74a57c21ae04d", "f3f4067fdb365ea0fc5eee7c2b0176ddb45c69c5ddf68ddf886aad64e3995a7f", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-sram-selector-mask-contract-repair", 1),', '("a72-isolation-held-result-contract-repair", "a72-p30e-entry-diagnostic", 1),', 1),
    (".derived-collect-a72-selector-mask-repair-inner.XXXXXXXX", ".derived-collect-a72-p30e-entry-diagnostic-inner.XXXXXXXX", 1),
    ("selector-mask repair collector derivation", "P30E entry collector derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E collector derivation: expected {count}, found {actual}: {old}"
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
