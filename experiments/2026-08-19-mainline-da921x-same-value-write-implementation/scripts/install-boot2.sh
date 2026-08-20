#!/usr/bin/env bash

# Source-pin the guarded installer for the exact same-value-write candidate.
# It resolves live GPT boot2, records but does not back up the predecessor,
# verifies a full readback, and powers off cleanly on success.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0cb1386ab3cd6d5af7565eddd39e853696f9c3133c12f403638a4eaa1f0fc1cb

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-18-mainline-da921x-runtime-preflight-ledger/scripts/install-boot2.sh"
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
    ("runtime-triggered preflight candidate", "same-value-write candidate", 1),
    ("af560eaad69b61239db7980995776b47b1194bb26fe5c8a24d8f1462008ab296",
     "b81813d13acc970c7b9203b89ec034921ef6f7e1017539a0c228754619af7b22", 1),
    ("f179790089e0eb9af6458d2bb2fdf71fe7fb37484e6de3adc708c919a4e843af",
     "e5e5ff3e0a1828e59381117d33ee539d2be19c7c234c5150fadea888e705b068", 1),
    ("candidate-mainline-da921x-runtime-preflight-5f1ce652",
     "candidate-mainline-da921x-same-value-write-b84f3ba8", 1),
    ("mainline-da921x-runtime-preflight-deployment-",
     "mainline-da921x-same-value-write-deployment-", 1),
    ("gemini-mainline-da921x-runtime-preflight",
     "gemini-mainline-da921x-same-value-write", 1),
    ("2026-08-18-mainline-da921x-runtime-preflight-ledger",
     "2026-08-19-mainline-da921x-same-value-write-implementation", 1),
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
