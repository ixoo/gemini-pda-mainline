#!/usr/bin/env bash

# Source-pin the guarded live-GPT installer for the exact stage-ledger
# candidate and require the exact model-guard predecessor on boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f3e9f234f4405dce89882371199f0c4ea0d704fd437b1bbf0705be42431c688d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-expected-midr-model-guard-repair/scripts/install-boot2.sh"
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-effect-plan-stage-ledger.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69",
     "b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1", 1),
    (
        "     '     \"b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d\", 1),', 1),",
        "     '     \"5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69\", 1),', 1),",
        1,
    ),
    ("ee5eefe99d8940598a0a4218a34b16a460fab684daf580d4ae8b5f0813d5c22b",
     "58124fd3397e82e4bb6c5568875b2326bc72ef43513b6b281e479777184f60b5", 1),
    ("candidate-a72-expected-midr-model-guard-repair-bf7ebec8",
     "candidate-a72-effect-plan-stage-ledger-37de54a0", 1),
    ("expected-midr-model-guard-repair", "effect-plan-stage-ledger", 1),
    ("expected-MIDR model-guard repair", "effect-plan stage ledger", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage-ledger installer derivation: expected {count}, "
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
