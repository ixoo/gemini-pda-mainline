#!/usr/bin/env bash

# Source-pin the boot-bound executor and retarget the exact model-guard
# candidate, ABI-5 tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=3684aca26d0587faa491757b0f6896f7b1035632db3513385b0466b9f4302b4b
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-31-mainline-a72-r0p1-expected-pair-repair/scripts/execute-trigger.sh"
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-expected-midr-model-guard.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d",
     "5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69", 1),
    ("1c1a0e8b975276c51866b56831108c785c1f69d4107b0b2808bfa442cfaef348",
     "607277cfea6d8e9b61079854e247bac6ac0a8eafba8646bf486b5057f6e4b215", 1),
    ("a237f2d8f251661caa5cdd37aeda97c269129bb1c411f4d44be67f888192f6f0",
     "307c43a114edff8f4566914ca820b3649d94a1b2148e6d1c9eac2f0f1a620565", 1),
    ("c0426f2c197df439ef7108082c12d72a70b0c36722d7828952706bf3de508ab3",
     "323b49071d93c0a13fc25a957c80ba5a82ba9b0f94c1ee5e3197a12d056c408e", 1),
    ("2026-08-31-mainline-a72-r0p1-expected-pair-repair",
     "2026-08-31-mainline-a72-expected-midr-model-guard-repair", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-r0p1-expected-pair-repair", 1),',
     '("a72-isolation-held-result-contract-repair", "a72-expected-midr-model-guard-repair", 1),', 1),
    (".derived-execute-a72-r0p1-expected-pair-repair-inner.XXXXXXXX",
     ".derived-execute-a72-expected-midr-model-guard-inner.XXXXXXXX", 1),
    ("r0p1 expected-pair repair executor derivation",
     "expected-MIDR model-guard repair executor derivation", 1),
)
for old, new, count in replacements:
    if text.count(old) != count:
        raise SystemExit(f"unsafe model-guard executor derivation: {old}")
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
