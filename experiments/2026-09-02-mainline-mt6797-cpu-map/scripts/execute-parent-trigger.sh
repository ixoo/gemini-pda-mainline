#!/usr/bin/env bash

# Spend the proven one-shot CPU8/CPU9 admission trigger on the exact CPU-map
# candidate while retaining the existing trigger and classifier semantics.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=4c472374115c49977c484e0b25be38d1c4e0b914c62da8cd196878cb617b2de7
readonly VALIDATOR_SHA256=9e1617b8121f33f45b67749fa0b5cf195557bbedd57b279ff47b800f0e9d5ab5
readonly CLASSIFIER_SHA256=c41d58cf60e0f5c769f195b28933b1349963f3523e86248fa197b59b718f58b1
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/execute-completion-lock-repair-trigger.sh"
[[ -f "$source_executor" && ! -L "$source_executor" ]] || die 'source completion-lock executor is absent or unsafe'
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source completion-lock executor changed'
source_dir=$(cd -- "$(dirname -- "$source_executor")" && pwd -P)
validator="$script_dir/validate-pretrigger.py"
[[ -f "$validator" && ! -L "$validator" ]] || die 'CPU-map pre-trigger validator is absent or unsafe'
[[ "$(sha256sum "$validator" | awk '{print $1}')" == "$VALIDATOR_SHA256" ]] || die 'CPU-map pre-trigger validator changed'
classifier="$script_dir/classify-parent-trigger.py"
[[ -f "$classifier" && ! -L "$classifier" ]] || die 'CPU-map trigger classifier is absent or unsafe'
[[ "$(sha256sum "$classifier" | awk '{print $1}')" == "$CLASSIFIER_SHA256" ]] || die 'CPU-map trigger classifier changed'

derived=$(mktemp "$source_dir/.derived-execute-mt6797-cpu-map-parent.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e",
     "68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393", 1),
    ("d86e78db5996f96b0e11efebd044454719ca8f0a6636671e72a405e1047499aa",
     "9e1617b8121f33f45b67749fa0b5cf195557bbedd57b279ff47b800f0e9d5ab5", 1),
    ("b10dcf6a1f7d495b012e856d45ae04047a2ad70be5d8280724336adf9c82f536",
     "c41d58cf60e0f5c769f195b28933b1349963f3523e86248fa197b59b718f58b1", 1),
    ("a72-cpu9-completion-lock-pretrigger-attempt-1",
     "a72-mt6797-cpu-map-attempt-1", 1),
    ('validator="$script_dir/validate-completion-lock-repair-pretrigger.py"',
     'validator="$repo_root/experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/validate-pretrigger.py"', 1),
    ('classifier="$script_dir/classify-completion-lock-repair-attempt.py"',
     'classifier="$repo_root/experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/classify-parent-trigger.py"', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU-map parent-executor derivation: expected {count}, "
            f"found {actual}: {old}"
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
