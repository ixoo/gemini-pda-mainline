#!/usr/bin/env bash

# Source-pin the independent Python validator and retarget only its exact
# global-initcall package, records, zero-effect contract, and identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=dac54074b9997e7d27f35f422ad25763561192f806c7695231c3d8170b2f6b59

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_validator="$repo_root/experiments/2026-08-24-mainline-a72-physical-source-observer/scripts/validate-candidate.py"
[[ -f "$source_validator" && ! -L "$source_validator" ]] ||
	die 'source validator is missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator identity changed'

derived=$(mktemp "$script_dir/.derived-validate-candidate-a72-global-initcall.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
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
        b"GEMINI_A72_INITCALL_V1 token=GAIC-20260824-A checkpoint=subsys-init slot=1 crc32=cf2a6946",
        b"GEMINI_A72_INITCALL_V1 token=GAIC-20260824-A checkpoint=fs-init slot=2 crc32=91ac2a49","""
replacements = (
    ("f3bf03f4c2515e9c1ac5049c6544c618aaeb8af1", "16567a0bf48286e00579ecc9838cef399e7c5919", 1),
    ('PROFILE = "a72-physical-source-candidate"', 'PROFILE = "a72-global-initcall-ledger"', 1),
    ('RELEASE = "7.1.3-gemini-a72-physical-source"', 'RELEASE = "7.1.3-gemini-a72-initcalls"', 1),
    ('PACKAGE_NAME = "linux-7.1.3-gemini-a72-physical-source-candidate-b2cd59e6-a48e2c2d"', 'PACKAGE_NAME = "linux-7.1.3-gemini-a72-global-initcall-ledger-f3b5b60c-a3fd7bf9"', 1),
    ("1cde8722a28029de498436315eee61027596db19cdee4a2a7224ece079bd7079", "6712c701ca6f2c8e10dd2c9fe17fb0298ce6a9887ed1d6ee5769a1d1f3587b9c", 1),
    ("9ecefb990bd0cf136d32f443ebb59597de48a814df84e2dccf3669c600aac3b9", "541f2ed83c4ea6f604842be63583357446820724fccdec39ff2605df0285b4a9", 1),
    ("39a5a007937d10f50e79da865feda843a06c0ed98301333b9f5c24bbd1808f99", "0a2e292b00575fc2ad199bd4d6c525a5002f7880dc90725152bc95e800cc483a", 1),
    ("f139629d79deb15726381c898c79ca4e57973da8188e6d4addab9a0ffd9008ef", "8eba1940c32c7df9485733a26b155312fc704c50c72155eb5db93b90ac9bc6df", 1),
    ("92120e48a478bdbd3aac78f69c3ea00dbc82b86111bebcf022f3d6493c3f180f", "36541a144dffc8bd6d0a9d9c1bea8d76c9b819bcb04a9b36d96471f4c0437125", 1),
    ("9bcc4a90075f659e4ab423bd6bbcf0eefb1a9f2fe4a9929f44701021d642e52c", "26d335e9631bb9724d8c2db173979c03e0b45eb6f022432bd144d466d5fd39b7", 1),
    ("1d0c1420ca2a1ea7c88d22ffeda44c2fa14d238ebceeb73ce7d56133bac4f005", "41a181f631456be55ae28b75ee525226dd7b41da844c5c4ed5a0acd3f13c5156", 1),
    ("aa02ab666e63e7011139c1057bda99cdbab89245d41f9cad59dae30743b41246", "e9d565021de9ed1164aa78a78795d6a3dabd7af656aaa3df791e23424e66125a", 1),
    ("RAW_SIZE = 6_912_000", "RAW_SIZE = 6_909_952", 1),
    ('BOOT_NAME = "gemini-a72src"', 'BOOT_NAME = "gemini-a72icall"', 1),
    ('BOOT_FILE = "gemini-mt6797-a72-physical-source.boot.img"', 'BOOT_FILE = "gemini-mt6797-a72-global-initcall.boot.img"', 1),
    ('candidate-a72-physical-source-{RAW_SHA256[:8]}', 'candidate-a72-global-initcall-{RAW_SHA256[:8]}', 1),
    ('CONFIG_LOCALVERSION="-gemini-a72-physical-source"', 'CONFIG_LOCALVERSION="-gemini-a72-initcalls"', 1),
    ('"CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER=y",', '"# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER is not set",\n        "# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER is not set",\n        "CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER=y",', 1),
    ('"PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION",\n        "PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",', '"PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION",\n        "PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER",\n        "PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER",\n        "PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",', 1),
    ('"gemini_protected_readback_ledger_checkpoint",\n    ):', '"gemini_protected_readback_ledger_checkpoint",\n        "gemini_a72_subsys_initcall_checkpoint",\n        "gemini_a72_fs_initcall_checkpoint",\n    ):', 1),
    (old_markers, new_markers, 1),
    ('require(image_bytes.count(marker) == 1, "Image marker changed")\n\n    observer =', 'require(image_bytes.count(marker) == 1, "Image marker changed")\n    for rejected in (\n        b"GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A",\n        b"GEMINI_A72_PHYSICAL_SOURCE_V1 state=complete",\n        b"GEMINI_A72_PRECAPTURE_V1 token=GAPC-20260824-A",\n        b"GEMINI_A72_INIT_PROBE_V1 token=GAIP-20260824-A",\n    ):\n        require(rejected not in image_bytes, "rejected predecessor marker returned")\n\n    observer =', 1),
    ("validation=a72-physical-source-candidate-independent", "validation=a72-global-initcall-candidate-independent", 1),
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
            f"unsafe global-initcall validator derivation: expected {count}, "
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
