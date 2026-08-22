#!/usr/bin/env bash

# Source-pin the independent manual-checkpoint candidate validator and
# specialize it for the exact live prefix-reason Image and container.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=2ee968b95f6584d9d97ee66ca2bbd719c14f5283b2b28c374c2ff00e913b7140

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_validator="$repo_root/experiments/2026-08-21-mainline-manual-checkpoint-control/scripts/test-candidate.sh"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator identity changed'

derived="$(mktemp "$script_dir/.manual-checkpoint-prefix-validator.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("manual-checkpoint Image, configuration, and container",
     "manual-checkpoint live prefix-reason Image, configuration, and container", 1),
    (".manual-checkpoint-validator.XXXXXXXX", ".manual-checkpoint-prefix-validator-inner.XXXXXXXX", 1),
    ('"""Independently validate the manual-checkpoint control candidate."""',
     '"""Independently validate the manual-checkpoint live prefix-reason candidate."""', 1),
    ("RAW_SIZE = 6_893_568", "RAW_SIZE = 6_895_616", 1),
    ("KERNEL_FIELD_SIZE = 4_815_224", "KERNEL_FIELD_SIZE = 4_818_907", 1),
    ("c1d59f3b1783f70e92b4ab27d11c5809f9722869",
     "49f8e7f31c29cecde992a048103f2591e6a1aef1", 1),
    ("da921x-manual-checkpoint-control", "da921x-manual-checkpoint-prefix-control", 1),
    ("7.1.3-gemini-checkpoint-ctl", "7.1.3-gemini-checkpoint-prefix", 1),
    ("e796316372ed008aed2abccd4ed2acadf640105f6a641aff2dd0e48e61245959",
     "6340299f8ef5cc33bdf4828a0bbd3e453cb569cf57804cfd8526922859c757dd", 1),
    ("638a9732387c5b742905ed2b71698be9cda69cfb231ecf8400fb6c2a4ee9800a",
     "ed2f64374f0f0d5b40b012ba3c914e3c6fadd5d9e073300679e035f15c7ab0dd", 1),
    ("411692b59d20ed2ed67fd64274e4f980119ff0607df4297342594a13b4ecf321",
     "4ab905bd150c5890d7a38962aafb12c695a33ac873630623144110131cd28205", 1),
    ("100b461163bfce3e4c15b69c5e7b2effdcfb760942ce4e55b9af61ade82468fa",
     "a9547ad04f47043b5f865637d80b6fcc408e05a2334d69b01a1440871f4a6b6d", 1),
    ("39e5bb68be28a2b41fc1250a0271b38b2b9d103afe81961e14b6d6060d5a593e",
     "ff38c25b4b68832fd6bd9797c37bc43d693b2247b3779af9ff1d1248b6b99960", 1),
    ("9d5fef4e7a100813c5d53451ae2a24a5c37efc37db7e19ef34a4f90df146e69d",
     "2a5df2760ea35af83edc68bdea8aa19844dbff812cbfeb896a0bca6e186a430a", 1),
    ("4338ac1ee770ea23087694f7c166226c2297874fd595751d1a235565ecee3805",
     "1d69e03378ae880d1b4f52f6350cd27e9be322478dcec0c022d91d7d0885e6ee", 1),
    ("53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c",
     "ced1f56fc56833ce47b63a98205a373276f5d666007190ec0d3bd5adb98f3901", 1),
    ("gemini-mt6797-manual-checkpoint-control.boot.img",
     "gemini-mt6797-manual-checkpoint-prefix-control.boot.img", 1),
    ("gemini-manual-checkpoint-dtb-mutation.", "gemini-manual-checkpoint-prefix-dtb-mutation.", 1),
    ('b"gemini-chkctl"', 'b"gemini-chkpfx"', 1),
    ("validation=mainline-manual-checkpoint-control-candidate",
     "validation=mainline-manual-checkpoint-prefix-control-candidate", 1),
    (r'''        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y\\n",''',
     r'''        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y\\n",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_STAGE_CONTROL=y\\n",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL=y\\n",''', 1),
    (r"""new_localversion = '        "CONFIG_LOCALVERSION=\\"-gemini-checkpoint-ctl\\"\\n",'""",
     r"""new_localversion = '        "CONFIG_LOCALVERSION=\\"-gemini-checkpoint-prefix\\"\\n",'""", 1),
    ('b"GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1",',
     'b"GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1",\n'
     '        b"GEMINI_MANUAL_CHECKPOINT_STAGE_V1",\n'
     '        b"GEMINI_MANUAL_CHECKPOINT_PREFIX_V1",\n'
     '        b"bad-signature",\n'
     '        b"nonzero-start",\n'
     '        b"nonzero-size",\n'
     '        b"unstable-or-other",\n'
     '        b"exact-record-refused",', 1),
    (r'''        " t gemini_protected_readback_manual_control_init\\n",''',
     r'''        " t gemini_protected_readback_manual_control_init\\n",
        " t gemini_prb_capture_prefix\\n",
        " d gemini_prb_prefix_checkpoint\\n",
        " d gemini_prb_prefix_slot_index\\n",
        " d gemini_prb_prefix_reason\\n",
        " d gemini_prb_stage\\n",''', 1),
    ("manual_checkpoint_retained_writes_expected=2",
     "manual_checkpoint_retained_writes_expected=prefix-refusal-consistent-0", 1),
    ("manual_checkpoint_local_full_readbacks_expected=2",
     "manual_checkpoint_local_full_readbacks_expected=prefix-refusal-consistent-0", 1),
    ("manual_checkpoint_calls=2", "manual_checkpoint_max_calls=2", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe prefix validator derivation: expected {count}, found {actual}: {old}"
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
