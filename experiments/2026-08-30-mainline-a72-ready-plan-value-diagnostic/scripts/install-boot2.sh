#!/usr/bin/env bash

# Source-pin the guarded predicate-observer installer and retarget only the
# exact current predecessor, value candidate, artifact manifest, and evidence.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f852542a2a039a2df464ecae2699b2038dc383e1c6a327fb1a25e220874a7630
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-30-mainline-a72-ready-plan-predicate-diagnostic/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-ready-plan-value.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272", "1c08f1fc9c2153965983eb469ea58babe7740fc4e3e7f14d799a060a44649d28", 1),
    ("726b622ab503e844e2faddb33fe357250df329510d5b3ab5877687f4db7bfcb0", "7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272", 1),
    ("7c1fe27a46cd4280b54ece13b29b4309a47e14c0827fa140d49a26195413c050", "7568d7733b12e5c0ccbbad9f62c58ae51d92ee60246361f9f2f456a306beb6de", 1),
    ("candidate-a72-ready-plan-predicate-diagnostic-08eec751", "candidate-a72-ready-plan-value-diagnostic-42f760a7", 1),
    ('("a72-admission-trace", "a72-ready-plan-predicate-diagnostic", 5)', '("a72-admission-trace", "a72-ready-plan-value-diagnostic", 5)', 1),
    ("2026-08-30-mainline-a72-ready-plan-predicate-diagnostic", "2026-08-30-mainline-a72-ready-plan-value-diagnostic", 1),
    (".derived-install-a72-ready-plan-diagnostic.XXXXXXXX", ".derived-install-a72-ready-plan-value-inner.XXXXXXXX", 1),
    ("unsafe predicate-diagnostic installer derivation", "unsafe value-diagnostic installer derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe value-diagnostic installer derivation: expected {count}, found {actual}: {old}"
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
