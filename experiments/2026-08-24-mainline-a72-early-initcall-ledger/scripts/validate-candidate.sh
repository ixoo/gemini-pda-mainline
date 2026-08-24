#!/usr/bin/env bash

# Source-pin the independent Python validator and retarget only its exact
# early-initcall package, records, zero-effect contract, and identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=dac54074b9997e7d27f35f422ad25763561192f806c7695231c3d8170b2f6b59

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_validator="$repo_root/experiments/2026-08-24-mainline-a72-physical-source-observer/scripts/validate-candidate.py"
[[ -f "$source_validator" && ! -L "$source_validator" ]] ||
	die 'source validator is missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator identity changed'

derived=$(mktemp "$script_dir/.derived-validate-candidate-a72-early-initcall.XXXXXXXX")
cleanup() { [[ ! -e "$derived" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
old_markers = """\
        b"GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A checkpoint=before-bigidvfs slot=1 crc32=47eaad49",
        b"GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A checkpoint=after-bigidvfs slot=2 crc32=d03ca6dc",
        b"GEMINI_A72_PHYSICAL_SOURCE_V1 state=complete registrations=1 callbacks=1 unregisters=1 platform_calls=1 provider_snapshots=1 clock_calls=1 retained_writes=2 bigidvfs_calls=1 bigidvfs_smc_reads=8 compositor_retries=0 provider_acquires=0 provider_releases=0 publisher_calls=0 owner_mutations=0 cpu_requests=0","""
new_markers = """\
        b"GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=pure-init outcome=commit slot=1 crc32=03d9627f",
        b"GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=core-init outcome=commit slot=2 crc32=57dd63b5",
        b"GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=pure-init outcome=primary-refused slot=2 crc32=5767e326","""
replacements = (
    ("f3bf03f4c2515e9c1ac5049c6544c618aaeb8af1", "26274db63316bbb24eeb9bfa8de21759da666b9e", 1),
    ('PROFILE = "a72-physical-source-candidate"', 'PROFILE = "a72-early-initcall-ledger"', 1),
    ('RELEASE = "7.1.3-gemini-a72-physical-source"', 'RELEASE = "7.1.3-gemini-a72-early"', 1),
    ('PACKAGE_NAME = "linux-7.1.3-gemini-a72-physical-source-candidate-b2cd59e6-a48e2c2d"', 'PACKAGE_NAME = "linux-7.1.3-gemini-a72-early-initcall-ledger-467fadf8-211dd7c8"', 1),
    ("1cde8722a28029de498436315eee61027596db19cdee4a2a7224ece079bd7079", "6a990065ed3be26bb1ec113a578baba68600733d00f46bff45783569a22bfce0", 1),
    ("9ecefb990bd0cf136d32f443ebb59597de48a814df84e2dccf3669c600aac3b9", "00992be8c2ccb222c42eecfd92c43b81305f12d756cc2e2a7fc533299e2ce293", 1),
    ("39a5a007937d10f50e79da865feda843a06c0ed98301333b9f5c24bbd1808f99", "d951032cfaee8e05c5ff0c69e689a1384375d2ddce657481722451261ba332dd", 1),
    ("f139629d79deb15726381c898c79ca4e57973da8188e6d4addab9a0ffd9008ef", "16807a1bfadb4175156f162ae0656326afc93ed636dec48b829a0d67224b23c8", 1),
    ("92120e48a478bdbd3aac78f69c3ea00dbc82b86111bebcf022f3d6493c3f180f", "738759ca844d9da96db082c30e31670e2e59b4a858c9a6bf12b4c98ed0ad5e8b", 1),
    ("9bcc4a90075f659e4ab423bd6bbcf0eefb1a9f2fe4a9929f44701021d642e52c", "4753b29adba9e4cc340d7768c44a04a40d31c7e403a287ccf363cbfc5bb5f890", 1),
    ("1d0c1420ca2a1ea7c88d22ffeda44c2fa14d238ebceeb73ce7d56133bac4f005", "8bff90591b02f0c888e794c2abb28daf0768b754745f193b11b195f804f22789", 1),
    ("aa02ab666e63e7011139c1057bda99cdbab89245d41f9cad59dae30743b41246", "d2951eade3c08c889ecaeb1376f85262c44ad729048ddc3164c1db39acced609", 1),
    ("RAW_SIZE = 6_912_000", "RAW_SIZE = 6_909_952", 1),
    ('BOOT_NAME = "gemini-a72src"', 'BOOT_NAME = "gemini-a72early"', 1),
    ('BOOT_FILE = "gemini-mt6797-a72-physical-source.boot.img"', 'BOOT_FILE = "gemini-mt6797-a72-early-initcall.boot.img"', 1),
    ('candidate-a72-physical-source-' + '{RAW_SHA256[:8]}', 'candidate-a72-early-initcall-' + '{RAW_SHA256[:8]}', 1),
    ('CONFIG_LOCALVERSION="-gemini-a72-physical-source"', 'CONFIG_LOCALVERSION="-gemini-a72-early"', 1),
    ('"CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER=y",', '"# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER is not set",\n        "# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER is not set",\n        "# CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER is not set",\n        "CONFIG_PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER=y",', 1),
    ('"PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION",\n        "PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",', '"PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION",\n        "PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER",\n        "PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER",\n        "PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER",\n        "PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",', 1),
    ('"gemini_protected_readback_ledger_checkpoint",\n    ):', '"gemini_protected_readback_ledger_checkpoint",\n        "gemini_a72_pure_initcall_checkpoint",\n        "gemini_a72_core_initcall_checkpoint",\n    ):', 1),
    (old_markers, new_markers, 1),
    ('require(image_bytes.count(marker) == 1, "Image marker changed")\n\n    observer =', 'require(image_bytes.count(marker) == 1, "Image marker changed")\n    for rejected in (\n        b"GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A",\n        b"GEMINI_A72_PHYSICAL_SOURCE_V1 state=complete",\n        b"GEMINI_A72_PRECAPTURE_V1 token=GAPC-20260824-A",\n        b"GEMINI_A72_INIT_PROBE_V1 token=GAIP-20260824-A",\n        b"GEMINI_A72_INITCALL_V1 token=GAIC-20260824-A",\n    ):\n        require(rejected not in image_bytes, "rejected predecessor marker returned")\n\n    observer =', 1),
    ("validation=a72-physical-source-candidate-independent", "validation=a72-early-initcall-candidate-independent", 1),
    ('print("platform_calls=1")', 'print("observer_registrations=0")\n    print("allocations=0")\n    print("source_lookups=0")\n    print("platform_snapshots=0")', 1),
    ('print("provider_snapshots=1")', 'print("provider_snapshots=0")', 1),
    ('print("clock_calls=1")', 'print("clock_calls=0")', 1),
    ('print("bigidvfs_calls=1")', 'print("bigidvfs_calls=0")', 1),
    ('print("bigidvfs_smc_reads=8")', 'print("bigidvfs_smc_reads=0")', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe early-initcall validator derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"

set +e
python3 "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
