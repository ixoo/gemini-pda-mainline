#!/usr/bin/env bash

# Source-pin the proven protected-readback Android-v0 builder and specialize it
# for the exact call-ledger package and candidate identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=13e9b0b09568cf87001f5afe22470f957a980e994bce2f142be9d61e4122edca

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-21-mainline-protected-readback-runtime-observer/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

derived="$(mktemp "$script_dir/.protected-readback-call-ledger-builder.XXXXXXXX")"
cleanup() { [[ ! -f "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")

replacements = (
    (
        "# Assemble the exact protected-readback observer Android-v0/LK candidate.",
        "# Assemble the exact protected-readback call-ledger Android-v0/LK candidate.",
        1,
    ),
    (
        "readonly REPOSITORY_COMMIT=1bd49d97673731509f0e2c7dcadbb2f03ed343ca",
        "readonly REPOSITORY_COMMIT=36027e9e5381cae6223ad64abe2a9e2368f0aba9",
        1,
    ),
    ("readonly PROFILE=protected-readback-observer", "readonly PROFILE=protected-readback-call-ledger", 1),
    ("readonly RELEASE=7.1.3-gemini-protected-readback-ro", "readonly RELEASE=7.1.3-gemini-protected-readback-ledger", 1),
    ("readonly IMAGE_SHA256=670d963560c654df75f7282959141a0170d04eb2babf26a9ea56869e321b36e3", "readonly IMAGE_SHA256=5b8682eb9eb5ed81ad238d1e265d0200c58fc009b1c9b1053531641ff721c60b", 1),
    ("readonly IMAGE_GZIP_SHA256=95d11ee7f26cba1085d24af60f6d60b029fcaf8dfca3e93df5e9bbf55dc013e5", "readonly IMAGE_GZIP_SHA256=2beabfc3f40f635e27d9085604416b301024098ad2a1ad4cebe99ac8000a5c59", 1),
    ("readonly CONFIG_SHA256=6b47a8d9014044ff7a9769304d2bb02cf2c56bcf6407a316f8c6068a51af89f0", "readonly CONFIG_SHA256=a4565fec73f962a0ab1b0e7856b426b538c9fb9023f29fd112f31b2abf45298b", 1),
    ("readonly SYSTEM_MAP_SHA256=71db0783b2504fd6dfaac567b7ca0020e1610ad7ec2a23b3f0d49f569fd5990a", "readonly SYSTEM_MAP_SHA256=a84c97a82aa81aef2c5a02fd95fbb8060fb3f789a34068fc2bb89c52feddd313", 1),
    ("readonly BUILD_JSON_SHA256=21de87b3ce8ac54abf23dfd774bc80b722220c2297b08e96eeecb8f0b35006d4", "readonly BUILD_JSON_SHA256=63e67a7895fc26d2ecfc4c2b0cd62d6bbf23939bf3a2de83e16c54619f496b80", 1),
    ("readonly PACKAGE_MANIFEST_SHA256=31031b9a5b43d8d913e8d0e00a7bb92c9555fed016ba7355a26a2e10e6dc48b5", "readonly PACKAGE_MANIFEST_SHA256=38a44be3495dc24df6c7c3d021239cb37ed1a486d021876fde077394ca9f596e", 1),
    ("readonly RAW_SHA256=a3cb0e1c79447345d700fefc5eb68f3d136c893db8a87ecf0ebf54d0ffc0189c", "readonly RAW_SHA256=199e618af834d140746c367f7789407da39ce61dd2b1f9bab40fe63150285c17", 1),
    ("readonly PADDED_SHA256=30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a", "readonly PADDED_SHA256=3ce494c971c24c9edab73aac592d0ba8dd0bbd25f06051245f7846f95d0c715a", 1),
    ("readonly RAW_SIZE=7636992", "readonly RAW_SIZE=7639040", 1),
    ("readonly BOOT_FILE=gemini-mt6797-protected-readback-ro.boot.img", "readonly BOOT_FILE=gemini-mt6797-protected-readback-ledger.boot.img", 1),
    (".protected-readback-candidate.XXXXXXXX", ".protected-readback-call-ledger-candidate.XXXXXXXX", 1),
    ("validation=portable-fetched-protected-readback-kernel-package", "validation=portable-fetched-protected-readback-call-ledger-kernel-package", 1),
    ("experiment=2026-08-21-mainline-protected-readback-runtime-observer", "experiment=2026-08-21-mainline-protected-readback-call-ledger", 1),
    ("runtime_hypothesis=one-clock-and-one-bigidvfs-readback-record", "runtime_hypothesis=retained-checkpoints-bracket-first-protected-clock-call", 1),
    ("output_name=\"candidate-protected-readback-ro-${RAW_SHA256:0:8}\"", "output_name=\"candidate-protected-readback-ledger-${RAW_SHA256:0:8}\"", 1),
    ("validation=protected-readback-observer-candidate-build", "validation=protected-readback-call-ledger-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe builder derivation: expected {count} occurrences, found {actual}: {old}"
        )
    text = text.replace(old, new)

insertions = (
    (
        "\t'CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER=y' \\\n",
        "\t'CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER=y' \\\n"
        "\t'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y' \\\n"
        "\t'# CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER is not set' \\\n"
        "\t'# CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER is not set' \\\n"
        "\t'# CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT is not set' \\\n",
        1,
    ),
    (
        "\tmt6797_readback_observer_probe mt6797_readback_observer_driver_init; do",
        "\tmt6797_readback_observer_probe mt6797_readback_observer_driver_init \\\n"
        "\tgemini_protected_readback_ledger_checkpoint; do",
        1,
    ),
    (
        "\t'GEMINI_PROTECTED_READBACK_V1 state=complete attempts=1 clock_calls=1 bigidvfs_calls=1 cpu_requests=0 owner_registration=0'; do",
        "\t'GEMINI_PROTECTED_READBACK_V1 state=complete attempts=1 clock_calls=1 bigidvfs_calls=1 cpu_requests=0 owner_registration=0' \\\n"
        "\t'GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A checkpoint=before-clock slot=173 crc32=08f2fe56' \\\n"
        "\t'GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A checkpoint=after-clock slot=174 crc32=e477a18e'; do",
        1,
    ),
)
for old, new, count in insertions:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe builder insertion: expected {count} occurrences, found {actual}: {old}"
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
