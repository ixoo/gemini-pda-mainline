#!/usr/bin/env bash

# Source-pin the independent container validator and specialize it for the
# exact zero-protected-call clock-backend entry candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=dba6ba9fd59e67afeac5292542ec5d21691cb83735c9c7091b4f3e0ff3d0bbbb

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_validator="$repo_root/experiments/2026-08-21-mainline-protected-readback-runtime-observer/scripts/test-candidate.py"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator identity changed'

workdir="$(mktemp -d "$repo_root/artifacts/.clock-backend-entry-validator.XXXXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
derived="$workdir/test-candidate.py"

python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")

replacements = (
    (
        "Independently validate the exact protected-readback observer candidate.",
        "Independently validate the exact clock-backend entry-ledger candidate.",
        1,
    ),
    ("KERNEL_FIELD_SIZE = 5_560_167", "KERNEL_FIELD_SIZE = 5_559_536", 1),
    (
        'RAW_SHA256 = "a3cb0e1c79447345d700fefc5eb68f3d136c893db8a87ecf0ebf54d0ffc0189c"',
        'RAW_SHA256 = "1c5a410b07b0fd971b2105f14cb97dea05168c5d5cf73dc67a47c2892a171768"',
        1,
    ),
    (
        'PADDED_SHA256 = "30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a"',
        'PADDED_SHA256 = "444ffc4a3631e75d05e567f6304fdd1607695adbd1f3c8b5654714633e6278de"',
        1,
    ),
    (
        'IMAGE_SHA256 = "670d963560c654df75f7282959141a0170d04eb2babf26a9ea56869e321b36e3"',
        'IMAGE_SHA256 = "380c487f0cdd81cf96fdd48412a287493eed81f7afa68bd14fcf8cef85ae04f5"',
        1,
    ),
    (
        'IMAGE_GZIP_SHA256 = "95d11ee7f26cba1085d24af60f6d60b029fcaf8dfca3e93df5e9bbf55dc013e5"',
        'IMAGE_GZIP_SHA256 = "ecde52ac44e79249389d1877f5b0530e9263f6e7506f262614391aad83cce268"',
        1,
    ),
    (
        'DTB_SHA256 = "34f24e49600e16e9b00f25ecba1d0806c4ce325944e176acccc6751a236b8998"',
        'DTB_SHA256 = "d93cba886584ebf3f9b30a9341f4dbea8f90fb35745200464265449a7811c920"',
        1,
    ),
    (
        'CONFIG_SHA256 = "6b47a8d9014044ff7a9769304d2bb02cf2c56bcf6407a316f8c6068a51af89f0"',
        'CONFIG_SHA256 = "c9bef81037aa6f41f3fbef50158870d3bfe5b814254609d93543e2e042ce5243"',
        1,
    ),
    (
        'SYSTEM_MAP_SHA256 = "71db0783b2504fd6dfaac567b7ca0020e1610ad7ec2a23b3f0d49f569fd5990a"',
        'SYSTEM_MAP_SHA256 = "5109aeb63c1bc21577759970da77d2adcf009a320e27fe2fb2aa3bf48b1f4db9"',
        1,
    ),
    (
        'BUILD_JSON_SHA256 = "21de87b3ce8ac54abf23dfd774bc80b722220c2297b08e96eeecb8f0b35006d4"',
        'BUILD_JSON_SHA256 = "60df6a05d60ed71dc58c8e5bbf0cbb0283a411dac76d6d92780aaf9d38cb8f33"',
        1,
    ),
    (
        'BOOT_FILE = "gemini-mt6797-protected-readback-ro.boot.img"',
        'BOOT_FILE = "gemini-mt6797-clock-backend-entry.boot.img"',
        1,
    ),
    (
        'args.package\n        / "dtbs/mediatek/mt6797-gemini-pda-protected-readback.dtb"',
        'args.package\n        / "dtbs/mediatek/mt6797-gemini-pda-clock-backend-entry.dtb"',
        1,
    ),
    (
        '== "1bd49d97673731509f0e2c7dcadbb2f03ed343ca"',
        '== "c3fd5d983ff07926837f8f95cb15da2ea9fd607c"',
        1,
    ),
    (
        'provenance["build_profile"] == "protected-readback-observer"',
        'provenance["build_profile"] == "clock-backend-entry-ledger"',
        1,
    ),
    (
        'provenance["kernel_release"] == "7.1.3-gemini-protected-readback-ro"',
        'provenance["kernel_release"] == "7.1.3-gemini-clock-backend-entry-ledger"',
        1,
    ),
    (
        "validation=protected-readback-observer-candidate",
        "validation=clock-backend-entry-ledger-candidate",
        1,
    ),
    (
        "runtime_markers=clock,bigidvfs,complete",
        "runtime_markers=driver-init,probe-enter",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe validator derivation: expected {count} occurrences, found {actual}: {old}"
        )
    text = text.replace(old, new)

old_config = '''    for line in (
        b"CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y\\n",
        b"CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y\\n",
        b"CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER=y\\n",
        b"# CONFIG_MTK_MT6797_A72_POWER is not set\\n",
        b"# CONFIG_MTK_MT6797_A72_PLATFORM_STATE is not set\\n",
        b"# CONFIG_REGULATOR_DA9211 is not set\\n",
        b"# CONFIG_KUNIT is not set\\n",
    ):
        require(line in config, f"configuration gate missing: {line!r}")
'''
new_config = '''    for line in (
        b"CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y\\n",
        b"CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y\\n",
        b"CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER=y\\n",
        b"# CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND is not set\\n",
        b"# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER is not set\\n",
        b"# CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER is not set\\n",
        b"# CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER is not set\\n",
        b"# CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT is not set\\n",
        b"# CONFIG_MTK_MT6797_A72_POWER is not set\\n",
        b"# CONFIG_MTK_MT6797_A72_PLATFORM_STATE is not set\\n",
        b"# CONFIG_REGULATOR_DA9211 is not set\\n",
        b"# CONFIG_KUNIT is not set\\n",
    ):
        require(line in config, f"configuration gate missing: {line!r}")
    require(
        b"CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER" not in config,
        "protected-readback observer unexpectedly enabled",
    )
'''
if text.count(old_config) != 1:
    raise SystemExit("unsafe validator config-gate replacement")
text = text.replace(old_config, new_config)

old_symbols = '''    for symbol in (
        b"mt6797_dvfsp_clock_backend_read",
        b"mt6797_bigidvfs_backend_read",
        b"mt6797_readback_observer_probe",
        b"mt6797_readback_observer_driver_init",
    ):
        require(system_map.count(b" " + symbol + b"\\n") == 1, f"linked symbol changed: {symbol!r}")
'''
new_symbols = '''    for symbol in (
        b"gemini_protected_readback_ledger_checkpoint",
        b"mt6797_dvfsp_clock_backend_probe",
        b"mt6797_dvfsp_clock_backend_driver_init",
    ):
        require(system_map.count(b" " + symbol + b"\\n") == 1, f"linked symbol changed: {symbol!r}")
'''
if text.count(old_symbols) != 1:
    raise SystemExit("unsafe validator symbol-gate replacement")
text = text.replace(old_symbols, new_symbols)

old_markers = '''    for marker in (
        b"GEMINI_PROTECTED_READBACK_V1 clock ret=%d",
        b"GEMINI_PROTECTED_READBACK_V1 bigidvfs ret=%d",
        b"GEMINI_PROTECTED_READBACK_V1 state=complete attempts=1 clock_calls=1 bigidvfs_calls=1 cpu_requests=0 owner_registration=0",
    ):
        require(image.count(marker) == 1, f"runtime marker not unique: {marker!r}")
'''
new_markers = '''    for marker in (
        b"GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1 token=GCBE-20260821-A checkpoint=driver-init slot=173 crc32=cda5d04d",
        b"GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1 token=GCBE-20260821-A checkpoint=probe-enter slot=174 crc32=a3662888",
    ):
        require(image.count(marker) == 1, f"runtime marker not unique: {marker!r}")
'''
if text.count(old_markers) != 1:
    raise SystemExit("unsafe validator marker-gate replacement")
text = text.replace(old_markers, new_markers)

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
