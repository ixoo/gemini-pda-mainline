#!/usr/bin/env bash

# Source-pin the proven manual-checkpoint observer and specialize it for one
# unique prefix reason plus bounded changed-ID Gemian retained recovery.
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

derived="$(mktemp "$script_dir/.derived-manual-checkpoint-prefix-collector.XXXXXXXX")"
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
     "one exact prefix reason and serviceability pass", 1),
    ("114d637fdbfb7f7fd09f960f2b0b231a79ad12d60e8f9427dca2fb8d53a2f77e",
     "2c96d3b6a096b68bb18522fc35b7550f593d6e541c6ab33d7029810c4fec35dd", 2),
    ("ae39d5b4755c974c29f94b9c1b8ea909d278e52488d309e5e5ad74583d669dc8",
     "a4d88ba70410ab53529d1d74f5f342a6bb082043cd15a9f936426f9482c6dd48", 2),
    ("52dc1ec02e24cbedfe03623b3e177899b8b5abd4cb80df484cd035dd6632460a",
     "1f2f886225240b5cb738784cd88ed0499f0b97121830a3a8fc8468afddb7899a", 1),
    ("53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c",
     "ced1f56fc56833ce47b63a98205a373276f5d666007190ec0d3bd5adb98f3901", 2),
    ("manual-checkpoint-control-attempt-1", "manual-checkpoint-prefix-control-attempt-1", 3),
    ("manual-checkpoint-control", "manual-checkpoint-prefix-control", 1),
    ("__MANUAL_CHECKPOINT_CONTROL_RUNTIME_BEGIN__",
     "__MANUAL_CHECKPOINT_PREFIX_RUNTIME_BEGIN__", 1),
    ("__MANUAL_CHECKPOINT_CONTROL_RUNTIME_END__",
     "__MANUAL_CHECKPOINT_PREFIX_RUNTIME_END__", 1),
    ("manual-checkpoint-live-pass", "manual-checkpoint-prefix-pass", 2),
    ("writer-and-recovery-pass|live-pass-recovered-empty",
     "live-pass-recovered-empty", 1),
    (".derived-manual-checkpoint-collector.XXXXXXXX",
     ".derived-manual-checkpoint-prefix-collector-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe prefix collector derivation: expected {count}, found {actual}: {old}"
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
