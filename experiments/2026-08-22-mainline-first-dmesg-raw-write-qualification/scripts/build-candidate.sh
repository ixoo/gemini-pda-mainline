#!/usr/bin/env bash

# Source-pin the qualified raw-write builder and specialize it for the exact
# first-dmesg package, record, configuration, and Android-v0 container.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=656c57cbd4d33da0b10a65a0cffc2baf55e25be092805334350268cc364938fc

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-22-mainline-manual-checkpoint-raw-write-qualification/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

derived="$(mktemp "$script_dir/.first-dmesg-raw-write-builder.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("manual-checkpoint one-record raw-write identities and closures",
     "first-dmesg one-record raw-write identities and closures", 1),
    (".manual-checkpoint-raw-write-builder.XXXXXXXX",
     ".first-dmesg-raw-write-builder-inner.XXXXXXXX", 1),
    ("24f0a696e1cedbf80f382ca04e9d812254c7e18f",
     "41a7b69627338277e5b53216a68d26c71b504d21", 1),
    ("da921x-manual-checkpoint-raw-write",
     "da921x-first-dmesg-raw-write", 1),
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
    ("readonly BOOT_NAME=gemini-chkraw", "readonly BOOT_NAME=gemini-chkfdm", 1),
    ("readonly BOOT_FILE=gemini-mt6797-manual-checkpoint-raw-write.boot.img",
     "readonly BOOT_FILE=gemini-mt6797-first-dmesg-raw-write.boot.img", 1),
    ("'manual-checkpoint raw-write serviceability DTB'",
     "'first-dmesg raw-write serviceability DTB'", 1),
    (".manual-checkpoint-raw-write.XXXXXXXX",
     ".first-dmesg-raw-write.XXXXXXXX", 1),
    ("portable-fetched-manual-checkpoint-raw-write-package",
     "portable-fetched-first-dmesg-raw-write-package", 1),
    ("experiment=2026-08-22-mainline-manual-checkpoint-raw-write-qualification",
     "experiment=2026-08-22-mainline-first-dmesg-raw-write-qualification", 1),
    ("runtime_hypothesis=one-raw-record-commits-and-recovers-before-protected-backend",
     "runtime_hypothesis=first-dmesg-record-commits-and-enumerates-on-changed-ID-Gemian", 1),
    ("kernel_delta_from-last-runtime-proven=default-off-one-record-raw-write-qualification",
     "kernel_delta_from-last-runtime-proven=qualified-writer-targets-first-dmesg-record", 1),
    ("candidate-manual-checkpoint-raw-write-${RAW_SHA256:0:8}",
     "candidate-first-dmesg-raw-write-${RAW_SHA256:0:8}", 1),
    ("validation=manual-checkpoint-raw-write-candidate-build",
     "validation=first-dmesg-raw-write-candidate-build", 1),
    ("'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION=y' \\",
     "'# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION is not set' \\\n\t'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION=y' \\", 1),
    ('CONFIG_LOCALVERSION="-gemini-checkpoint-raw-write"',
     'CONFIG_LOCALVERSION="-gemini-checkpoint-first-dmesg"', 1),
    ("'GEMINI_MANUAL_RAW_WRITE_QUALIFICATION_LIVE_V1'; do",
     "'GEMINI_FIRST_DMESG_RAW_WRITE_QUALIFICATION_LIVE_V1'; do", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe first-dmesg candidate derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

old_anchor = '''    ("manual_checkpoint_local_full_readbacks_expected=2",
     "manual_checkpoint_local_full_readbacks_expected=exactly-1", 1),
)'''
new_anchor = '''    ("manual_checkpoint_local_full_readbacks_expected=2",
     "manual_checkpoint_local_full_readbacks_expected=exactly-1", 1),
    ("GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260821-A checkpoint=manual-first slot=173 crc32=9576f05d",
     "GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260822-B checkpoint=manual-first slot=1 crc32=7785e4ce", 2),
)'''
if text.count(old_anchor) != 1:
    raise SystemExit("unsafe first-dmesg record replacement anchor")
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
