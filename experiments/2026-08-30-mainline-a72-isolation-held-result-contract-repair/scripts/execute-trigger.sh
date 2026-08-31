#!/usr/bin/env bash

# Source-pin the boot-bound one-shot executor and retarget only the exact
# isolation-result repair candidate, tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=bb648b275130accdaa3bb9dfa8491562c1a526cf0e9e964df2b30ce6f400591d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-30-mainline-a72-p27-held-result-contract-repair/scripts/execute-trigger.sh"
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-isolation-held-result-repair.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5", "510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726", 1),
    ("eb468b61306d21175d5f758d8c0e682ab549bf8757ccbef0c3955beb4ebbc009", "b609a64e41d664167912dd0156c45c3428a13b0c9495deab8317ca9288611508", 1),
    ("1d18274509912d1178baa329a57c31593458404ed022cf3980a19aac6cef57c8", "69034fd59cfee5a8d5ae34bd23a55ef199bcbe61007b763fef014762eb45bfe3", 1),
    ("4bc91d5bf53ebf45328d3b57838823a16b691cc6e0a2064bf6c3dad872915b25", "c75c6c43f30f9b029b94aeb3ce17229f51fa26f20d08087b0208fed3a0926b2e", 1),
    ("2026-08-30-mainline-a72-p27-held-result-contract-repair", "2026-08-30-mainline-a72-isolation-held-result-contract-repair", 1),
    ("a72-p27-held-result-contract-repair", "a72-isolation-held-result-contract-repair", 1),
    (".derived-execute-a72-p27-held-result-repair-inner.XXXXXXXX", ".derived-execute-a72-isolation-held-result-repair-inner.XXXXXXXX", 1),
    ("held-result repair executor derivation", "isolation-result repair executor derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe isolation-result repair executor derivation: expected "
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
