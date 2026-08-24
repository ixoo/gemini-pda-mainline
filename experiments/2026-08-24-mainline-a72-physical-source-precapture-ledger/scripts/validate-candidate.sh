#!/usr/bin/env bash

# Source-pin the independent Python validator and retarget only its
# exact pre-capture package, records, zero-capture contract, and identities.
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

derived=$(mktemp "$script_dir/.derived-validate-candidate-a72-precapture.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("f3bf03f4c2515e9c1ac5049c6544c618aaeb8af1", "94b3e6a12d0701ddedaa442a794b08b3563130f5", 1),
    ('PROFILE = "a72-physical-source-candidate"', 'PROFILE = "a72-physical-source-precapture-ledger"', 1),
    ('RELEASE = "7.1.3-gemini-a72-physical-source"', 'RELEASE = "7.1.3-gemini-a72-precapture"', 1),
    ('PACKAGE_NAME = "linux-7.1.3-gemini-a72-physical-source-candidate-b2cd59e6-a48e2c2d"', 'PACKAGE_NAME = "linux-7.1.3-gemini-a72-physical-source-precapture-ledger-a98fe737-5a9c9dff"', 1),
    ("1cde8722a28029de498436315eee61027596db19cdee4a2a7224ece079bd7079", "1f166ad5ff0488a4a94755aade7793582419dace18d959d8cc3807333c053782", 1),
    ("9ecefb990bd0cf136d32f443ebb59597de48a814df84e2dccf3669c600aac3b9", "e3dfc1b9afd09e672a56e0734989d381360528d6dbe2234323c9d2e360c6dd6d", 1),
    ("39a5a007937d10f50e79da865feda843a06c0ed98301333b9f5c24bbd1808f99", "b2969d82aca8ac9f44f3b548ceba3e3bdb87c418b6752e786a6fce3d5017b185", 1),
    ("f139629d79deb15726381c898c79ca4e57973da8188e6d4addab9a0ffd9008ef", "0ad642371f1878ced248f3a709e0454a8de2fe01ddd40c23a03e3a144b6d01be", 1),
    ("92120e48a478bdbd3aac78f69c3ea00dbc82b86111bebcf022f3d6493c3f180f", "7a5321d6ea0c09908068b9215ff2ebe76e77200193c20feceb7c18fd8c0fd942", 1),
    ("9bcc4a90075f659e4ab423bd6bbcf0eefb1a9f2fe4a9929f44701021d642e52c", "1e05f36df6dce8d37f19c66ff9237cb2cab14a89cfdecd9bb15dd50d8392a9d3", 1),
    ("1d0c1420ca2a1ea7c88d22ffeda44c2fa14d238ebceeb73ce7d56133bac4f005", "6397a032ffef624dcb9104b5788d292cfb2774c078fd8c498dc0912b189e7373", 1),
    ("aa02ab666e63e7011139c1057bda99cdbab89245d41f9cad59dae30743b41246", "825cfc4299a375efbf48b3f6b6e0bd1234b08f4610702f76cbe91138dd5392a2", 1),
    ("RAW_SIZE = 6_912_000", "RAW_SIZE = 6_909_952", 1),
    ('BOOT_NAME = "gemini-a72src"', 'BOOT_NAME = "gemini-a72pre"', 1),
    ('BOOT_FILE = "gemini-mt6797-a72-physical-source.boot.img"', 'BOOT_FILE = "gemini-mt6797-a72-precapture.boot.img"', 1),
    ('candidate-a72-physical-source-{RAW_SHA256[:8]}', 'candidate-a72-physical-source-precapture-{RAW_SHA256[:8]}', 1),
    ('CONFIG_LOCALVERSION="-gemini-a72-physical-source"', 'CONFIG_LOCALVERSION="-gemini-a72-precapture"', 1),
    ('"CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER=y",', '"# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER is not set",\n        "CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER=y",', 1),
    ('"PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION",\n        "PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",', '"PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION",\n        "PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER",\n        "PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",', 1),
    ("GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A checkpoint=before-bigidvfs slot=1 crc32=47eaad49", "GEMINI_A72_PRECAPTURE_V1 token=GAPC-20260824-A checkpoint=probe-enter slot=1 crc32=b8f6c566", 1),
    ("GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A checkpoint=after-bigidvfs slot=2 crc32=d03ca6dc", "GEMINI_A72_PRECAPTURE_V1 token=GAPC-20260824-A checkpoint=sources-held slot=2 crc32=9e7fd3e6", 1),
    ("GEMINI_A72_PHYSICAL_SOURCE_V1 state=complete registrations=1 callbacks=1 unregisters=1 platform_calls=1 provider_snapshots=1 clock_calls=1 retained_writes=2 bigidvfs_calls=1 bigidvfs_smc_reads=8 compositor_retries=0 provider_acquires=0 provider_releases=0 publisher_calls=0 owner_mutations=0 cpu_requests=0", "pre-capture ledger complete; capture disabled", 1),
    ('require(image_bytes.count(marker) == 1, "Image marker changed")\n\n    observer =', 'require(image_bytes.count(marker) == 1, "Image marker changed")\n    require(b"GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A" not in image_bytes,\n            "rejected physical-source record returned")\n    require(b"GEMINI_A72_PHYSICAL_SOURCE_V1 state=complete" not in image_bytes,\n            "rejected capture completion returned")\n\n    observer =', 1),
    ("validation=a72-physical-source-candidate-independent", "validation=a72-physical-source-precapture-candidate-independent", 1),
    ('print("platform_calls=1")', 'print("source_devices_held=3")\n    print("platform_snapshots=0")', 1),
    ('print("provider_snapshots=1")', 'print("provider_snapshots=0")', 1),
    ('print("clock_calls=1")', 'print("clock_calls=0")', 1),
    ('print("bigidvfs_calls=1")', 'print("bigidvfs_calls=0")', 1),
    ('print("bigidvfs_smc_reads=8")', 'print("bigidvfs_smc_reads=0")', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe pre-capture validator derivation: expected {count}, "
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
