#!/usr/bin/env bash

# Source-pin the bounded read-only collector and retarget only the exact
# isolation-result repair candidate, tooling identities, and capture namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=bf12250f511a07bd4d96fc1133fd6333f45bcd98e2f07b662b37280c62001de2
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-30-mainline-a72-p27-held-result-contract-repair/scripts/collect-pretrigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-isolation-held-result-repair.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5", "510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726", 1),
    ("a02558fed0305e53106588238c2f745f86554d4fad7485bc2222dc1dd3ccecc0", "feb927cd43bc54b32bd4cedfc2da8164e83f5b722cdae636feaedfa3fc3a3d78", 1),
    ("42ea9c05a9d02464aedd975dc3dc0cc87b2dd92c1f3b0f44ba9517745351dae0", "20b11cebf6950f8f241b46dd1b2775e9ab872b3eefed3c6b45cf65355fff56a1", 1),
    ("4bc91d5bf53ebf45328d3b57838823a16b691cc6e0a2064bf6c3dad872915b25", "c75c6c43f30f9b029b94aeb3ce17229f51fa26f20d08087b0208fed3a0926b2e", 1),
    ("a72-p27-held-result-contract-repair", "a72-isolation-held-result-contract-repair", 1),
    (".derived-collect-a72-p27-held-result-repair-inner.XXXXXXXX", ".derived-collect-a72-isolation-held-result-repair-inner.XXXXXXXX", 1),
    ("held-result repair collector derivation", "isolation-result repair collector derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe isolation-result repair collector derivation: expected "
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
