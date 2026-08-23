#!/usr/bin/env bash

# Source-pin the independent qualified raw-write candidate validator and
# specialize it for the exact first-dmesg Image and container.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=c37b04a81ab1eab765bcb3fa7f6b258777ad4a28d137b5963ea15fbc22c08812

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_validator="$repo_root/experiments/2026-08-22-mainline-manual-checkpoint-raw-write-qualification/scripts/test-candidate.sh"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator identity changed'

derived="$(mktemp "$script_dir/.first-dmesg-raw-write-validator.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("exact one-record raw-write Image and container",
     "exact first-dmesg raw-write Image and container", 1),
    (".manual-checkpoint-raw-write-validator.XXXXXXXX",
     ".first-dmesg-raw-write-validator-inner.XXXXXXXX", 1),
    ('"""Independently validate the manual-checkpoint raw-write candidate."""',
     '"""Independently validate the first-dmesg raw-write candidate."""', 1),
    ("KERNEL_FIELD_SIZE = 4_818_512", "KERNEL_FIELD_SIZE = 4_818_491", 1),
    ("24f0a696e1cedbf80f382ca04e9d812254c7e18f",
     "41a7b69627338277e5b53216a68d26c71b504d21", 1),
    ("da921x-manual-checkpoint-raw-write", "da921x-first-dmesg-raw-write", 1),
    ("7.1.3-gemini-checkpoint-raw-write",
     "7.1.3-gemini-checkpoint-first-dmesg", 1),
    ("bf1b3fb57605fb207d2bf2cd9a8cc98c7127327195dc4d14a78169e6f58db715",
     "42b2240c843b72a47b7534721fd47b5d9c88420c2d2e31e007133d8bc3e483e8", 1),
    ("0c9b5db9fdadeb0c32d93a23bc6f8cbab0b50bf095a86ed05c19283e13e951f6",
     "d03e492461ebeba59a6d473c6cca1f1e1a5cc6781608634e006af6e6e6432d04", 1),
    ("ce61fec47cba4ab06f176aa68956aad81951b9f7b208e80a4f85a3b38f379341",
     "d05e45acf117db86e18ee505df29109e26144d3fd037c590dd21d861e216495a", 1),
    ("85805de3dab0fa0a9e4595cb4e4123f3a4cc17c145271e663bb6359711d53613",
     "ea07b99209a4665df99cf7ce463928c54d21450505ab3acb7b82fca706a8c499", 1),
    ("1bd62a99576b8746b68caf2ba71e4cefbc7c2b156d439475a173ab199907f4f3",
     "b0afda9aa7404e64bcda630b6fd2fc30c37386bbbc2f0a64ccb7f9ed92866524", 1),
    ("579cedd1396c4b86b9e9c9600ca9feab3590c59852db19fcec059cf2ff8435cd",
     "a30287de9d6fe6426cfcccfec5a70f5fa6b5fe7d51d7c2de65813678d5c3f536", 1),
    ("6a2f698fe05a67a96ccb8ff282ac62668170e229125fe3ddeae3257ac135adf3",
     "bcb8b61a74b6209bda287df0f949ad24344a8edc40bf28e8cb8c829c506e5b5c", 1),
    ("c10f2c03490fe1aa8ded11895a2d1817dd649edaffa307d0635fe2d69ce1c631",
     "b96ec109b3f020fdaf0cdc6ca1733d012051e6607b5520a11d32a6441f569e96", 1),
    ("gemini-mt6797-manual-checkpoint-raw-write.boot.img",
     "gemini-mt6797-first-dmesg-raw-write.boot.img", 1),
    ("gemini-manual-checkpoint-raw-write-dtb-mutation.",
     "gemini-first-dmesg-raw-write-dtb-mutation.", 1),
    ('b"gemini-chkraw"', 'b"gemini-chkfdm"', 1),
    ("validation=mainline-manual-checkpoint-raw-write-candidate",
     "validation=mainline-first-dmesg-raw-write-candidate", 1),
    (r'''        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION=y\\n",''',
     r'''        "# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION is not set\\n",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION=y\\n",''', 1),
    (r'''new_localversion = '        "CONFIG_LOCALVERSION=\\"-gemini-checkpoint-raw-write\\"\\n",''',
     r'''new_localversion = '        "CONFIG_LOCALVERSION=\\"-gemini-checkpoint-first-dmesg\\"\\n",''', 1),
    ('b"GEMINI_MANUAL_RAW_WRITE_QUALIFICATION_LIVE_V1",',
     'b"GEMINI_FIRST_DMESG_RAW_WRITE_QUALIFICATION_LIVE_V1",', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe first-dmesg validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

old_anchor = '''    ("manual_checkpoint_calls=2", "manual_checkpoint_max_calls=1", 1),
)'''
new_anchor = '''    ("manual_checkpoint_calls=2", "manual_checkpoint_max_calls=1", 1),
    ("GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260821-A checkpoint=manual-first slot=173 crc32=9576f05d",
     "GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260822-B checkpoint=manual-first slot=1 crc32=7785e4ce", 1),
)'''
if text.count(old_anchor) != 1:
    raise SystemExit("unsafe first-dmesg validator record anchor")
text = text.replace(old_anchor, new_anchor)
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
