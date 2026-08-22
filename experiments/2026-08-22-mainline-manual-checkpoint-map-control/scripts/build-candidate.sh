#!/usr/bin/env bash

# Source-pin the prefix-control builder and specialize it for the exact
# read-only mapping-model comparison package, configuration, and container.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f6e60660fff1521ce213b7b733c3110848cde4a6090e6ff561560842bf6db5d6

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-21-mainline-manual-checkpoint-prefix-control/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

derived="$(mktemp "$script_dir/.manual-checkpoint-map-builder.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("live prefix-reason identities and closures",
     "read-only mapping-model identities and closures", 1),
    (".manual-checkpoint-prefix-builder.XXXXXXXX",
     ".manual-checkpoint-map-builder-inner.XXXXXXXX", 1),
    ("49f8e7f31c29cecde992a048103f2591e6a1aef1",
     "0ada85aab04a3ebaaa4275fad235016292774946", 1),
    ("da921x-manual-checkpoint-prefix-control",
     "da921x-manual-checkpoint-map-control", 1),
    ("7.1.3-gemini-checkpoint-prefix", "7.1.3-gemini-checkpoint-map", 1),
    ("6340299f8ef5cc33bdf4828a0bbd3e453cb569cf57804cfd8526922859c757dd",
     "0185e3cb9e5f765382a1abf4cc6ddc1bca16e927a7719572595fe8005cd08a90", 1),
    ("ed2f64374f0f0d5b40b012ba3c914e3c6fadd5d9e073300679e035f15c7ab0dd",
     "bd6fb838a8564a37174802f869850da754a6a5ced14023154e618789c9fb57d3", 1),
    ("4ab905bd150c5890d7a38962aafb12c695a33ac873630623144110131cd28205",
     "8bbabdd444c855f0d49eb9622320bcf325f1930d90f784b1f959dbe2d365ba8e", 1),
    ("a9547ad04f47043b5f865637d80b6fcc408e05a2334d69b01a1440871f4a6b6d",
     "e835f09373ac67ae2d471529ddc31ac0d1e098790af3273bd8812d4e685bb53e", 1),
    ("ff38c25b4b68832fd6bd9797c37bc43d693b2247b3779af9ff1d1248b6b99960",
     "d96d9f7efd4dbbeaaa16e5614120e4a4992bf44b369fd90187f23540061f3304", 1),
    ("2a5df2760ea35af83edc68bdea8aa19844dbff812cbfeb896a0bca6e186a430a",
     "57b4e363f1c0997dcbf2a8d9b008b3b312ec234d7a9dd4f291900b494bf2b779", 1),
    ("1d69e03378ae880d1b4f52f6350cd27e9be322478dcec0c022d91d7d0885e6ee",
     "ecd021b2c25f48a1481ff0653c4c0b053490bdb60266100b8b270e90f2299cae", 1),
    ("ced1f56fc56833ce47b63a98205a373276f5d666007190ec0d3bd5adb98f3901",
     "dd513384c78ee8378e1e4bf515f89b99ca87ed6ed86c1d38ec37f8aadd693b5b", 1),
    ("readonly RAW_SIZE=6895616", "readonly RAW_SIZE=6899712", 1),
    ("readonly BOOT_NAME=gemini-chkpfx", "readonly BOOT_NAME=gemini-chkmap", 1),
    ("gemini-mt6797-manual-checkpoint-prefix-control.boot.img",
     "gemini-mt6797-manual-checkpoint-map-control.boot.img", 1),
    ("manual-checkpoint prefix serviceability DTB",
     "manual-checkpoint map-control serviceability DTB", 1),
    (".manual-checkpoint-prefix-control.XXXXXXXX",
     ".manual-checkpoint-map-control.XXXXXXXX", 1),
    ("portable-fetched-manual-checkpoint-prefix-control-package",
     "portable-fetched-manual-checkpoint-map-control-package", 1),
    ("experiment=2026-08-21-mainline-manual-checkpoint-prefix-control",
     "experiment=2026-08-22-mainline-manual-checkpoint-map-control", 1),
    ("runtime_hypothesis=one-live-prefix-reason-identifies-first-header-refusal",
     "runtime_hypothesis=compare-parallel-and-persistent-ram-vmap-header-views-read-only", 1),
    ("kernel_delta_from-last-runtime-proven=default-off-post-refusal-three-read-snapshot-only",
     "kernel_delta_from-last-runtime-proven=default-off-two-view-read-only-map-control", 1),
    ("candidate-manual-checkpoint-prefix-control-${RAW_SHA256:0:8}",
     "candidate-manual-checkpoint-map-control-${RAW_SHA256:0:8}", 1),
    ("validation=manual-checkpoint-prefix-control-candidate-build",
     "validation=manual-checkpoint-map-control-candidate-build", 1),
    ("'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL=y' \\",
     "'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL=y' \\\n\t'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_MAP_CONTROL=y' \\", 1),
    ('CONFIG_LOCALVERSION="-gemini-checkpoint-prefix"',
     'CONFIG_LOCALVERSION="-gemini-checkpoint-map"', 1),
    ("'GEMINI_MANUAL_CHECKPOINT_PREFIX_V1'; do",
     "'GEMINI_MANUAL_CHECKPOINT_MAP_CONTROL_V1'; do", 1),
    ("manual_checkpoint_retained_writes_expected=prefix-refusal-consistent-0",
     "manual_checkpoint_retained_writes_expected=map-control-fixed-0", 1),
    ("manual_checkpoint_local_full_readbacks_expected=prefix-refusal-consistent-0",
     "manual_checkpoint_header_reads_expected=parallel-3-and-vmap-maximum-3", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe map-control candidate derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

marker_anchor = "'GEMINI_MANUAL_CHECKPOINT_MAP_CONTROL_V1'; do"
marker_replacement = (
    "'GEMINI_MANUAL_CHECKPOINT_MAP_CONTROL_V1' \\\n"
    "\t'ramoops-map-unavailable' 'ramoops-empty-parallel-all-ones' \\\n"
    "\t'both-empty' 'views-match-other' 'views-differ'; do"
)
if text.count(marker_anchor) != 1:
    raise SystemExit("unsafe map result marker insertion")
text = text.replace(marker_anchor, marker_replacement)

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
