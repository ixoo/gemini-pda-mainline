#!/usr/bin/env bash

# Source-pin the bounded P30E collector and retarget its exact candidate,
# corrected blocker probe, validator, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=87791fd805c416d1b0dce594462ebcab7e49536f44ce74d1f903debba740a2be
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-31-mainline-a72-p30e-entry-diagnostic/scripts/collect-pretrigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-p30e-ready-identity-repair.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453", "459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16", 1),
    ("742a8322254f617efe07ffff6265720cbeebe647edc3d1f0f77f087a5fb9a685", "57f7c9dc2ff66143c4297d02fd689b34f01126cacf8141e92e137327eaf297c0", 1),
    ("af527e6224d68f731534b5d14001c3d10070c62828bc3d59188c55495c992efd", "ca217011846721e9366c7be5fe41e5f74e633d71c3bbb6f99531f046c6238f46", 1),
    ("f3f4067fdb365ea0fc5eee7c2b0176ddb45c69c5ddf68ddf886aad64e3995a7f", "05accc9657be8268b0602216324919efa193243c61ad2ae78bdc2a6e3734304d", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-p30e-entry-diagnostic", 1),', '("a72-isolation-held-result-contract-repair", "a72-p30e-ready-identity-repair", 1),', 1),
    (".derived-collect-a72-p30e-entry-diagnostic-inner.XXXXXXXX", ".derived-collect-a72-p30e-ready-identity-repair-inner.XXXXXXXX", 1),
    ("P30E entry collector derivation", "P30E READY-identity collector derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E READY-identity collector derivation: expected "
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
