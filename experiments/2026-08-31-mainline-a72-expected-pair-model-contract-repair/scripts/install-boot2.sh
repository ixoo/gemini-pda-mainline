#!/usr/bin/env bash

# Source-pin the guarded live-GPT installer for the exact expected-pair
# repair candidate and require the stage-ledger predecessor on boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f1ec0f30e5b8374b39e35190f5e870e1402b7a6c4f5a0be58c18383dcc9de477
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-effect-plan-stage-ledger/scripts/install-boot2.sh"
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-expected-pair-model-contract.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1",
     "42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee", 1),
    (
        "     '     \\\"5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69\\\", 1),', 1),",
        "     '     \\\"b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1\\\", 1),', 1),",
        1,
    ),
    ("58124fd3397e82e4bb6c5568875b2326bc72ef43513b6b281e479777184f60b5",
     "25ef693ecaa6b1bf214d2f5948f146e1d95674cc8108562b7a48b1d687208474", 1),
    ("candidate-a72-effect-plan-stage-ledger-37de54a0",
     "candidate-a72-expected-pair-model-contract-repair-c66c24c6", 1),
    ("effect-plan-stage-ledger", "expected-pair-model-contract-repair", 2),
    ("effect-plan stage ledger", "expected-pair model-contract repair", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe expected-pair installer derivation: expected {count}, "
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
