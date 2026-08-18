#!/usr/bin/env bash

# Source-pin the guarded installer for the exact runtime-triggered preflight
# candidate. The inherited policy resolves live GPT boot2, records but does not
# back up the predecessor, verifies a full readback, and powers off on success.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=056e651ff233d792a6cc4097ad57d6561eb0ce1220041eb19cd06c1e2d6206d5

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-17-mainline-da921x-readonly-preflight-ledger/scripts/install-boot2.sh"
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
    ("read-only preflight candidate", "runtime-triggered preflight candidate", 1),
    ("41c652225d3627f5aaaba2272e29a58171008e17b0f7c936116842e7ab0166e3",
     "af560eaad69b61239db7980995776b47b1194bb26fe5c8a24d8f1462008ab296", 1),
    ("680e1b66939fa2536b87d8766c781a5bf7f3e42c2ad398031814a3c4560d58de",
     "f179790089e0eb9af6458d2bb2fdf71fe7fb37484e6de3adc708c919a4e843af", 1),
    ("candidate-mainline-da921x-preflight-4a0c4406",
     "candidate-mainline-da921x-runtime-preflight-5f1ce652", 1),
    ("mainline-da921x-preflight-deployment-",
     "mainline-da921x-runtime-preflight-deployment-", 1),
    ("gemini-mainline-da921x-preflight", "gemini-mainline-da921x-runtime-preflight", 2),
    ("2026-08-17-mainline-da921x-readonly-preflight-ledger",
     "2026-08-18-mainline-da921x-runtime-preflight-ledger", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe installer derivation: expected {count}, found {actual}: {old}"
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
