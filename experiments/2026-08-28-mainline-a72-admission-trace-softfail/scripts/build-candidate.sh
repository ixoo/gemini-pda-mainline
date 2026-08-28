#!/usr/bin/env bash

# Source-pin the independently validated durable admission builder and retarget
# only its exact package, trace-softfail gates, LK identity, and output hashes.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=e7966c2251c290e3d3a4c2d39da247977e62568366b2c8dff61ad7d0de7c5610
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-28-mainline-a72-admission-durable-candidate/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-admission-softtrace.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("eb87d46ae9d58df1ff336751103745d58eed59fe",
     "f89406beccd35e179f31a0c6be8ae1e5f4667318", 1),
    ("7.1.3-gemini-a72-admission-trace",
     "7.1.3-gemini-a72-admission-softtrace", 1),
    ("a72-admission-durable-candidate", "a72-admission-trace-softfail-candidate", 4),
    ("linux-7.1.3-gemini-a72-admission-trace-softfail-candidate-13dd59d3-a15d3567",
     "linux-7.1.3-gemini-a72-admission-trace-softfail-candidate-e5ce5cc2-bc0b48a2", 1),
    ("3468c9ccc8c5e965980d283e4e441ab78ca6531a5a44e989ff4d742285f2f3b3",
     "fb088c46775add2d91b0ebec430d632db21f36459f2c97804648394f296f77df", 1),
    ("05c9f1960ac315baf4d20b37f126a7fc700acfc137f5e977650cf916395c3d3b",
     "5b6cc87a4ec5683a0af848f6ca32487440f7bc32663c783718ce4e8374602dd7", 1),
    ("d59b56cfe259fdc4294a3d51c7dcab66ba4b5270bf4b6ea526763fd4dc534c89",
     "04c2e336ef3b9de84b1c27354ec9d1289d6c096b93e70b9e549ee126fb6cbc1b", 1),
    ("f9d1242a102c4a0e5544991ab8d9f7bd5263e158f0ec5d07d41368fbbc701585",
     "86e0379376d5b6cdddb5c66c121fd918c8deaf245f683c2f325803ea30cf2899", 1),
    ("d02a8aa8ac144fb590ac4515a1bce4b67d8286fa1bc857bf5135daa4b59d29c5",
     "9d9ace53a0f2e91e4f79a297e4336047842d2661192712b5498e8f5a4ed7a62c", 1),
    ("27d550c7c88a49331d325ed1cf8dfba64dd6ed2f8fc3ae83c66f7301ea3a0604",
     "5271cc4348f0c0208f04172d34053cf2742f87143e29c5a261e5f4bd9bff3f04", 1),
    ("ed6fc5294f5677ed1895bf1157649330c91dd1f6051a6677f2d26972915cd185",
     "9d1912aa3055d0835831a9376aec141329e5809fd833359f5baaeb6ad033fd40", 1),
    ("60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1",
     "83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0", 1),
    ("readonly RAW_SIZE=6934528", "readonly RAW_SIZE=6942720", 1),
    ("gemini-a72adm", "gemini-a72soft", 1),
    ("gemini-mt6797-a72-admission-trace.boot.img",
     "gemini-mt6797-a72-admission-softtrace.boot.img", 1),
    (".a72-admission.XXXXXXXX", ".a72-admission-softtrace.XXXXXXXX", 1),
    ('\t\'CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER=y\' \\\n'
     "\t'CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER=y' \\\n",
     '\t\'CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER=y\' \\\n'
     '\t\'CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y\' \\\n'
     "\t'CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER=y' \\\n", 1),
    ('CONFIG_LOCALVERSION="-gemini-a72-admission-trace"',
     'CONFIG_LOCALVERSION="-gemini-a72-admission-softtrace"', 1),
    ("marker='GEMINI_A72_ADMISSION_V1 state=terminal ret=%d consumed=1 requests=%u/0/0 retries=0'\n"
     '[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d \' \')" == 1 ]] ||\n'
     "\tdie 'admission runtime marker is not unique'",
     "for marker in \\\n"
     "\t'GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 trigger_executions=0 core_consumed=0 requests=0/0/0 retries=0' \\\n"
     "\t'GEMINI_A72_ADMISSION_LIVE_V1 state=terminal operation_ret=%d core_consumed=%d entry_trace_ret=%d terminal_trace_ret=%d requests=%u/0/0 retries=0' \\\n"
     "\t'run-a72-admission-20260828-a'; do\n"
     '\t[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d \' \')" == 1 ]] ||\n'
     '\t\tdie "trace-softfail marker is not unique: $marker"\n'
     "done", 1),
    ("portable-fetched-a72-admission-trace-package",
     "portable-fetched-a72-admission-trace-softfail-package", 1),
    ("one-source-derived-same-task-add-cpu8-request",
     "live-trace-softfail-one-shot-cpu8-request", 1),
    ("failure_evidence=retained-entry-zero-terminal-or-transition-ledger",
     "failure_evidence=terminal-status-with-separate-trace-and-operation-results", 1),
    ("candidate-a72-admission-trace-", "candidate-a72-admission-softtrace-", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe trace-softfail candidate builder derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
