#!/usr/bin/env bash

# Source-pin the independent prefix-control validator and specialize it for
# the exact read-only mapping-model Image, configuration, and container.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0b7cdfea858d539d57e7b2743e5a5bf2ad705b2bf3cfc0cb22016a96d2158918

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_validator="$repo_root/experiments/2026-08-21-mainline-manual-checkpoint-prefix-control/scripts/test-candidate.sh"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator identity changed'

derived="$(mktemp "$script_dir/.manual-checkpoint-map-validator.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("live prefix-reason Image, configuration, and container",
     "read-only mapping-model Image, configuration, and container", 1),
    (".manual-checkpoint-prefix-validator.XXXXXXXX",
     ".manual-checkpoint-map-validator-inner.XXXXXXXX", 1),
    ("manual-checkpoint live prefix-reason candidate",
     "manual-checkpoint read-only mapping-model candidate", 1),
    ("RAW_SIZE = 6_895_616", "RAW_SIZE = 6_899_712", 1),
    ("KERNEL_FIELD_SIZE = 4_818_907", "KERNEL_FIELD_SIZE = 4_822_422", 1),
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
    ("gemini-mt6797-manual-checkpoint-prefix-control.boot.img",
     "gemini-mt6797-manual-checkpoint-map-control.boot.img", 1),
    ("gemini-manual-checkpoint-prefix-dtb-mutation.",
     "gemini-manual-checkpoint-map-dtb-mutation.", 1),
    ('b"gemini-chkpfx"', 'b"gemini-chkmap"', 1),
    ("validation=mainline-manual-checkpoint-prefix-control-candidate",
     "validation=mainline-manual-checkpoint-map-control-candidate", 1),
    (r'"CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL=y\\n",',
     r'"CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL=y\\n",'
     '\n'
     r'        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_MAP_CONTROL=y\\n",', 1),
    ('-gemini-checkpoint-prefix', '-gemini-checkpoint-map', 1),
    ('b"GEMINI_MANUAL_CHECKPOINT_PREFIX_V1",',
     'b"GEMINI_MANUAL_CHECKPOINT_MAP_CONTROL_V1",', 1),
    ('bad-signature', 'ramoops-map-unavailable', 1),
    ('nonzero-start', 'ramoops-empty-parallel-all-ones', 1),
    ('nonzero-size', 'both-empty', 1),
    ('unstable-or-other', 'views-match-other', 1),
    ('exact-record-refused', 'views-differ', 1),
    (r'" t gemini_prb_capture_prefix\\n",',
     r'" t gemini_prb_capture_prefix.constprop.0\\n",'
     '\n'
     r'        " T persistent_ram_gemini_snapshot_header\\n",'
     '\n'
     r'        " t gemini_prb_slot_empty\\n",', 1),
    (r'''" d gemini_prb_prefix_checkpoint\\n",
        " d gemini_prb_prefix_slot_index\\n",
        " d gemini_prb_prefix_reason\\n",''',
     r'''" d gemini_prb_map_reason\\n",
        " b gemini_prb_map_parallel_signature\\n",
        " b gemini_prb_map_parallel_start\\n",
        " b gemini_prb_map_parallel_size\\n",
        " b gemini_prb_map_ramoops_signature\\n",
        " b gemini_prb_map_ramoops_start\\n",
        " b gemini_prb_map_ramoops_size\\n",
        " b gemini_prb_map_ramoops_reads\\n",''', 1),
    ("manual_checkpoint_retained_writes_expected=prefix-refusal-consistent-0",
     "manual_checkpoint_retained_writes_expected=map-control-fixed-0", 1),
    ("manual_checkpoint_local_full_readbacks_expected=prefix-refusal-consistent-0",
     "manual_checkpoint_header_reads_expected=parallel-3-and-vmap-maximum-3", 1),
    ("manual_checkpoint_max_calls=2", "manual_checkpoint_max_calls=2-map-control-exits-first", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe map-control validator derivation: expected {count}, found {actual}: {old}"
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
