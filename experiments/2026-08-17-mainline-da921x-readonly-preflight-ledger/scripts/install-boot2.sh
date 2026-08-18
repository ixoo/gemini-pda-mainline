#!/usr/bin/env bash

# Source-pin the guarded installer for the exact DA921x read-only preflight
# candidate. The inherited policy resolves live GPT boot2, records but does not
# back up the predecessor, verifies a full readback, and powers off on success.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a4e78786d6869e1ebabe8f2a8749a913bb3876131eb968a1436321963ce9782a

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-17-mainline-da921x-readonly-provider-baseline/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("read-only DA921x provider candidate",
     "DA921x read-only preflight candidate", 1),
    ("eeee7adea53134c8146e10591708725649a8331bdef7ad418a847b5d04c8e854",
     "41c652225d3627f5aaaba2272e29a58171008e17b0f7c936116842e7ab0166e3", 1),
    ("2a1c84683bf63f2e93c9e36d9679f3cc9858b787ac4c0a4933a1ea912a92b64b",
     "680e1b66939fa2536b87d8766c781a5bf7f3e42c2ad398031814a3c4560d58de", 1),
    ("candidate-mainline-da921x-lkro-provider-ab86ce39",
     "candidate-mainline-da921x-preflight-4a0c4406", 1),
    ("mainline-da921x-lkro-provider-deployment-",
     "mainline-da921x-preflight-deployment-", 1),
    (r"\.gemini-mainline-da921x-lkro-provider\.",
     r"\.gemini-mainline-da921x-preflight\.", 1),
    ("/home/gemini/.gemini-mainline-da921x-lkro-provider.XXXXXXXX",
     "/home/gemini/.gemini-mainline-da921x-preflight.XXXXXXXX", 1),
    ("experiment=2026-08-17-mainline-da921x-readonly-provider-baseline",
     "experiment=2026-08-17-mainline-da921x-readonly-preflight-ledger", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe installer derivation: expected {count} occurrences, found {actual}: {old}"
        )
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
