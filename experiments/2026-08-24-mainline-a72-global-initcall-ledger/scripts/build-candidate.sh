#!/usr/bin/env bash

# Source-pin the independently reviewed physical-source builder and retarget
# only its exact package, global-initcall records, zero-effect contract, and names.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=9e02338db6bab33f0bf57714d071829fdf9d9e3df6ae199c0e76f1e25ec97398

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-24-mainline-a72-physical-source-observer/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] ||
	die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

derived=$(mktemp "$script_dir/.derived-build-candidate-a72-global-initcall.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
old_markers = """\
\t'GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A checkpoint=before-bigidvfs slot=1 crc32=47eaad49' \\
\t'GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A checkpoint=after-bigidvfs slot=2 crc32=d03ca6dc' \\
\t'GEMINI_A72_PHYSICAL_SOURCE_V1 state=complete registrations=1 callbacks=1 unregisters=1 platform_calls=1 provider_snapshots=1 clock_calls=1 retained_writes=2 bigidvfs_calls=1 bigidvfs_smc_reads=8 compositor_retries=0 provider_acquires=0 provider_releases=0 publisher_calls=0 owner_mutations=0 cpu_requests=0'; do"""
new_markers = """\
\t'GEMINI_A72_INITCALL_V1 token=GAIC-20260824-A checkpoint=subsys-init slot=1 crc32=cf2a6946' \\
\t'GEMINI_A72_INITCALL_V1 token=GAIC-20260824-A checkpoint=fs-init slot=2 crc32=91ac2a49'; do"""
replacements = (
    ("guarded A72 physical-source candidate", "guarded A72 global-initcall candidate", 1),
    ("f3bf03f4c2515e9c1ac5049c6544c618aaeb8af1", "16567a0bf48286e00579ecc9838cef399e7c5919", 1),
    ("readonly PROFILE=a72-physical-source-candidate", "readonly PROFILE=a72-global-initcall-ledger", 1),
    ("7.1.3-gemini-a72-physical-source", "7.1.3-gemini-a72-initcalls", 1),
    ("1cde8722a28029de498436315eee61027596db19cdee4a2a7224ece079bd7079", "6712c701ca6f2c8e10dd2c9fe17fb0298ce6a9887ed1d6ee5769a1d1f3587b9c", 1),
    ("9ecefb990bd0cf136d32f443ebb59597de48a814df84e2dccf3669c600aac3b9", "541f2ed83c4ea6f604842be63583357446820724fccdec39ff2605df0285b4a9", 1),
    ("39a5a007937d10f50e79da865feda843a06c0ed98301333b9f5c24bbd1808f99", "0a2e292b00575fc2ad199bd4d6c525a5002f7880dc90725152bc95e800cc483a", 1),
    ("f139629d79deb15726381c898c79ca4e57973da8188e6d4addab9a0ffd9008ef", "8eba1940c32c7df9485733a26b155312fc704c50c72155eb5db93b90ac9bc6df", 1),
    ("92120e48a478bdbd3aac78f69c3ea00dbc82b86111bebcf022f3d6493c3f180f", "36541a144dffc8bd6d0a9d9c1bea8d76c9b819bcb04a9b36d96471f4c0437125", 1),
    ("9bcc4a90075f659e4ab423bd6bbcf0eefb1a9f2fe4a9929f44701021d642e52c", "26d335e9631bb9724d8c2db173979c03e0b45eb6f022432bd144d466d5fd39b7", 1),
    ("1d0c1420ca2a1ea7c88d22ffeda44c2fa14d238ebceeb73ce7d56133bac4f005", "41a181f631456be55ae28b75ee525226dd7b41da844c5c4ed5a0acd3f13c5156", 1),
    ("aa02ab666e63e7011139c1057bda99cdbab89245d41f9cad59dae30743b41246", "e9d565021de9ed1164aa78a78795d6a3dabd7af656aaa3df791e23424e66125a", 1),
    ("readonly RAW_SIZE=6912000", "readonly RAW_SIZE=6909952", 1),
    ("readonly BOOT_NAME=gemini-a72src", "readonly BOOT_NAME=gemini-a72icall", 1),
    ("readonly BOOT_FILE=gemini-mt6797-a72-physical-source.boot.img", "readonly BOOT_FILE=gemini-mt6797-a72-global-initcall.boot.img", 1),
    ('CONFIG_LOCALVERSION="-gemini-a72-physical-source"', 'CONFIG_LOCALVERSION="-gemini-a72-initcalls"', 1),
    ("'CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER=y' \\", "'# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER is not set' \\\n\t'# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER is not set' \\\n\t'CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER=y' \\", 1),
    ("\tPSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION \\\n\tPSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER \\", "\tPSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION \\\n\tPSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER \\\n\tPSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER \\\n\tPSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER \\", 1),
    ("\tgemini_protected_readback_ledger_checkpoint; do", "\tgemini_protected_readback_ledger_checkpoint \\\n\tgemini_a72_subsys_initcall_checkpoint \\\n\tgemini_a72_fs_initcall_checkpoint; do", 1),
    (old_markers, new_markers, 1),
    ("for forbidden in \\\n\t'GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1", "for forbidden in \\\n\t'GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A' \\\n\t'GEMINI_A72_PHYSICAL_SOURCE_V1 state=complete' \\\n\t'GEMINI_A72_PRECAPTURE_V1 token=GAPC-20260824-A' \\\n\t'GEMINI_A72_INIT_PROBE_V1 token=GAIP-20260824-A' \\\n\t'GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1", 1),
    (".a72-physical-source.XXXXXXXX", ".a72-global-initcall.XXXXXXXX", 1),
    ("validation=portable-fetched-a72-physical-source-package", "validation=portable-fetched-a72-global-initcall-package", 1),
    ("experiment=2026-08-24-mainline-a72-physical-source-observer", "experiment=2026-08-24-mainline-a72-global-initcall-ledger", 1),
    ("runtime_hypothesis=one-all-or-zero-direct-physical-source-snapshot", "runtime_hypothesis=subsys-and-fs-global-initcall-boundaries", 1),
    ("platform_calls_expected=1", "observer_registrations_expected=0\nallocations_expected=0\nsource_lookups_expected=0\nplatform_snapshots_expected=0", 1),
    ("provider_snapshots_expected=1", "provider_snapshots_expected=0", 1),
    ("protected_clock_reads_expected=1", "protected_clock_reads_expected=0", 1),
    ("bigidvfs_calls_expected=1", "bigidvfs_calls_expected=0", 1),
    ("bigidvfs_smc_reads_expected=8", "bigidvfs_smc_reads_expected=0", 1),
    ('output_name="candidate-a72-physical-source-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-global-initcall-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-physical-source-candidate-build", "validation=a72-global-initcall-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe global-initcall builder derivation: expected {count}, "
            f"found {actual}: {old}"
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
