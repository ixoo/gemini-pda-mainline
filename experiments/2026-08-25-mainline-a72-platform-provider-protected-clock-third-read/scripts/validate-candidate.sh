#!/usr/bin/env bash

# Source-pin the independent container validator and retarget its exact package,
# DT, layout, configuration, marker, and candidate identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=8a403b370cc40634288a925cbcf1a52f45bea947795c85f61177cff108cde8e7
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_validator="$repo_root/experiments/2026-08-24-mainline-a72-platform-snapshot-first-read/scripts/validate-candidate.sh"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator is missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator changed'

derived=$(mktemp "$script_dir/.derived-validate-a72-platform-provider-clock.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
old_required = r'''        b'CONFIG_LOCALVERSION="-gemini-a72-platform-read"\\n',
        b"CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y\\n",
        b"CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y\\n",
        b"CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y\\n",
        b"CONFIG_MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER=y\\n",
        b"CONFIG_PSTORE_GEMINI_A72_PLATFORM_SNAPSHOT_LEDGER=y\\n",'''
new_required = r'''        b'CONFIG_LOCALVERSION="-gemini-a72-clock-third"\\n',
        b"CONFIG_REGULATOR_DA9213_LEGACY=y\\n",
        b"CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER=y\\n",
        b"CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y\\n",
        b"CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y\\n",
        b"CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y\\n",
        b"CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER=y\\n",
        b"CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER=y\\n",'''
old_forbidden = r'''        b"CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y\\n",
        b"CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER=y\\n",
        b"CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR=y\\n",
        b"CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER=y\\n",
        b"CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE=y\\n",'''
new_forbidden = r'''        b"CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER=y\\n",
        b"CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER=y\\n",
        b"CONFIG_MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER=y\\n",
        b"CONFIG_PSTORE_GEMINI_A72_PLATFORM_SNAPSHOT_LEDGER=y\\n",
        b"CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y\\n",
        b"CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER=y\\n",
        b"CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR=y\\n",
        b"CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER=y\\n",
        b"CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION=y\\n",
        b"CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW=y\\n",
        b"CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE=y\\n",'''
old_markers = r'''        b"GEMINI_A72_PLATFORM_SNAPSHOT_V1 token=GAPS-20260824-A checkpoint=before-platform slot=1 crc32=a8bf2262",
        b"GEMINI_A72_PLATFORM_SNAPSHOT_V1 token=GAPS-20260824-A checkpoint=after-platform slot=2 crc32=ca566ccf",
        b"GEMINI_A72_PLATFORM_SNAPSHOT_V1 state=complete platform_calls=1 stable_samples=2 register_observations=26 retained_writes=2 retries=0 provider_snapshots=0 protected_clock_reads=0 bigidvfs_reads=0 secure_calls=0 publisher_calls=0 owner_mutations=0 cpu_requests=0",'''
new_markers = r'''        b"GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1 token=GAPC-20260825-A checkpoint=before-clock slot=1 crc32=7a63713c",
        b"GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1 token=GAPC-20260825-A checkpoint=after-clock slot=2 crc32=5773d4f6",
        b"GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1 platform valid=%u spm=%08x/%08x/%08x/%08x mp2=%08x/%08x/%08x iso=%08x dcm=%08x cci=%08x/%08x/%08x pwrap=%u",
        b"GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1 provider abi=%u valid=%u raw=%02x/%02x/%02x/%02x/%02x",
        b"GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1 clock ret=%d abi=%u generation=%llu muxsel=%08x ckdiv=%08x pll_ll=%08x/%08x/%08x pll_l=%08x/%08x/%08x pll_cci=%08x/%08x/%08x cspm_swctrl=%08x/%08x/%08x cspm_hwsta=%08x/%08x/%08x/%08x",
        b"GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1 state=complete provider_ready_gate=passed clock_ready_gate=passed valid=%u clock_returned=%u after_checkpoint=%u platform_calls=1 platform_samples=2 platform_register_observations=26 provider_snapshots=1 provider_samples=2 provider_i2c_reads=10 provider_i2c_writes=0 retained_write_attempts=2 protected_clock_calls=1 protected_clock_ret=%d protected_clock_abi=%u protected_clock_generation=%llu clock_gate_pairs=1 explicit_mmio_writes_maximum=401 explicit_mmio_reads_maximum=419 observer_retries=0 bigidvfs_reads=0 secure_calls=0 provider_acquires=0 provider_releases=0 publisher_calls=0 owner_mutations=0 cpu_requests=0",'''
replacements = (
    ("exact A72 platform-snapshot candidate", "exact A72 platform/provider/protected-clock candidate", 1),
    ("6_909_952", "6_912_000", 1),
    ("4_832_980", "4_833_642", 1),
    ("7d87638c9626469d78e643ac3d7daf7fab5b42f11c54b3ab42df7e834d6ab9f8", "d2f4d2bdecbac924eaf4b6d2a4732b6e6be2847391b974da3b4bc6d2beeb3139", 1),
    ("39f801f713a76c616ed8d9282fc0a662fb34c5a766d6839e4c47c757638bae43", "1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2", 1),
    ("64ec89795d90245f65c62cc1d389715a4feacae51ab7e2096c467f10411977b1", "845fbcaf68e847d18f5f4e4dce2981f93b5d1106cf396308515e5372d0ba9c62", 1),
    ("3ec18e139078b38b0ee354461d8035388535065598ea4b80f7e7a74209681784", "c3a7a0f583c925c93537463d84c7fb0a04bb715c232a2595e920f8504d79c4ad", 1),
    ("3c6c54ff07dde1ee3ea234feb39a0ceef72101414f16679e3881a5461570f284", "90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d", 1),
    ("972d871f1c3c138b328f2c4438189aea4229331452655c8252b4f26694b0f38f", "2facfaaec397287267701d3cc74a3362418f34b793a96dbcd88920e730f63755", 1),
    ("5904070bff14da0ff82afb441078497bcbf9d4145d6ce961aa0a9d2281725231", "1ae62d5eaf09ac4d990cb4e81cce6101721ea332aa182821b266667729701d02", 1),
    ("9c6100ebd61bf059abe4719095b85a13357b2ca215df3be5531789c9fb3cf54b", "407be8f6f60f22f6c42d850f5006803086d611b7c279167b3791743560243340", 1),
    ("gemini-mt6797-a72-platform-snapshot-first-read.boot.img", "gemini-mt6797-a72-platform-provider-clock-third-read.boot.img", 1),
    ('b"gemini-a72snap"', 'b"gemini-a72pclk"', 1),
    ("2dd7b176a2e54e086a0d7acd689e1aa330a4c358", "5e4b0d584f76d4bf5a5e7e924b886d6b65ed4bd5", 1),
    ('"a72-platform-snapshot-candidate"', '"a72-platform-provider-clock-candidate"', 1),
    ('"7.1.3-gemini-a72-platform-read"', '"7.1.3-gemini-a72-clock-third"', 1),
    (old_required, new_required, 1),
    (old_forbidden, new_forbidden, 1),
    (old_markers, new_markers, 1),
    ("validation=a72-platform-snapshot-candidate", "validation=a72-platform-provider-clock-candidate", 1),
    ('print("platform_snapshot_markers=before,after,complete")', 'print("platform_provider_clock_markers=before-clock,after-clock,platform,provider,clock,complete")', 1),
    ('print("control_dtb=passed-three-backend-plus-platform-snapshot-observer")', 'print("control_dtb=exact-reversible-provider-ready-clock-observer-derivative")', 1),
    ("unsafe platform-snapshot validator derivation", "unsafe platform/provider/clock validator derivation", 1),
    (".derived-validate-a72-platform-snapshot.XXXXXXXX", ".derived-validate-a72-platform-provider-clock-nested.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe platform/provider/clock validator wrapper: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
