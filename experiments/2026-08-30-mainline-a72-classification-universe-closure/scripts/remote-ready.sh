#!/usr/bin/env bash

# Materialize the exact read-only frame probe for the classification-universe
# closure candidate. It observes the READY contract and never sends a trigger.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=d59dc7827e8883370a38bc1aed7891e38e470785ece30185f82fa16a50e977a9
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-30-mainline-a72-ready-plan-expectation-repair/scripts/remote-ready.sh"
[[ -f "$source_probe" && ! -L "$source_probe" ]] || die 'source probe is missing or unsafe'
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source probe changed'

derived=$(mktemp "$script_dir/.derived-remote-a72-classification-closure.XXXXXXXX")
probe=$(mktemp "$script_dir/.materialized-remote-a72-classification-closure.XXXXXXXX")
cleanup() {
	[[ ! -e "${derived:-}" ]] || rm -f -- "$derived"
	[[ ! -e "${probe:-}" ]] || rm -f -- "$probe"
}
trap cleanup EXIT HUP INT TERM
python3 - "$source_probe" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("9abdd1c66b8665ed7ccd0b9ca8e0cc7b74ddd40ebce65b2fb5d7a37aef6571cc", "2245c1c4056cfd849ff89ba8afa220bf0cf038f1ea23a324c1e717c6ea23d89b", 1),
    (".derived-remote-a72-ready-plan-repair.XXXXXXXX", ".derived-remote-a72-classification-closure-inner.XXXXXXXX", 1),
    ("unsafe READY-repair remote derivation", "unsafe classification-closure remote derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe classification-closure remote derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@" >"$probe"
rc=$?
set -e
python3 - "$probe" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        "$BB printf 'ready_plan_diag_line='; $BB dmesg | $BB grep -Fm1 'A72_READY_PLAN_DIAG_V1 ' || true",
        "$BB printf 'ready_plan_diag_line='; $BB dmesg | $BB grep -Fm1 'A72_READY_PLAN_DIAG_V1 ' || $BB printf '\\n'",
        1,
    ),
    (
        "$BB printf 'ready_plan_values_line='; $BB dmesg | $BB grep -Fm1 'A72_READY_PLAN_VALUES_V1 ' || true",
        "$BB printf 'ready_plan_values_line='; $BB dmesg | $BB grep -Fm1 'A72_READY_PLAN_VALUES_V1 ' || $BB printf '\\n'",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe classification-closure probe repair: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
sys.stdout.write(text)
PY
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
