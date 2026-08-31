#!/usr/bin/env bash

# Source-pin the boot-bound executor and retarget the exact checkpoint
# candidate, ABI-4 tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0dd7ba7f23711a7510f118fb67610e582ede842a4365c5d0b69c806b81d70db0
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-31-mainline-a72-p30e-ready-identity-repair/scripts/execute-trigger.sh"
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-secondary-entry-checkpoints.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16", "6d0bf75b55ef981a915ba0b9a8d305d5713476acc4fc2ee95e4201f234b2253f", 1),
    ("93cee6501a6224b2c3c2e944c3701f7523c029f17ea55de822689cc49423e68d", "2a203083e9034b04e963f30e6bff557863f41287aff55ca1e3ce43d0152e5777", 1),
    ("6b896c649c7c296a81833d769e763e1964bc359f6e6d002253d063a8d1683e25", "39866fc11d957c4e1d2cb9f7e2f58f6ca6659793896a30f23cbfb3a383c9589b", 1),
    ("05accc9657be8268b0602216324919efa193243c61ad2ae78bdc2a6e3734304d", "b79bf294e197345061afda682da56afdafaf9540a1dbc3e3db7a2c2e36e4923d", 1),
    ("2026-08-31-mainline-a72-p30e-ready-identity-repair", "2026-08-31-mainline-a72-secondary-entry-checkpoints", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-p30e-ready-identity-repair", 1),', '("a72-isolation-held-result-contract-repair", "a72-secondary-entry-checkpoints", 1),', 1),
    (".derived-execute-a72-p30e-ready-identity-repair-inner.XXXXXXXX", ".derived-execute-a72-secondary-entry-checkpoints-inner.XXXXXXXX", 1),
    ("P30E READY-identity executor derivation", "secondary-entry checkpoint executor derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe checkpoint executor derivation: expected "
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
