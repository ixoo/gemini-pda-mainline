#!/usr/bin/env bash

# Source-pin the bounded collector and retarget the exact stage-ledger
# candidate, expanded read-only probe, validator, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f66b0a5137226728768b44c77761bc2a1bd9f177093448574707977a4e3b160c
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-31-mainline-a72-expected-midr-model-guard-repair/scripts/collect-pretrigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-effect-plan-stage-ledger.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69",
     "b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1", 1),
    ("80e9a7220f329ce54d24101ce9ce73123af0e9d642b423a61a4709646f355dbb",
     "2b6ed5dbcea25613ea5bef0b66f4500bf2d1b0b17d5eae49fe279e1cacb97406", 1),
    ("2ff487b51656909fcc04d0b8a4c5503844dd3f9589f86bd32e8e6ba9bbb512d2",
     "868349708c241796ef9fac702e0e0bec8782a7f5a992b0e9ab42ab34ad8ba9d2", 1),
    ("323b49071d93c0a13fc25a957c80ba5a82ba9b0f94c1ee5e3197a12d056c408e",
     "20feaad24a8fb68f1f4d6a77d2457c36749aa5feeea88667e3118a4781ad11c5", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-expected-midr-model-guard-repair", 1),',
     '("a72-isolation-held-result-contract-repair", "a72-effect-plan-stage-ledger", 1),', 1),
    (".derived-collect-a72-expected-midr-model-guard-inner.XXXXXXXX",
     ".derived-collect-a72-effect-plan-stage-ledger-inner.XXXXXXXX", 1),
    ("expected-MIDR model-guard repair collector derivation",
     "effect-plan stage-ledger collector derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage-ledger collector derivation: expected {count}, "
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
