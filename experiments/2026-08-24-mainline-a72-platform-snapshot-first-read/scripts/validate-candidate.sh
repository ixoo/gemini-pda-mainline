#!/usr/bin/env bash

# Source-pin the independent Android-v0 validator and retarget every exact
# package, DT, layout, marker, and candidate identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=1b650f422147d39884a9484077e3a11efdf5ff17cb2df88ab42158b7f9c7bc71
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_validator="$repo_root/experiments/2026-08-16-mainline-lk-handoff-dtb-control/scripts/test-candidate.py"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator is missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator changed'

derived=$(mktemp "$script_dir/.derived-validate-a72-platform-snapshot.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
old_config = """\
    for line in (
        b"CONFIG_MODULES=y\\n",
        b"# CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER is not set\\n",
        b"CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER=y\\n",
        b"# CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT is not set\\n",
    ):
        require(line in config, f"configuration gate missing: {line!r}")
    for marker in (
        b"GAEL-20260816-A E0",
        b"GAEL-20260816-A E1",
        b"GAEL-20260816-A E2",
        b"GAEL-20260816-A E3",
    ):"""
new_config = """\
    for line in (
        b"CONFIG_MODULES=y\\n",
        b'CONFIG_LOCALVERSION="-gemini-a72-platform-read"\\n',
        b"CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y\\n",
        b"CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y\\n",
        b"CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y\\n",
        b"CONFIG_MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER=y\\n",
        b"CONFIG_PSTORE_GEMINI_A72_PLATFORM_SNAPSHOT_LEDGER=y\\n",
        b"# CONFIG_KUNIT is not set\\n",
    ):
        require(line in config, f"configuration gate missing: {line!r}")
    for line in (
        b"CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y\\n",
        b"CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER=y\\n",
        b"CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR=y\\n",
        b"CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER=y\\n",
        b"CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE=y\\n",
    ):
        require(line not in config, f"later path leaked into configuration: {line!r}")
    for marker in (
        b"GEMINI_A72_PLATFORM_SNAPSHOT_V1 token=GAPS-20260824-A checkpoint=before-platform slot=1 crc32=a8bf2262",
        b"GEMINI_A72_PLATFORM_SNAPSHOT_V1 token=GAPS-20260824-A checkpoint=after-platform slot=2 crc32=ca566ccf",
        b"GEMINI_A72_PLATFORM_SNAPSHOT_V1 state=complete platform_calls=1 stable_samples=2 register_observations=26 retained_writes=2 retries=0 provider_snapshots=0 protected_clock_reads=0 bigidvfs_reads=0 secure_calls=0 publisher_calls=0 owner_mutations=0 cpu_requests=0",
    ):"""
replacements = (
    ("exact GAEL/Stage-27-DTB control", "exact A72 platform-snapshot candidate", 1),
    ("RAW_SIZE = 6_879_232", "RAW_SIZE = 6_909_952", 1),
    ("KERNEL_FIELD_SIZE = 4_802_149", "KERNEL_FIELD_SIZE = 4_832_980", 1),
    ("e96d0cc2670bf4de6e0cc88d35d8814c5c3aa05442d0a5bd83818fa078ca2086", "7d87638c9626469d78e643ac3d7daf7fab5b42f11c54b3ab42df7e834d6ab9f8", 1),
    ("68515e0ecbb073b4ee18b318bd869fd5b7dea1c3ac838681ceb42b7451dc1c67", "39f801f713a76c616ed8d9282fc0a662fb34c5a766d6839e4c47c757638bae43", 1),
    ("37f3897cee5a7eb899273878938b3c98522a98dd2fac64d2f0f72235d2c10d84", "64ec89795d90245f65c62cc1d389715a4feacae51ab7e2096c467f10411977b1", 1),
    ("539f83bf4e6f31e21edacde26399ea285c1e87cdf4df25fb2896d364822a89fe", "3ec18e139078b38b0ee354461d8035388535065598ea4b80f7e7a74209681784", 1),
    ("7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806", "3c6c54ff07dde1ee3ea234feb39a0ceef72101414f16679e3881a5461570f284", 1),
    ("e622eb1a3acde5c8e351227e7044e34cd894091b2f3b9c210c37e42cced0b323", "972d871f1c3c138b328f2c4438189aea4229331452655c8252b4f26694b0f38f", 1),
    ("dcdfb20bd9102c882366885ffb879885e58b8d88d73e9822a6049c9d5fc7d4ec", "5904070bff14da0ff82afb441078497bcbf9d4145d6ce961aa0a9d2281725231", 1),
    ("88ab3409c4026f140cd4a8daa0682799a6e0420b50dd8b30010e14573017fcee", "9c6100ebd61bf059abe4719095b85a13357b2ca215df3be5531789c9fb3cf54b", 1),
    ("gemini-mt6797-arm64-entry-ledger-stage27-dtb.boot.img", "gemini-mt6797-a72-platform-snapshot-first-read.boot.img", 2),
    ('b"gemini-dtbctl"', 'b"gemini-a72snap"', 1),
    ("98996fdfbf09f8de2a6b86e488defef22fcc7968", "2dd7b176a2e54e086a0d7acd689e1aa330a4c358", 1),
    ('"da921x-modules-arm64-entry-ledger"', '"a72-platform-snapshot-candidate"', 1),
    ('"7.1.3-gemini-entryled-a"', '"7.1.3-gemini-a72-platform-read"', 1),
    (old_config, new_config, 1),
    ("0xFFFF8000808DE000", "0xFFFF8000808E3000", 1),
    ("0xFFFF8000808DEFB8", "0xFFFF8000808E3B40", 1),
    ("validation=lk-handoff-dtb-control-candidate", "validation=a72-platform-snapshot-candidate", 1),
    ('print("entry_ledger_markers=E0,E1,E2,E3")', 'print("platform_snapshot_markers=before,after,complete")', 1),
    ('print("control_dtb=exact-runtime-proven-stage27")', 'print("control_dtb=passed-three-backend-plus-platform-snapshot-observer")', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe platform-snapshot validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
python3 "$derived" "$@"
result=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$result"
