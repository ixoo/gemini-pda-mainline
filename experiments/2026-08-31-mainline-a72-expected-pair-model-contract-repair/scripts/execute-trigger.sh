#!/usr/bin/env bash

# Source-pin the boot-bound executor and retarget the exact expected-pair
# repair candidate, tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=56019caec32edcff8cab67ab1d29aaaa548a8e25280330afb51e9bfbce0b8c0a
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-31-mainline-a72-expected-midr-model-guard-repair/scripts/execute-trigger.sh"
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-expected-pair-model-contract.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69",
     "42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee", 1),
    ("607277cfea6d8e9b61079854e247bac6ac0a8eafba8646bf486b5057f6e4b215",
     "623cbbf621da6ae924ff238e2acd0ace0d15d4c735ba11fbe8492afa91dfe25b", 1),
    ("307c43a114edff8f4566914ca820b3649d94a1b2148e6d1c9eac2f0f1a620565",
     "00890a0de2b522a8c483201c9ac620409eb2397e7c15a57c6dfccc73d148ac4e", 1),
    ("323b49071d93c0a13fc25a957c80ba5a82ba9b0f94c1ee5e3197a12d056c408e",
     "6ed44a37f0b7c495c01ef24fdb91cd469da2fbe5323c81e18db1a6355ce962c4", 1),
    ("2026-08-31-mainline-a72-expected-midr-model-guard-repair",
     "2026-08-31-mainline-a72-expected-pair-model-contract-repair", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-expected-midr-model-guard-repair", 1),',
     '("a72-isolation-held-result-contract-repair", "a72-expected-pair-model-contract-repair", 1),', 1),
    (".derived-execute-a72-expected-midr-model-guard-inner.XXXXXXXX",
     ".derived-execute-a72-expected-pair-model-contract-inner.XXXXXXXX", 1),
    ("expected-MIDR model-guard repair executor derivation",
     "expected-pair model-contract repair executor derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe expected-pair executor derivation: expected {count}, "
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
