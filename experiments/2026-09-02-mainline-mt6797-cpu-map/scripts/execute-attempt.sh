#!/usr/bin/env bash

# Source-pin the proven one-shot admission plus volatile-RAM executor and
# retarget it to the exact CPU-map candidate and corrected topology oracle.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=d8f307cd3e9753031d9915091a740c2b7aabcf2aa02f5ffb071bd5cbc6d9bf4e
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-09-02-mainline-dual-a72-ram-coherency/scripts/execute-attempt.sh"
[[ -f "$source_executor" && ! -L "$source_executor" ]] || die 'source RAM executor is absent or unsafe'
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source RAM executor changed'

derived=$(mktemp "$script_dir/.derived-execute-mt6797-cpu-map.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old_parent_derivation = '''text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "a72-cpu9-completion-lock-pretrigger-attempt-1"
new = "a72-dual-ram-coherency-attempt-1"
if text.count(old) != 1:
    raise SystemExit("unsafe parent-executor derivation")
Path(sys.argv[2]).write_text(text.replace(old, new), encoding="utf-8")'''
new_parent_derivation = '''Path(sys.argv[2]).write_bytes(Path(sys.argv[1]).read_bytes())'''
if text.count(old_parent_derivation) != 1:
    raise SystemExit("unsafe CPU-map parent-executor copy derivation")
text = text.replace(old_parent_derivation, new_parent_derivation)
replacements = (
    ("370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e",
     "68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393", 1),
    ("4c472374115c49977c484e0b25be38d1c4e0b914c62da8cd196878cb617b2de7",
     "12317b5e6e0d3ad32982d9fb90e37b9f656d2a202fb49e59b126ac75be48449f", 1),
    ("5cf2730d41d12f1b18860acdd3e85f7d58f565bc2c1fe28857d4e5a83810ba08",
     "daf71fbd3badf5a646afb042730205889624ff03751afe845f69c572a93fea46", 1),
    ("a5892bfb0d72d176344c93f2ec389e35c5c5f8d7253ac40b61a11d645c39d888",
     "2cd81b4ee24e5575fd22ec8330f351678c3b6f46a054c6fe0b481d4d192f7319", 1),
    ("a72-dual-ram-coherency-attempt-1", "a72-mt6797-cpu-map-attempt-1", 1),
    ("runtime_classification=dual-a72-ram-integrity-pass",
     "runtime_classification=mt6797-4+4+2-topology-and-dual-a72-ram-integrity-pass", 2),
    ('source_executor="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/execute-completion-lock-repair-trigger.sh"',
     'source_executor="$script_dir/execute-parent-trigger.sh"', 1),
    ('remote_wrapper="$script_dir/remote-bounded-ram-coherency.sh"',
     'remote_wrapper="$script_dir/remote-bounded-topology-ram.sh"', 1),
    ("__GEMINI_A72_RAM_COHERENCY_SCRIPT__", "__GEMINI_MT6797_TOPOLOGY_RAM_SCRIPT__", 1),
    ("experiment=2026-09-02-mainline-dual-a72-ram-coherency",
     "experiment=2026-09-02-mainline-mt6797-cpu-map", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU-map attempt-executor derivation: expected {count}, "
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
