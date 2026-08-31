#!/usr/bin/env bash

# Source-pin the bounded read-only P27 collector and retarget only the exact
# held-result repair candidate, tooling identities, and capture namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=1e90eef0bf3bac8342f474267ac321b9e04aa0ce89348946d48bb6fe0c9bb15c
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-30-mainline-a72-p27-runtime-attribution/scripts/collect-pretrigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-p27-held-result-repair.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", "fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5", 1),
    ("c7530fde97bc834bb6d8ae3e1a47ebbcffc21b1c78dbb9103c13bb9ef1198702", "a02558fed0305e53106588238c2f745f86554d4fad7485bc2222dc1dd3ccecc0", 1),
    ("d638ec37f77bcce968cf4a83a68ff7da6efbfaa0525487a13d9906560603abd9", "42ea9c05a9d02464aedd975dc3dc0cc87b2dd92c1f3b0f44ba9517745351dae0", 1),
    ("4513c845db329390eb778c07b866e723b3fba1638033536fcf5333958caef7a2", "4bc91d5bf53ebf45328d3b57838823a16b691cc6e0a2064bf6c3dad872915b25", 1),
    ("a72-p27-runtime-attribution", "a72-p27-held-result-contract-repair", 1),
    (".derived-collect-a72-p27-attribution.XXXXXXXX", ".derived-collect-a72-p27-held-result-repair-inner.XXXXXXXX", 1),
    ("P27 collector derivation", "held-result repair collector derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe held-result repair collector derivation: expected "
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
