#!/usr/bin/env bash

# Source-pin the proven Android-v0 builder and specialize it for the exact
# zero-protected-call clock-backend entry package and candidate identities.
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

derived="$(mktemp "$script_dir/.clock-backend-entry-builder.XXXXXXXX")"
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
        "# Assemble the exact clock-backend entry-ledger Android-v0/LK candidate.",
        1,
    ),
    (
        "readonly REPOSITORY_COMMIT=1bd49d97673731509f0e2c7dcadbb2f03ed343ca",
        "readonly REPOSITORY_COMMIT=c3fd5d983ff07926837f8f95cb15da2ea9fd607c",
        1,
    ),
    (
        "readonly PROFILE=protected-readback-observer",
        "readonly PROFILE=clock-backend-entry-ledger",
        1,
    ),
    (
        "readonly RELEASE=7.1.3-gemini-protected-readback-ro",
        "readonly RELEASE=7.1.3-gemini-clock-backend-entry-ledger",
        1,
    ),
    (
        "readonly IMAGE_SHA256=670d963560c654df75f7282959141a0170d04eb2babf26a9ea56869e321b36e3",
        "readonly IMAGE_SHA256=380c487f0cdd81cf96fdd48412a287493eed81f7afa68bd14fcf8cef85ae04f5",
        1,
    ),
    (
        "readonly IMAGE_GZIP_SHA256=95d11ee7f26cba1085d24af60f6d60b029fcaf8dfca3e93df5e9bbf55dc013e5",
        "readonly IMAGE_GZIP_SHA256=ecde52ac44e79249389d1877f5b0530e9263f6e7506f262614391aad83cce268",
        1,
    ),
    (
        "readonly DTB_SHA256=34f24e49600e16e9b00f25ecba1d0806c4ce325944e176acccc6751a236b8998",
        "readonly DTB_SHA256=d93cba886584ebf3f9b30a9341f4dbea8f90fb35745200464265449a7811c920",
        1,
    ),
    (
        "readonly CONFIG_SHA256=6b47a8d9014044ff7a9769304d2bb02cf2c56bcf6407a316f8c6068a51af89f0",
        "readonly CONFIG_SHA256=c9bef81037aa6f41f3fbef50158870d3bfe5b814254609d93543e2e042ce5243",
        1,
    ),
    (
        "readonly SYSTEM_MAP_SHA256=71db0783b2504fd6dfaac567b7ca0020e1610ad7ec2a23b3f0d49f569fd5990a",
        "readonly SYSTEM_MAP_SHA256=5109aeb63c1bc21577759970da77d2adcf009a320e27fe2fb2aa3bf48b1f4db9",
        1,
    ),
    (
        "readonly BUILD_JSON_SHA256=21de87b3ce8ac54abf23dfd774bc80b722220c2297b08e96eeecb8f0b35006d4",
        "readonly BUILD_JSON_SHA256=60df6a05d60ed71dc58c8e5bbf0cbb0283a411dac76d6d92780aaf9d38cb8f33",
        1,
    ),
    (
        "readonly PACKAGE_MANIFEST_SHA256=31031b9a5b43d8d913e8d0e00a7bb92c9555fed016ba7355a26a2e10e6dc48b5",
        "readonly PACKAGE_MANIFEST_SHA256=a9a09dbd072e5b82f5a86abbff67d34de896b33efa113aa1dd5cae3d538a4af6",
        1,
    ),
    (
        "readonly RAW_SHA256=a3cb0e1c79447345d700fefc5eb68f3d136c893db8a87ecf0ebf54d0ffc0189c",
        "readonly RAW_SHA256=1c5a410b07b0fd971b2105f14cb97dea05168c5d5cf73dc67a47c2892a171768",
        1,
    ),
    (
        "readonly PADDED_SHA256=30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a",
        "readonly PADDED_SHA256=444ffc4a3631e75d05e567f6304fdd1607695adbd1f3c8b5654714633e6278de",
        1,
    ),
    (
        "readonly BOOT_FILE=gemini-mt6797-protected-readback-ro.boot.img",
        "readonly BOOT_FILE=gemini-mt6797-clock-backend-entry.boot.img",
        1,
    ),
    (
        'dtb="$package/dtbs/mediatek/mt6797-gemini-pda-protected-readback.dtb"',
        'dtb="$package/dtbs/mediatek/mt6797-gemini-pda-clock-backend-entry.dtb"',
        1,
    ),
    ("'protected-readback candidate DTB'", "'clock-backend entry candidate DTB'", 1),
    (".protected-readback-candidate.XXXXXXXX", ".clock-backend-entry-candidate.XXXXXXXX", 1),
    (
        "validation=portable-fetched-protected-readback-kernel-package",
        "validation=portable-fetched-clock-backend-entry-kernel-package",
        1,
    ),
    (
        "experiment=2026-08-21-mainline-protected-readback-runtime-observer",
        "experiment=2026-08-21-mainline-clock-backend-entry-ledger",
        1,
    ),
    (
        "runtime_hypothesis=one-clock-and-one-bigidvfs-readback-record",
        "runtime_hypothesis=clock-driver-init-and-probe-entry-retained-records",
        1,
    ),
    (
        'output_name="candidate-protected-readback-ro-${RAW_SHA256:0:8}"',
        'output_name="candidate-clock-backend-entry-${RAW_SHA256:0:8}"',
        1,
    ),
    (
        "validation=protected-readback-observer-candidate-build",
        "validation=clock-backend-entry-ledger-candidate-build",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe builder derivation: expected {count} occurrences, found {actual}: {old}"
        )
    text = text.replace(old, new)

old_config = r'''for gate in \
	'CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y' \
	'CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y' \
	'CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER=y' \
	'CONFIG_CMDLINE_FORCE=y' \
	'# CONFIG_MTK_MT6797_A72_POWER is not set' \
	'# CONFIG_MTK_MT6797_A72_PLATFORM_STATE is not set' \
	'# CONFIG_REGULATOR_DA9211 is not set' \
	'# CONFIG_KUNIT is not set'; do
	grep -Fqx "$gate" "$config" || die "configuration gate changed: $gate"
done
'''
new_config = r'''for gate in \
	'CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y' \
	'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y' \
	'CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER=y' \
	'# CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND is not set' \
	'# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER is not set' \
	'# CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER is not set' \
	'# CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER is not set' \
	'# CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT is not set' \
	'CONFIG_CMDLINE_FORCE=y' \
	'# CONFIG_MTK_MT6797_A72_POWER is not set' \
	'# CONFIG_MTK_MT6797_A72_PLATFORM_STATE is not set' \
	'# CONFIG_REGULATOR_DA9211 is not set' \
	'# CONFIG_KUNIT is not set'; do
	grep -Fqx "$gate" "$config" || die "configuration gate changed: $gate"
done
! grep -q '^CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER' "$config" ||
	die 'protected-readback observer unexpectedly enabled'
'''
if text.count(old_config) != 1:
    raise SystemExit("unsafe builder config-gate replacement")
text = text.replace(old_config, new_config)

old_symbols = r'''for symbol in mt6797_dvfsp_clock_backend_read mt6797_bigidvfs_backend_read \
	mt6797_readback_observer_probe mt6797_readback_observer_driver_init; do
	grep -q " $symbol$" "$system_map" || die "linked symbol missing: $symbol"
done
'''
new_symbols = r'''for symbol in gemini_protected_readback_ledger_checkpoint \
	mt6797_dvfsp_clock_backend_probe mt6797_dvfsp_clock_backend_driver_init; do
	grep -q " $symbol$" "$system_map" || die "linked symbol missing: $symbol"
done
'''
if text.count(old_symbols) != 1:
    raise SystemExit("unsafe builder symbol-gate replacement")
text = text.replace(old_symbols, new_symbols)

old_markers = r'''for marker in \
	'GEMINI_PROTECTED_READBACK_V1 clock ret=%d' \
	'GEMINI_PROTECTED_READBACK_V1 bigidvfs ret=%d' \
	'GEMINI_PROTECTED_READBACK_V1 state=complete attempts=1 clock_calls=1 bigidvfs_calls=1 cpu_requests=0 owner_registration=0'; do
	[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d ' ')" == 1 ]] ||
		die "runtime marker is not unique: $marker"
done
'''
new_markers = r'''for marker in \
	'GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1 token=GCBE-20260821-A checkpoint=driver-init slot=173 crc32=cda5d04d' \
	'GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1 token=GCBE-20260821-A checkpoint=probe-enter slot=174 crc32=a3662888'; do
	[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d ' ')" == 1 ]] ||
		die "runtime marker is not unique: $marker"
done
'''
if text.count(old_markers) != 1:
    raise SystemExit("unsafe builder marker-gate replacement")
text = text.replace(old_markers, new_markers)

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
