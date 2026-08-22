#!/usr/bin/env bash

# Source-pin the proven manual-checkpoint observer and specialize it for one
# unique fixed live stage plus bounded changed-ID Gemian retained recovery.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=6bb8454d416d710f3808770d9e8561a7341c578d9ae858299a9234787f94e5db

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-21-mainline-manual-checkpoint-control/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector identity changed'

derived="$(mktemp "$script_dir/.derived-manual-checkpoint-stage-collector.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("two local full readbacks and serviceability pass",
     "one fixed live stage and serviceability pass", 1),
    ("114d637fdbfb7f7fd09f960f2b0b231a79ad12d60e8f9427dca2fb8d53a2f77e",
     "df0b8ddfd46b91d75fd198c673b22a3764671a4d425318885599164a7248a3cf", 2),
    ("ae39d5b4755c974c29f94b9c1b8ea909d278e52488d309e5e5ad74583d669dc8",
     "a6a01f65a8a63c131d0e5af841a1e02d50f91f06ddac059cccc1b8621bfa98b1", 2),
    ("52dc1ec02e24cbedfe03623b3e177899b8b5abd4cb80df484cd035dd6632460a",
     "fdaa505ccab9d3be6851b8af5b6142eb043ef36b3b128a57655f0fefbc3382a6", 1),
    ("53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c",
     "43e7f44eeef694ef876f7686ae03e2a779a118141e7f9efa060ccc1182c8eac3", 2),
    ("manual-checkpoint-control-attempt-1", "manual-checkpoint-stage-control-attempt-1", 3),
    ("manual-checkpoint-control", "manual-checkpoint-stage-control", 1),
    ("__MANUAL_CHECKPOINT_CONTROL_RUNTIME_BEGIN__",
     "__MANUAL_CHECKPOINT_STAGE_RUNTIME_BEGIN__", 1),
    ("__MANUAL_CHECKPOINT_CONTROL_RUNTIME_END__",
     "__MANUAL_CHECKPOINT_STAGE_RUNTIME_END__", 1),
    ("manual-checkpoint-live-pass", "manual-checkpoint-stage-pass", 2),
    ("^retained_classification=(writer-and-recovery-pass|live-pass-recovered-empty)$",
     "^retained_classification=(writer-and-recovery-pass|writer-first-recovery-pass|live-pass-recovered-empty)$", 1),
    (".derived-manual-checkpoint-collector.XXXXXXXX",
     ".derived-manual-checkpoint-stage-collector-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage collector derivation: expected {count}, found {actual}: {old}"
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
