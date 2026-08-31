#!/usr/bin/env bash

# Source-pin the P27 boot-bound one-shot executor and retarget only the exact
# repaired candidate, local tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=97052688eec42423f8bdaf6d8f4faa03efdda2eeccc10999796cba360de5348f
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-30-mainline-a72-p27-runtime-attribution/scripts/execute-trigger.sh"
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-p27-held-result-repair.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", "fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5", 1),
    ("d8016c61216d16a64d35850eb6ec95a4dd011b1dae62afedd7345de2a41caa81", "eb468b61306d21175d5f758d8c0e682ab549bf8757ccbef0c3955beb4ebbc009", 1),
    ("ee53bef775ae2b3c16a77de63e916dfda06fca22cd871a62f37cf065f1badb1f", "1d18274509912d1178baa329a57c31593458404ed022cf3980a19aac6cef57c8", 1),
    ("4513c845db329390eb778c07b866e723b3fba1638033536fcf5333958caef7a2", "4bc91d5bf53ebf45328d3b57838823a16b691cc6e0a2064bf6c3dad872915b25", 1),
    ("2026-08-30-mainline-a72-p27-runtime-attribution", "2026-08-30-mainline-a72-p27-held-result-contract-repair", 1),
    ("a72-p27-runtime-attribution", "a72-p27-held-result-contract-repair", 1),
    (".derived-execute-a72-p27-attribution.XXXXXXXX", ".derived-execute-a72-p27-held-result-repair-inner.XXXXXXXX", 1),
    ("P27 executor derivation", "held-result repair executor derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe held-result repair executor derivation: expected "
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
