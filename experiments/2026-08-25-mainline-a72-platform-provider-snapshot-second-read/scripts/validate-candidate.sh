#!/usr/bin/env bash

# Source-pin the independent platform-snapshot validator and retarget its exact
# container, package, DT, configuration, and marker identities.
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

derived=$(mktemp "$script_dir/.derived-validate-a72-platform-provider.XXXXXXXX")
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
new_required = r'''        b'CONFIG_LOCALVERSION="-gemini-a72-provider-read"\\n',
        b"CONFIG_REGULATOR_DA9213_LEGACY=y\\n",
        b"CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER=y\\n",
        b"CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y\\n",
        b"CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y\\n",
        b"CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y\\n",
        b"CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER=y\\n",
        b"CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER=y\\n",'''
old_forbidden = r'''        b"CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y\\n",
        b"CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER=y\\n",
        b"CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR=y\\n",
        b"CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER=y\\n",
        b"CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE=y\\n",'''
new_forbidden = r'''        b"CONFIG_MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER=y\\n",
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
new_markers = r'''        b"GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 token=GAPP-20260825-A checkpoint=before-provider slot=1 crc32=0150f9c7",
        b"GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 token=GAPP-20260825-A checkpoint=after-provider slot=2 crc32=4fffb31e",
        b"GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 platform valid=%u spm=%08x/%08x/%08x/%08x mp2=%08x/%08x/%08x iso=%08x dcm=%08x cci=%08x/%08x/%08x pwrap=%u",
        b"GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 provider abi=%u valid=%u raw=%02x/%02x/%02x/%02x/%02x",
        b"GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 state=complete platform_calls=1 platform_samples=2 platform_register_observations=26 retained_writes=2 provider_snapshots=1 provider_samples=2 provider_i2c_reads=10 provider_i2c_writes=0 observer_retries=0 protected_clock_reads=0 bigidvfs_reads=0 secure_calls=0 provider_acquires=0 provider_releases=0 publisher_calls=0 owner_mutations=0 cpu_requests=0",'''
replacements = (
    ("exact A72 platform-snapshot candidate", "exact A72 platform/provider-snapshot candidate", 1),
    ("6_909_952", "6_912_000", 1),
    ("4_832_980", "4_833_733", 1),
    ("7d87638c9626469d78e643ac3d7daf7fab5b42f11c54b3ab42df7e834d6ab9f8", "32059676f453e84e4c060294646224dfa988ed8ee2941c979578b10880c7e728", 1),
    ("39f801f713a76c616ed8d9282fc0a662fb34c5a766d6839e4c47c757638bae43", "ff902d12b95893872990ebf813f24ca298ca76c4f86d4650f3b696cbdc00d79f", 1),
    ("64ec89795d90245f65c62cc1d389715a4feacae51ab7e2096c467f10411977b1", "661c6221e2e175781e7d6fccd280dc8154648a8d524c3019dfcdc398d9f4e4d4", 1),
    ("3ec18e139078b38b0ee354461d8035388535065598ea4b80f7e7a74209681784", "55007fac97d1f3075a3f66cb1410d03a56ff944463c82b251530946a9f705456", 1),
    ("3c6c54ff07dde1ee3ea234feb39a0ceef72101414f16679e3881a5461570f284", "ee8baf009bd3c94e59c91a4d4b6090e6280e4045b5a0ff8abdcd0c0ef2f6d1ac", 1),
    ("972d871f1c3c138b328f2c4438189aea4229331452655c8252b4f26694b0f38f", "2838806a9b3004c9b7840adfe34ec2bb819be22f10af0c0d51f93b2725983faa", 1),
    ("5904070bff14da0ff82afb441078497bcbf9d4145d6ce961aa0a9d2281725231", "5071bd36c9cac884e123df20d87bda7087d8439fb7983bbcc1c233a14b56b486", 1),
    ("9c6100ebd61bf059abe4719095b85a13357b2ca215df3be5531789c9fb3cf54b", "ab3cdf901630b955e9b469b336c6741a4829daaf2f5160bce3ef42cd95364b5a", 1),
    ("gemini-mt6797-a72-platform-snapshot-first-read.boot.img", "gemini-mt6797-a72-platform-provider-snapshot-second-read.boot.img", 1),
    ('b"gemini-a72snap"', 'b"gemini-a72prov"', 1),
    ("2dd7b176a2e54e086a0d7acd689e1aa330a4c358", "2a936080d28cba12df241eb19a694fa1d559ee53", 1),
    ('"a72-platform-snapshot-candidate"', '"a72-platform-provider-snapshot-candidate"', 1),
    ('"7.1.3-gemini-a72-platform-read"', '"7.1.3-gemini-a72-provider-read"', 1),
    (old_required, new_required, 1),
    (old_forbidden, new_forbidden, 1),
    (old_markers, new_markers, 1),
    ("validation=a72-platform-snapshot-candidate", "validation=a72-platform-provider-snapshot-candidate", 1),
    ('print("platform_snapshot_markers=before,after,complete")', 'print("platform_provider_markers=before-provider,after-provider,platform,provider,complete")', 1),
    ('print("control_dtb=passed-three-backend-plus-platform-snapshot-observer")', 'print("control_dtb=passed-platform-tree-with-composed-observer-replacement")', 1),
    ("unsafe platform-snapshot validator derivation", "unsafe platform/provider validator derivation", 1),
    (".derived-validate-a72-platform-snapshot.XXXXXXXX", ".derived-validate-a72-platform-provider-nested.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe platform/provider validator wrapper: expected {count}, found {actual}: {old}"
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
