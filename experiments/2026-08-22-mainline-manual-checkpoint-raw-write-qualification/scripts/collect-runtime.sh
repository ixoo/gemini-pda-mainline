#!/usr/bin/env bash

# Source-pin the proven manual-checkpoint observer and specialize it for one
# exact raw-write result plus bounded changed-ID Gemian retained recovery.
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

derived="$(mktemp "$script_dir/.derived-manual-checkpoint-raw-write-collector.XXXXXXXX")"
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
     "one exact raw record, local full readback, and serviceability pass", 1),
    ("114d637fdbfb7f7fd09f960f2b0b231a79ad12d60e8f9427dca2fb8d53a2f77e",
     "e4ece8ef8aab1b13cefbeee12dcfdf9e1fa39a03e24f69ef95185c9ced2a6aa3", 2),
    ("ae39d5b4755c974c29f94b9c1b8ea909d278e52488d309e5e5ad74583d669dc8",
     "e37b3dedc7897037fa76954e02c6d4175f3067b68b35dab2126bcbd520b893a5", 2),
    ("52dc1ec02e24cbedfe03623b3e177899b8b5abd4cb80df484cd035dd6632460a",
     "959bdc19902b158aa130719ccabe6ce0140bbc4432397c76c9da1b9e9b7d1e4f", 1),
    ("53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c",
     "c10f2c03490fe1aa8ded11895a2d1817dd649edaffa307d0635fe2d69ce1c631", 2),
    ("manual-checkpoint-control-attempt-1",
     "manual-checkpoint-raw-write-attempt-1", 3),
    ("manual-checkpoint-control", "manual-checkpoint-raw-write", 1),
    ("__MANUAL_CHECKPOINT_CONTROL_RUNTIME_BEGIN__",
     "__MANUAL_CHECKPOINT_RAW_WRITE_RUNTIME_BEGIN__", 1),
    ("__MANUAL_CHECKPOINT_CONTROL_RUNTIME_END__",
     "__MANUAL_CHECKPOINT_RAW_WRITE_RUNTIME_END__", 1),
    ("manual-checkpoint-live-pass",
     "manual-checkpoint-raw-write-live-pass", 2),
    ("writer-and-recovery-pass|live-pass-recovered-empty",
     "raw-writer-and-recovery-pass", 1),
    (".derived-manual-checkpoint-collector.XXXXXXXX",
     ".derived-manual-checkpoint-raw-write-collector-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe raw-write collector derivation: expected {count}, found {actual}: {old}"
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
