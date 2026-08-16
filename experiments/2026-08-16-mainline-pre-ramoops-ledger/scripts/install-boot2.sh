#!/usr/bin/env bash

# Source-pin and mechanically derive the guarded installer for the exact
# pre-ramoops stage-ledger candidate. The inherited policy resolves live GPT
# boot2, records but does not back up the predecessor, verifies a full
# readback, and powers off after success.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a8eb584d947cb101941be5c02548e442c47ffaf3d5ace6fa31941a69bd335c4c

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-15-mainline-post-ramoops-checkpoint/scripts/install-boot2.sh"
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
    ("# post-ramoops checkpoint candidate.", "# pre-ramoops stage-ledger candidate.", 2),
    ("ae6b354d51a9e5096b9f6f74ee9037c47ba026e00895e6f4c8028f15bc9bd348",
     "ac849d9aca9454d5d6a29d25a67b5d27fcef94e16bb881f4d14db09d0d29d75f", 1),
    ("a375c3c99ad4a7531e93343e3676c109fe2aadc2a0f1821d940fcb1a603b829d",
     "dd3f68898dcae1c6c8167c3dd20d070d1e91dc42af23d15ac8308d4a9bec938c", 1),
    ("candidate-post-ramoops-checkpoint-e16405f0",
     "candidate-pre-ramoops-ledger-00455398", 1),
    ("post-ramoops-checkpoint-deployment-", "pre-ramoops-ledger-deployment-", 1),
    (r"\.gemini-post-ramoops-checkpoint\.", r"\.gemini-pre-ramoops-ledger\.", 1),
    ("/home/gemini/.gemini-post-ramoops-checkpoint.XXXXXXXX",
     "/home/gemini/.gemini-pre-ramoops-ledger.XXXXXXXX", 1),
    ("experiment=2026-08-15-mainline-post-ramoops-checkpoint",
     "experiment=2026-08-16-mainline-pre-ramoops-ledger", 1),
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
