#!/usr/bin/env bash

# Source-pin the guarded diagnostic installer and retarget only the exact
# selector-mask repair successor, predecessor, manifest, and evidence labels.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=d0af2f8b15ad7fd430b5f53dc3fe818e8ca111d39bea640c13687c6ecd3b326a
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-sram-p28-terminal-diagnostic/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-selector-mask-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        '("e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", "7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3", 1),',
        '("e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", "cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743", 1),',
        1,
    ),
    ("a4fcb4e6465b2dec5a1e52fabeb9e6f69230cef7472e7cba981b5c6f8ce3df10", "ab432d011f00788c7a85c4bb8a1a980d3e1a50d4a2904c28d2d9cd6031a96cf0", 1),
    (
        '("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", "510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726", 1),',
        '("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", "7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3", 1),',
        1,
    ),
    ("candidate-a72-sram-p28-terminal-diagnostic-0e1be4e0", "candidate-a72-sram-selector-mask-contract-repair-add111ac", 1),
    ("experiment=2026-08-31-mainline-a72-sram-p28-terminal-diagnostic", "experiment=2026-08-31-mainline-a72-sram-selector-mask-contract-repair", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-sram-p28-terminal-diagnostic", 1),', '("a72-isolation-held-result-contract-repair", "a72-sram-selector-mask-contract-repair", 1),', 1),
    (".derived-install-a72-sram-p28-terminal-diagnostic-inner.XXXXXXXX", ".derived-install-a72-selector-mask-repair-inner.XXXXXXXX", 1),
    ("SRAM/P28 terminal diagnostic candidate", "SRAM selector-mask repair candidate", 1),
    ("SRAM/P28 diagnostic installer derivation", "selector-mask repair installer derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe selector-mask repair installer derivation: expected "
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
