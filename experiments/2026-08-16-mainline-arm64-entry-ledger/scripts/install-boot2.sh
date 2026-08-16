#!/usr/bin/env bash

# Source-pin and mechanically derive the guarded installer for the exact
# arm64 entry-ledger candidate. The inherited policy resolves live GPT boot2,
# records but does not back up the predecessor, verifies a full readback, and
# powers off after success.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=453aa8ae078ed328e6f5f7830ce4a33c8c0d3ff4adb7f6c5f73b3a83813a5216

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-16-mainline-pre-ramoops-ledger/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
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
    ("# pre-ramoops stage-ledger candidate.", "# arm64 entry-ledger candidate.", 2),
    ("ac849d9aca9454d5d6a29d25a67b5d27fcef94e16bb881f4d14db09d0d29d75f",
     "a81939b41a64a362744580bec559baecb3fe13938187f34b3f1b9ad5f09527f2", 1),
    ("dd3f68898dcae1c6c8167c3dd20d070d1e91dc42af23d15ac8308d4a9bec938c",
     "a52d34adf408fdd6f0a81c91b3845678d5c849f598aff8503d8d1a45916bd615", 1),
    ("candidate-pre-ramoops-ledger-00455398",
     "candidate-arm64-entry-ledger-1249d907", 1),
    ("pre-ramoops-ledger-deployment-", "arm64-entry-ledger-deployment-", 1),
    (r"\.gemini-pre-ramoops-ledger\.", r"\.gemini-arm64-entry-ledger\.", 1),
    ("/home/gemini/.gemini-pre-ramoops-ledger.XXXXXXXX",
     "/home/gemini/.gemini-arm64-entry-ledger.XXXXXXXX", 1),
    ("experiment=2026-08-16-mainline-pre-ramoops-ledger",
     "experiment=2026-08-16-mainline-arm64-entry-ledger", 1),
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
