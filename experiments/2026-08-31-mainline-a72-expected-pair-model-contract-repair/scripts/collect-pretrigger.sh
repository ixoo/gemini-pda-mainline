#!/usr/bin/env bash

# Source-pin the bounded collector and retarget the exact expected-pair
# candidate, read-only probe, validator, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=5471328f1fd765841e492a0ebea7648ba8461840b0ea3ef70d145a59ea8ed279
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-31-mainline-a72-effect-plan-stage-ledger/scripts/collect-pretrigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-expected-pair-model-contract.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1",
     "42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee", 1),
    ("2b6ed5dbcea25613ea5bef0b66f4500bf2d1b0b17d5eae49fe279e1cacb97406",
     "a303ab237d22d2ae55d1df656cd963698152937dc7d122f87f5896eb7c7ae561", 1),
    ("868349708c241796ef9fac702e0e0bec8782a7f5a992b0e9ab42ab34ad8ba9d2",
     "56e3800749e7c6ba7c791db349a5a11d81f4e293ba8d983c15b858a6f51e6616", 1),
    ("20feaad24a8fb68f1f4d6a77d2457c36749aa5feeea88667e3118a4781ad11c5",
     "6ed44a37f0b7c495c01ef24fdb91cd469da2fbe5323c81e18db1a6355ce962c4", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-effect-plan-stage-ledger", 1),',
     '("a72-isolation-held-result-contract-repair", "a72-expected-pair-model-contract-repair", 1),', 1),
    (".derived-collect-a72-effect-plan-stage-ledger-inner.XXXXXXXX",
     ".derived-collect-a72-expected-pair-model-contract-inner.XXXXXXXX", 1),
    ("effect-plan stage-ledger collector derivation",
     "expected-pair model-contract collector derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe expected-pair collector derivation: expected {count}, "
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
