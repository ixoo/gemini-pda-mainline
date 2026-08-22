#!/usr/bin/env bash

# Source-pin the independent manual-checkpoint candidate validator and
# specialize it for the exact live-stage Image, configuration, and container.
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

derived="$(mktemp "$script_dir/.manual-checkpoint-stage-validator.XXXXXXXX")"
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
     "manual-checkpoint live-stage Image, configuration, and container", 1),
    (".manual-checkpoint-validator.XXXXXXXX", ".manual-checkpoint-stage-validator-inner.XXXXXXXX", 1),
    ('"""Independently validate the manual-checkpoint control candidate."""',
     '"""Independently validate the manual-checkpoint live-stage candidate."""', 1),
    ("RAW_SIZE = 6_893_568", "RAW_SIZE = 6_895_616", 1),
    ("KERNEL_FIELD_SIZE = 4_815_224", "KERNEL_FIELD_SIZE = 4_818_845", 1),
    ("c1d59f3b1783f70e92b4ab27d11c5809f9722869",
     "f4b48199932fdab458f4fae2e8f2d7a097c551ea", 1),
    ("da921x-manual-checkpoint-control", "da921x-manual-checkpoint-stage-control", 1),
    ("7.1.3-gemini-checkpoint-ctl", "7.1.3-gemini-checkpoint-stage", 1),
    ("e796316372ed008aed2abccd4ed2acadf640105f6a641aff2dd0e48e61245959",
     "6342345dc0055fbf982458bc8ab0150dee0a7b3258ca6f2fce49c36cbeaf9d15", 1),
    ("638a9732387c5b742905ed2b71698be9cda69cfb231ecf8400fb6c2a4ee9800a",
     "e7b5b9d4b3420d38222f913f964164ddaed3ae83322db062b60ae25f060e7038", 1),
    ("411692b59d20ed2ed67fd64274e4f980119ff0607df4297342594a13b4ecf321",
     "33619536a1334098cb622b6a7144b4d29bc1dd52cb2df6622ae5fe6947b8a719", 1),
    ("100b461163bfce3e4c15b69c5e7b2effdcfb760942ce4e55b9af61ade82468fa",
     "b368e02a02e95547712c50175229d0618038db6619ee816c98a2bba2b7463f91", 1),
    ("39e5bb68be28a2b41fc1250a0271b38b2b9d103afe81961e14b6d6060d5a593e",
     "e5ca9d71660b62412ac496ca93e694f327d3e7b9158d6da4ad4da1b9e80f640c", 1),
    ("9d5fef4e7a100813c5d53451ae2a24a5c37efc37db7e19ef34a4f90df146e69d",
     "9f95b9bdd3270f96b3440315d270c8543238e17db2b10ab1f9962a075128eadd", 1),
    ("4338ac1ee770ea23087694f7c166226c2297874fd595751d1a235565ecee3805",
     "07d2f185818ec7b823379c4b9291a9d2a5fcbf5341be295d4ab573e18a4386d0", 1),
    ("53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c",
     "43e7f44eeef694ef876f7686ae03e2a779a118141e7f9efa060ccc1182c8eac3", 1),
    ("gemini-mt6797-manual-checkpoint-control.boot.img",
     "gemini-mt6797-manual-checkpoint-stage-control.boot.img", 1),
    ("gemini-manual-checkpoint-dtb-mutation.", "gemini-manual-checkpoint-stage-dtb-mutation.", 1),
    ('b"gemini-chkctl"', 'b"gemini-chkstage"', 1),
    ("validation=mainline-manual-checkpoint-control-candidate",
     "validation=mainline-manual-checkpoint-stage-control-candidate", 1),
    (r'''        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y\\n",''',
     r'''        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y\\n",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_STAGE_CONTROL=y\\n",''', 1),
    (r"""new_localversion = '        "CONFIG_LOCALVERSION=\\"-gemini-checkpoint-ctl\\"\\n",'""",
     r"""new_localversion = '        "CONFIG_LOCALVERSION=\\"-gemini-checkpoint-stage\\"\\n",'""", 1),
    ('b"GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1",',
     'b"GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1",\n'
     '        b"GEMINI_MANUAL_CHECKPOINT_STAGE_V1",', 1),
    (r'''        " t gemini_protected_readback_manual_control_init\\n",''',
     r'''        " t gemini_protected_readback_manual_control_init\\n",
        " d gemini_prb_stage\\n",''', 1),
    ("manual_checkpoint_retained_writes_expected=2",
     "manual_checkpoint_retained_writes_expected=stage-consistent-0-to-2", 1),
    ("manual_checkpoint_local_full_readbacks_expected=2",
     "manual_checkpoint_local_full_readbacks_expected=stage-consistent-0-to-2", 1),
    ("manual_checkpoint_calls=2", "manual_checkpoint_max_calls=2", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage validator derivation: expected {count}, found {actual}: {old}"
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
