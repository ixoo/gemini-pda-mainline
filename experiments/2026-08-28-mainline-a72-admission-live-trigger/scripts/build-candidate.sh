#!/usr/bin/env bash

# Source-pin the independently validated durable admission builder and retarget
# only its exact package, live-trigger gates, LK identity, and output hashes.
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

derived=$(mktemp "$script_dir/.derived-build-a72-admission-live.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("eb87d46ae9d58df1ff336751103745d58eed59fe",
     "c147e2ddc1acc93827b59f8e3bb38b9b2f4d3fb2", 1),
    ("a72-admission-durable-candidate", "a72-admission-live-trigger-candidate", 4),
    ("7.1.3-gemini-a72-admission-trace",
     "7.1.3-gemini-a72-admission-live", 1),
    ("linux-7.1.3-gemini-a72-admission-live-trigger-candidate-13dd59d3-a15d3567",
     "linux-7.1.3-gemini-a72-admission-live-trigger-candidate-40a78b77-c2c76c89", 1),
    ("3468c9ccc8c5e965980d283e4e441ab78ca6531a5a44e989ff4d742285f2f3b3",
     "96c86abe4084333bf462f028c217c41eb0342ad080dae3014b439eef0f0cab18", 1),
    ("05c9f1960ac315baf4d20b37f126a7fc700acfc137f5e977650cf916395c3d3b",
     "4b884c0176d4d3e7d96c35f84ce36f0e591b2b7a411fe217f43427824f8377f4", 1),
    ("d59b56cfe259fdc4294a3d51c7dcab66ba4b5270bf4b6ea526763fd4dc534c89",
     "265f610b5200dff9184cd0dcca3c6993b572e167316e149a9856f05723c9eebd", 1),
    ("f9d1242a102c4a0e5544991ab8d9f7bd5263e158f0ec5d07d41368fbbc701585",
     "4d6e3ad347b755907a99b0c7dc0f1cb91fff00f533f21baeab663e77373731bd", 1),
    ("d02a8aa8ac144fb590ac4515a1bce4b67d8286fa1bc857bf5135daa4b59d29c5",
     "c1009fab6642739161d913bdb676fb027d7849dd60c61e1291ec04a8c2541241", 1),
    ("27d550c7c88a49331d325ed1cf8dfba64dd6ed2f8fc3ae83c66f7301ea3a0604",
     "0b6c85b3d6d870c22513f64d3b61d0944a3e9729ad26c0297b4d29414d561f41", 1),
    ("ed6fc5294f5677ed1895bf1157649330c91dd1f6051a6677f2d26972915cd185",
     "633f897ace3d0382dcc88bc064be03107ee3197bb8c7d0b686abab0e9e6b8135", 1),
    ("60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1",
     "4e0f86885a16df2f8b0c1efb4dd2e67394938bad1ef720adabf70ff4635ec0ef", 1),
    ("gemini-a72adm", "gemini-a72live", 1),
    ("gemini-mt6797-a72-admission-trace.boot.img",
     "gemini-mt6797-a72-admission-live.boot.img", 1),
    (".a72-admission.XXXXXXXX", ".a72-admission-live.XXXXXXXX", 1),
    ('\t\'CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER=y\' \\\n'
     "\t'CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER=y' \\\n",
     '\t\'CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER=y\' \\\n'
     '\t\'CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y\' \\\n'
     "\t'CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER=y' \\\n", 1),
    ('CONFIG_LOCALVERSION="-gemini-a72-admission-trace"',
     'CONFIG_LOCALVERSION="-gemini-a72-admission-live"', 1),
    ("marker='GEMINI_A72_ADMISSION_V1 state=terminal ret=%d consumed=1 requests=%u/0/0 retries=0'\n"
     '[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d \' \')" == 1 ]] ||\n'
     "\tdie 'admission runtime marker is not unique'",
     "for marker in \\\n"
     "\t'GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 trigger_executions=0 core_consumed=0 requests=0/0/0 retries=0' \\\n"
     "\t'GEMINI_A72_ADMISSION_LIVE_V1 state=terminal ret=%d core_consumed=%d requests=%u/0/0 retries=0' \\\n"
     "\t'run-a72-admission-20260828-a'; do\n"
     '\t[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d \' \')" == 1 ]] ||\n'
     '\t\tdie "live-trigger marker is not unique: $marker"\n'
     "done", 1),
    ("portable-fetched-a72-admission-trace-package",
     "portable-fetched-a72-admission-live-package", 1),
    ("one-source-derived-same-task-add-cpu8-request",
     "serviceability-first-one-shot-live-cpu8-request", 1),
    ("failure_evidence=retained-entry-zero-terminal-or-transition-ledger",
     "failure_evidence=durable-pre-trigger-frame-plus-terminal-status-or-transport-loss", 1),
    ("candidate-a72-admission-trace-", "candidate-a72-admission-live-", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe live-candidate builder derivation: expected {count}, "
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
