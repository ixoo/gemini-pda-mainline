#!/usr/bin/env bash

# Source-pin the guarded READY-repair installer and retarget only the exact
# predecessor, closure candidate, artifact manifest, and evidence identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=e4b6fb412550ad542b486d6d5059681608f7b16e30718b63d2d0ea6c9e41244a
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-30-mainline-a72-ready-plan-expectation-repair/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-classification-closure.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ('("7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272", "9abdd1c66b8665ed7ccd0b9ca8e0cc7b74ddd40ebce65b2fb5d7a37aef6571cc", 1)', '("7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272", "2245c1c4056cfd849ff89ba8afa220bf0cf038f1ea23a324c1e717c6ea23d89b", 1)', 1),
    ('("726b622ab503e844e2faddb33fe357250df329510d5b3ab5877687f4db7bfcb0", "1c08f1fc9c2153965983eb469ea58babe7740fc4e3e7f14d799a060a44649d28", 1)', '("726b622ab503e844e2faddb33fe357250df329510d5b3ab5877687f4db7bfcb0", "9abdd1c66b8665ed7ccd0b9ca8e0cc7b74ddd40ebce65b2fb5d7a37aef6571cc", 1)', 1),
    ("7057b19fe6bdc4e2de15e6e0f86beeae6d5554c275a693a5a6a1e5b0a0dfcc67", "545535d3e8f0637e7704118911da95581c98326cffc203a569bdbb409053e24a", 1),
    ("candidate-a72-ready-plan-expectation-repair-982c4b50", "candidate-a72-classification-universe-closure-9caea8fe", 1),
    ('("a72-admission-trace", "a72-ready-plan-expectation-repair", 5)', '("a72-admission-trace", "a72-classification-universe-closure", 5)', 1),
    ("2026-08-30-mainline-a72-ready-plan-expectation-repair", "2026-08-30-mainline-a72-classification-universe-closure", 1),
    (".derived-install-a72-ready-plan-repair.XXXXXXXX", ".derived-install-a72-classification-closure-inner.XXXXXXXX", 1),
    ("unsafe READY-repair installer derivation", "unsafe classification-closure installer derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe classification-closure installer derivation: expected {count}, found {actual}: {old}"
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
