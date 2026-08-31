#!/usr/bin/env bash

# Source-pin the bounded collector and retarget the exact r0p1 candidate,
# read-only probe, validator, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=154ca26d50d6568e13d1277cac9d33b43423c386fb34b01313d1b1806f4ab394
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-31-mainline-a72-post-capabilities-checkpoints/scripts/collect-pretrigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-r0p1-expected-pair-repair.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630",
     "b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d", 1),
    ("f0f558ce82cd712a84f5b6adc4a3b2ee48e370c42669489dd1dad6a108413772",
     "9c4491e18cac8b403fa120cfd3f6c31735b3079130d9e02d8594f1aa2b31b8a2", 1),
    ("9c722be18bb41ebf164e96d396014572d79bac24c2c8be6814d98bdb39edc0f8",
     "ec7f4879fb4f52c38d86fe7aeedda87453fcfec41c27c86618e4b3b0dbaad506", 1),
    ("6b2949fddca6c2001ed75cd11321f66ddbff253e4daf520f2554b4cbee26b407",
     "c0426f2c197df439ef7108082c12d72a70b0c36722d7828952706bf3de508ab3", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-post-capabilities-checkpoints", 1),',
     '("a72-isolation-held-result-contract-repair", "a72-r0p1-expected-pair-repair", 1),', 1),
    (".derived-collect-a72-post-capabilities-checkpoints-inner.XXXXXXXX",
     ".derived-collect-a72-r0p1-expected-pair-repair-inner.XXXXXXXX", 1),
    ("post-capabilities checkpoint collector derivation",
     "r0p1 expected-pair repair collector derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe r0p1 collector derivation: expected {count}, "
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
