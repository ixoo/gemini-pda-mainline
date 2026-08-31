#!/usr/bin/env bash

# Source-pin the guarded isolation-result installer and retarget only the exact
# SRAM/P28 diagnostic successor, predecessor, manifest, ledger, and evidence.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=1d2eb1a64744781504b75e601b9e5b97280887cec3b6264872f8207c55b6fe7d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-30-mainline-a72-isolation-held-result-contract-repair/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-sram-p28-terminal-diagnostic.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        '("e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", "510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726", 1),',
        '("e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", "7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3", 1),',
        1,
    ),
    ("4d1607238546ef4d01e8f15ee0d787108b24b220edc181f21f9fcb68cd92f64d", "a4fcb4e6465b2dec5a1e52fabeb9e6f69230cef7472e7cba981b5c6f8ce3df10", 1),
    (
        '("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", "fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5", 1),',
        '("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", "510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726", 1),',
        1,
    ),
    ("candidate-a72-isolation-held-result-contract-repair-53b52ffc", "candidate-a72-sram-p28-terminal-diagnostic-0e1be4e0", 1),
    ("experiment=2026-08-30-mainline-a72-isolation-held-result-contract-repair", "experiment=2026-08-31-mainline-a72-sram-p28-terminal-diagnostic", 1),
    ("a72-isolation-held-result-contract-repair", "a72-sram-p28-terminal-diagnostic", 1),
    (".derived-install-a72-isolation-held-result-repair-inner.XXXXXXXX", ".derived-install-a72-sram-p28-terminal-diagnostic-inner.XXXXXXXX", 1),
    ("isolation held-result repair candidate", "SRAM/P28 terminal diagnostic candidate", 1),
    ("isolation held-result repair installer derivation", "SRAM/P28 diagnostic installer derivation", 2),
    ("4442474348000000480000004737544c09000100010000000000000007000000", "4442474348000000480000004737544c09000100010000000000000009000000", 1),
    ("010000000400000000000000b044268b4737544c090001000100000000000000", "01000000050000000000000085b20e674737544c090001000100000000000000", 1),
    ("08000000030000000400000004000000422a9566", "0a000000030000000500000004000000bf0f9f2d", 1),
    ("transition_ledger_latest_generation=8", "transition_ledger_latest_generation=10", 1),
    ("transition_ledger_latest_stage=4", "transition_ledger_latest_stage=5", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe SRAM/P28 diagnostic installer derivation: expected "
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
