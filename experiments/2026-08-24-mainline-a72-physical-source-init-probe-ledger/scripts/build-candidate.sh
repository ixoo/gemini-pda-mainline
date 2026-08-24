#!/usr/bin/env bash

# Source-pin the independently reviewed physical-source builder and retarget
# only its exact package, init/probe records, zero-effect contract, and names.
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

derived=$(mktemp "$script_dir/.derived-build-candidate-a72-init-probe.XXXXXXXX")
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
\t'GEMINI_A72_INIT_PROBE_V1 token=GAIP-20260824-A checkpoint=driver-init slot=1 crc32=85e5f336' \\
\t'GEMINI_A72_INIT_PROBE_V1 token=GAIP-20260824-A checkpoint=probe-enter slot=2 crc32=85116721'; do"""
replacements = (
    ("guarded A72 physical-source candidate", "guarded A72 physical-source init/probe candidate", 1),
    ("f3bf03f4c2515e9c1ac5049c6544c618aaeb8af1", "0023bd9251f009b768ba32e94211926bdd60a0fd", 1),
    ("readonly PROFILE=a72-physical-source-candidate", "readonly PROFILE=a72-physical-source-init-probe-ledger", 1),
    ("7.1.3-gemini-a72-physical-source", "7.1.3-gemini-a72-init-probe", 1),
    ("1cde8722a28029de498436315eee61027596db19cdee4a2a7224ece079bd7079", "d3a43cc79a9f2ff6d339226a1e2f0d749a3c91c6187dfa3d041fd9a812479028", 1),
    ("9ecefb990bd0cf136d32f443ebb59597de48a814df84e2dccf3669c600aac3b9", "e8f36c2fe5a8b25ef618e8a481136a805ca0bb7c2c53445e85f0b98ef998601c", 1),
    ("39a5a007937d10f50e79da865feda843a06c0ed98301333b9f5c24bbd1808f99", "bd035bf86bab6400713942edeff0e2fa45367fadc27d162e5b8a079014dc8238", 1),
    ("f139629d79deb15726381c898c79ca4e57973da8188e6d4addab9a0ffd9008ef", "7c21e27cc5c44206d3cf8765ab91009f4d8f6ee6bdfa6065cc60bee61efda11e", 1),
    ("92120e48a478bdbd3aac78f69c3ea00dbc82b86111bebcf022f3d6493c3f180f", "f3e40afe1104e5ae0520b3f4df903748a1c7f7a957ffda341ae0e64397fd2a28", 1),
    ("9bcc4a90075f659e4ab423bd6bbcf0eefb1a9f2fe4a9929f44701021d642e52c", "2b26ad6807c1db2a9c8d745beb2fbb18a5e3e10e6cac7ef1a122fc7835dd0202", 1),
    ("1d0c1420ca2a1ea7c88d22ffeda44c2fa14d238ebceeb73ce7d56133bac4f005", "366316486f475a4af373f1db4b2d71cae0418ff607d4d2ad5ff8e7cb7efd81e3", 1),
    ("aa02ab666e63e7011139c1057bda99cdbab89245d41f9cad59dae30743b41246", "4185b85192f036df09d547cdf68991e885c6d4849927e684a5923cde15c0a03c", 1),
    ("readonly RAW_SIZE=6912000", "readonly RAW_SIZE=6909952", 1),
    ("readonly BOOT_NAME=gemini-a72src", "readonly BOOT_NAME=gemini-a72init", 1),
    ("readonly BOOT_FILE=gemini-mt6797-a72-physical-source.boot.img", "readonly BOOT_FILE=gemini-mt6797-a72-init-probe.boot.img", 1),
    ('CONFIG_LOCALVERSION="-gemini-a72-physical-source"', 'CONFIG_LOCALVERSION="-gemini-a72-init-probe"', 1),
    ("'CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER=y' \\", "'# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER is not set' \\\n\t'CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER=y' \\", 1),
    ("\tPSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION \\\n\tPSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER \\", "\tPSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION \\\n\tPSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER \\\n\tPSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER \\", 1),
    (old_markers, new_markers, 1),
    ("for forbidden in \\\n\t'GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1", "for forbidden in \\\n\t'GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A' \\\n\t'GEMINI_A72_PHYSICAL_SOURCE_V1 state=complete' \\\n\t'GEMINI_A72_PRECAPTURE_V1 token=GAPC-20260824-A' \\\n\t'GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1", 1),
    (".a72-physical-source.XXXXXXXX", ".a72-physical-source-init-probe.XXXXXXXX", 1),
    ("validation=portable-fetched-a72-physical-source-package", "validation=portable-fetched-a72-physical-source-init-probe-package", 1),
    ("experiment=2026-08-24-mainline-a72-physical-source-observer", "experiment=2026-08-24-mainline-a72-physical-source-init-probe-ledger", 1),
    ("runtime_hypothesis=one-all-or-zero-direct-physical-source-snapshot", "runtime_hypothesis=driver-init-and-probe-entry-boundaries", 1),
    ("platform_calls_expected=1", "allocations_expected=0\nsource_lookups_expected=0\nplatform_snapshots_expected=0", 1),
    ("provider_snapshots_expected=1", "provider_snapshots_expected=0", 1),
    ("protected_clock_reads_expected=1", "protected_clock_reads_expected=0", 1),
    ("bigidvfs_calls_expected=1", "bigidvfs_calls_expected=0", 1),
    ("bigidvfs_smc_reads_expected=8", "bigidvfs_smc_reads_expected=0", 1),
    ('output_name="candidate-a72-physical-source-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-physical-source-init-probe-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-physical-source-candidate-build", "validation=a72-physical-source-init-probe-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe init/probe builder derivation: expected {count}, "
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
