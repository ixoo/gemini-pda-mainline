#!/usr/bin/env bash

# Source-pin the bounded collector and retarget only the selector-mask repair
# candidate, tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0a7e0ceca281677f97aa2d754f3c7662d64790d9026925442f4a10e67cc4ec0f
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-31-mainline-a72-sram-p28-terminal-diagnostic/scripts/collect-pretrigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-selector-mask-repair.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3", "cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743", 1),
    ("e0cf19260f8542d33fe5f143310247748966adb6e9ce1ab8db595bd60d2e0165", "23177682a61122b6055aba518d15e803c207b828f2d4c4d41cc3f332b9dccd14", 1),
    ("a9d5c1a38363ed6c5fe722e093f8f7fa35833eddce6f232f5b927931e448fe77", "1de4be12c413b5b46cc57abc3e54ed0b8bbb286ab3f09959c834e297df8f077e", 1),
    ("644e0253a08586eed1579e52f865a488912f5b875663fbabfb2417442dd6d54f", "a22f33457be8bae80b32f60ff01026dbe49410368d73c76c1da74a57c21ae04d", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-sram-p28-terminal-diagnostic", 1),', '("a72-isolation-held-result-contract-repair", "a72-sram-selector-mask-contract-repair", 1),', 1),
    (".derived-collect-a72-sram-p28-terminal-diagnostic-inner.XXXXXXXX", ".derived-collect-a72-selector-mask-repair-inner.XXXXXXXX", 1),
    ("SRAM/P28 diagnostic collector derivation", "selector-mask repair collector derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe selector-mask repair collector derivation: expected "
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
