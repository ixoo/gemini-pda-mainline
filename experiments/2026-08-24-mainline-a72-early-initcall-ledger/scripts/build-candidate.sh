#!/usr/bin/env bash

# Source-pin the independently reviewed physical-source builder and retarget
# only its exact package, early-initcall records, zero-effect contract, and names.
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

derived=$(mktemp "$script_dir/.derived-build-candidate-a72-early-initcall.XXXXXXXX")
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
\t'GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=pure-init outcome=commit slot=1 crc32=03d9627f' \\
\t'GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=core-init outcome=commit slot=2 crc32=57dd63b5' \\
\t'GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=pure-init outcome=primary-refused slot=2 crc32=5767e326'; do"""
replacements = (
    ("guarded A72 physical-source candidate", "guarded A72 early-initcall candidate", 1),
    ("f3bf03f4c2515e9c1ac5049c6544c618aaeb8af1", "26274db63316bbb24eeb9bfa8de21759da666b9e", 1),
    ("readonly PROFILE=a72-physical-source-candidate", "readonly PROFILE=a72-early-initcall-ledger", 1),
    ("7.1.3-gemini-a72-physical-source", "7.1.3-gemini-a72-early", 1),
    ("1cde8722a28029de498436315eee61027596db19cdee4a2a7224ece079bd7079", "6a990065ed3be26bb1ec113a578baba68600733d00f46bff45783569a22bfce0", 1),
    ("9ecefb990bd0cf136d32f443ebb59597de48a814df84e2dccf3669c600aac3b9", "00992be8c2ccb222c42eecfd92c43b81305f12d756cc2e2a7fc533299e2ce293", 1),
    ("39a5a007937d10f50e79da865feda843a06c0ed98301333b9f5c24bbd1808f99", "d951032cfaee8e05c5ff0c69e689a1384375d2ddce657481722451261ba332dd", 1),
    ("f139629d79deb15726381c898c79ca4e57973da8188e6d4addab9a0ffd9008ef", "16807a1bfadb4175156f162ae0656326afc93ed636dec48b829a0d67224b23c8", 1),
    ("92120e48a478bdbd3aac78f69c3ea00dbc82b86111bebcf022f3d6493c3f180f", "738759ca844d9da96db082c30e31670e2e59b4a858c9a6bf12b4c98ed0ad5e8b", 1),
    ("9bcc4a90075f659e4ab423bd6bbcf0eefb1a9f2fe4a9929f44701021d642e52c", "4753b29adba9e4cc340d7768c44a04a40d31c7e403a287ccf363cbfc5bb5f890", 1),
    ("1d0c1420ca2a1ea7c88d22ffeda44c2fa14d238ebceeb73ce7d56133bac4f005", "8bff90591b02f0c888e794c2abb28daf0768b754745f193b11b195f804f22789", 1),
    ("aa02ab666e63e7011139c1057bda99cdbab89245d41f9cad59dae30743b41246", "d2951eade3c08c889ecaeb1376f85262c44ad729048ddc3164c1db39acced609", 1),
    ("readonly RAW_SIZE=6912000", "readonly RAW_SIZE=6909952", 1),
    ("readonly BOOT_NAME=gemini-a72src", "readonly BOOT_NAME=gemini-a72early", 1),
    ("readonly BOOT_FILE=gemini-mt6797-a72-physical-source.boot.img", "readonly BOOT_FILE=gemini-mt6797-a72-early-initcall.boot.img", 1),
    ('CONFIG_LOCALVERSION="-gemini-a72-physical-source"', 'CONFIG_LOCALVERSION="-gemini-a72-early"', 1),
    ("'CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER=y' \\", "'# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER is not set' \\\n\t'# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER is not set' \\\n\t'# CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER is not set' \\\n\t'CONFIG_PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER=y' \\", 1),
    ("\tPSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION \\\n\tPSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER \\", "\tPSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION \\\n\tPSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER \\\n\tPSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER \\\n\tPSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER \\\n\tPSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER \\", 1),
    ("\tgemini_protected_readback_ledger_checkpoint; do", "\tgemini_protected_readback_ledger_checkpoint \\\n\tgemini_a72_pure_initcall_checkpoint \\\n\tgemini_a72_core_initcall_checkpoint; do", 1),
    (old_markers, new_markers, 1),
    ("for forbidden in \\\n\t'GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1", "for forbidden in \\\n\t'GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A' \\\n\t'GEMINI_A72_PHYSICAL_SOURCE_V1 state=complete' \\\n\t'GEMINI_A72_PRECAPTURE_V1 token=GAPC-20260824-A' \\\n\t'GEMINI_A72_INIT_PROBE_V1 token=GAIP-20260824-A' \\\n\t'GEMINI_A72_INITCALL_V1 token=GAIC-20260824-A' \\\n\t'GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1", 1),
    (".a72-physical-source.XXXXXXXX", ".a72-early-initcall.XXXXXXXX", 1),
    ("validation=portable-fetched-a72-physical-source-package", "validation=portable-fetched-a72-early-initcall-package", 1),
    ("experiment=2026-08-24-mainline-a72-physical-source-observer", "experiment=2026-08-24-mainline-a72-early-initcall-ledger", 1),
    ("runtime_hypothesis=one-all-or-zero-direct-physical-source-snapshot", "runtime_hypothesis=pure-and-core-early-initcall-boundaries-with-primary-refusal-attribution", 1),
    ("platform_calls_expected=1", "observer_registrations_expected=0\nallocations_expected=0\nsource_lookups_expected=0\nplatform_snapshots_expected=0", 1),
    ("provider_snapshots_expected=1", "provider_snapshots_expected=0", 1),
    ("protected_clock_reads_expected=1", "protected_clock_reads_expected=0", 1),
    ("bigidvfs_calls_expected=1", "bigidvfs_calls_expected=0", 1),
    ("bigidvfs_smc_reads_expected=8", "bigidvfs_smc_reads_expected=0", 1),
    ('output_name="candidate-a72-physical-source-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-early-initcall-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-physical-source-candidate-build", "validation=a72-early-initcall-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe early-initcall builder derivation: expected {count}, "
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
