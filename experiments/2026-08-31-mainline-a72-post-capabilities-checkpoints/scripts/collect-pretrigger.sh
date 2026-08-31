#!/usr/bin/env bash

# Source-pin the bounded collector and retarget the exact post-capabilities
# candidate, read-only probe, validator, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f60886d0ea8cfe462a48b3fdfcd2ddd1ca03e1f436a3239fd035a290715f0e9a
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-31-mainline-a72-secondary-entry-checkpoints/scripts/collect-pretrigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-post-capabilities-checkpoints.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("6d0bf75b55ef981a915ba0b9a8d305d5713476acc4fc2ee95e4201f234b2253f",
     "9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630", 1),
    ("21fe26af7995e50cd9f4e50eecc299ed03a2da87fbb3e81b10c469b227d0b329",
     "f0f558ce82cd712a84f5b6adc4a3b2ee48e370c42669489dd1dad6a108413772", 1),
    ("7ff62048fe01c6c6a231b6d9b4af0c5b8d8b654b10e156a50fe29eb9200d48a8",
     "9c722be18bb41ebf164e96d396014572d79bac24c2c8be6814d98bdb39edc0f8", 1),
    ("b79bf294e197345061afda682da56afdafaf9540a1dbc3e3db7a2c2e36e4923d",
     "6b2949fddca6c2001ed75cd11321f66ddbff253e4daf520f2554b4cbee26b407", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-secondary-entry-checkpoints", 1),',
     '("a72-isolation-held-result-contract-repair", "a72-post-capabilities-checkpoints", 1),', 1),
    (".derived-collect-a72-secondary-entry-checkpoints-inner.XXXXXXXX",
     ".derived-collect-a72-post-capabilities-checkpoints-inner.XXXXXXXX", 1),
    ("secondary-entry checkpoint collector derivation",
     "post-capabilities checkpoint collector derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe post-capabilities collector derivation: expected "
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
