#!/usr/bin/env bash

# Source-pin the passed platform-snapshot assembler and retarget every exact
# package, DT, configuration, marker, and candidate identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=39168b6431bb71fb2c13e5ba038beeb72d15711303c69742078e1d16ac14a6d4
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-24-mainline-a72-platform-snapshot-first-read/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-platform-provider.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
old_config = r'''for token in \
	'CONFIG_LOCALVERSION="-gemini-a72-platform-read"' \
	'CONFIG_MODULES=y' \
	'CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y' \
	'CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y' \
	'CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y' \
	'CONFIG_MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER=y' \
	'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y' \
	'CONFIG_PSTORE_GEMINI_A72_PLATFORM_SNAPSHOT_LEDGER=y' \
	'# CONFIG_KUNIT is not set'; do
	grep -Fx "$token" "$config" >/dev/null || die "configuration missing: $token"
done
grep -q '^CONFIG_CMDLINE=".*maxcpus=8.*"$' "$config" || die 'exact maxcpus=8 closure absent'
for token in \
	CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER \
	CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER \
	CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR \
	CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER \
	CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION \
	CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW \
	CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE; do
	! grep -qx "$token=y" "$config" || die "later path enabled: $token"
done
for symbol in mt6797_a72_platform_state_snapshot mt6797_platform_snapshot_capture \
	mt6797_a72_platform_snapshot_probe mt6797_dvfsp_clock_backend_probe \
	mt6797_bigidvfs_backend_probe; do
	grep -q " ${symbol}$" "$system_map" || die "required symbol absent: $symbol"
done
for symbol in da9213_legacy_same_value_write mt6797_a72_atomic_publish \
	mt6797_a72_a34_evaluate; do
	! grep -q " ${symbol}$" "$system_map" || die "later symbol linked: $symbol"
done'''
new_config = r'''for token in \
	'CONFIG_LOCALVERSION="-gemini-a72-provider-read"' \
	'CONFIG_MODULES=y' \
	'CONFIG_REGULATOR_DA9213_LEGACY=y' \
	'CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER=y' \
	'CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y' \
	'CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y' \
	'CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y' \
	'CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER=y' \
	'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y' \
	'CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER=y' \
	'# CONFIG_KUNIT is not set'; do
	grep -Fx "$token" "$config" >/dev/null || die "configuration missing: $token"
done
grep -q '^CONFIG_CMDLINE=".*maxcpus=8.*"$' "$config" || die 'exact maxcpus=8 closure absent'
for token in \
	CONFIG_MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER \
	CONFIG_PSTORE_GEMINI_A72_PLATFORM_SNAPSHOT_LEDGER \
	CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER \
	CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER \
	CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR \
	CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER \
	CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION \
	CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW \
	CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE; do
	! grep -qx "$token=y" "$config" || die "later path enabled: $token"
done
for symbol in mt6797_a72_platform_state_snapshot mt6797_platform_provider_platform \
	mt6797_a72_platform_provider_probe mt6797_a72_provider_snapshot \
	da9213_provider_snapshot mt6797_dvfsp_clock_backend_probe \
	mt6797_bigidvfs_backend_probe; do
	grep -q " ${symbol}$" "$system_map" || die "required symbol absent: $symbol"
done
for symbol in da9213_legacy_same_value_write mt6797_a72_atomic_publish \
	mt6797_a72_a34_evaluate; do
	! grep -q " ${symbol}$" "$system_map" || die "later symbol linked: $symbol"
done'''
old_markers = r'''for marker in \
	'GEMINI_A72_PLATFORM_SNAPSHOT_V1 token=GAPS-20260824-A checkpoint=before-platform slot=1 crc32=a8bf2262' \
	'GEMINI_A72_PLATFORM_SNAPSHOT_V1 token=GAPS-20260824-A checkpoint=after-platform slot=2 crc32=ca566ccf' \
	'GEMINI_A72_PLATFORM_SNAPSHOT_V1 state=complete platform_calls=1 stable_samples=2 register_observations=26 retained_writes=2 retries=0 provider_snapshots=0 protected_clock_reads=0 bigidvfs_reads=0 secure_calls=0 publisher_calls=0 owner_mutations=0 cpu_requests=0'; do'''
new_markers = r'''for marker in \
	'GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 token=GAPP-20260825-A checkpoint=before-provider slot=1 crc32=0150f9c7' \
	'GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 token=GAPP-20260825-A checkpoint=after-provider slot=2 crc32=4fffb31e' \
	'GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 platform valid=%u spm=%08x/%08x/%08x/%08x mp2=%08x/%08x/%08x iso=%08x dcm=%08x cci=%08x/%08x/%08x pwrap=%u' \
	'GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 provider abi=%u valid=%u raw=%02x/%02x/%02x/%02x/%02x' \
	'GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 state=complete platform_calls=1 platform_samples=2 platform_register_observations=26 retained_writes=2 provider_snapshots=1 provider_samples=2 provider_i2c_reads=10 provider_i2c_writes=0 observer_retries=0 protected_clock_reads=0 bigidvfs_reads=0 secure_calls=0 provider_acquires=0 provider_releases=0 publisher_calls=0 owner_mutations=0 cpu_requests=0'; do'''
replacements = (
    ("2dd7b176a2e54e086a0d7acd689e1aa330a4c358", "2a936080d28cba12df241eb19a694fa1d559ee53", 1),
    ("readonly PROFILE=a72-platform-snapshot-candidate", "readonly PROFILE=a72-platform-provider-snapshot-candidate", 1),
    ("7.1.3-gemini-a72-platform-read", "7.1.3-gemini-a72-provider-read", 1),
    ("64ec89795d90245f65c62cc1d389715a4feacae51ab7e2096c467f10411977b1", "661c6221e2e175781e7d6fccd280dc8154648a8d524c3019dfcdc398d9f4e4d4", 1),
    ("3ec18e139078b38b0ee354461d8035388535065598ea4b80f7e7a74209681784", "55007fac97d1f3075a3f66cb1410d03a56ff944463c82b251530946a9f705456", 1),
    ("3c6c54ff07dde1ee3ea234feb39a0ceef72101414f16679e3881a5461570f284", "ee8baf009bd3c94e59c91a4d4b6090e6280e4045b5a0ff8abdcd0c0ef2f6d1ac", 1),
    ("972d871f1c3c138b328f2c4438189aea4229331452655c8252b4f26694b0f38f", "2838806a9b3004c9b7840adfe34ec2bb819be22f10af0c0d51f93b2725983faa", 1),
    ("5904070bff14da0ff82afb441078497bcbf9d4145d6ce961aa0a9d2281725231", "5071bd36c9cac884e123df20d87bda7087d8439fb7983bbcc1c233a14b56b486", 1),
    ("9c6100ebd61bf059abe4719095b85a13357b2ca215df3be5531789c9fb3cf54b", "ab3cdf901630b955e9b469b336c6741a4829daaf2f5160bce3ef42cd95364b5a", 1),
    ("9645c8e7a9f85e0f9550223937b43832b2496bcd1a864f7d3fa7c20ad2cfb526", "9a63872070f145304de2ab79b64b47b1c1e5f3b2432fe9787a6df282722909de", 1),
    ("7d87638c9626469d78e643ac3d7daf7fab5b42f11c54b3ab42df7e834d6ab9f8", "32059676f453e84e4c060294646224dfa988ed8ee2941c979578b10880c7e728", 1),
    ("39f801f713a76c616ed8d9282fc0a662fb34c5a766d6839e4c47c757638bae43", "ff902d12b95893872990ebf813f24ca298ca76c4f86d4650f3b696cbdc00d79f", 1),
    ("readonly RAW_SIZE=6909952", "readonly RAW_SIZE=6912000", 1),
    ("readonly BOOT_NAME=gemini-a72snap", "readonly BOOT_NAME=gemini-a72prov", 1),
    ("gemini-mt6797-a72-platform-snapshot-first-read.boot.img", "gemini-mt6797-a72-platform-provider-snapshot-second-read.boot.img", 1),
    (old_config, new_config, 1),
    (old_markers, new_markers, 1),
    (".a72-platform-snapshot-candidate.XXXXXXXX", ".a72-platform-provider-snapshot-candidate.XXXXXXXX", 1),
    ("portable-fetched-a72-platform-snapshot-candidate", "portable-fetched-a72-platform-provider-snapshot-candidate", 1),
    ("experiment=2026-08-24-mainline-a72-platform-snapshot-first-read", "experiment=2026-08-25-mainline-a72-platform-provider-snapshot-second-read", 1),
    ("one-stable-platform-snapshot-on-passed-three-backend-baseline", "one-stable-provider-snapshot-after-passed-platform-snapshot", 1),
    ("dtb_delta_from_passed_bigidvfs=observer-node-plus-source-phandle", "dtb_delta_from_passed_platform=replace-platform-observer-with-composed-observer", 1),
    ("platform_snapshot_calls=1\\nregister_observations=26\\nretries=0", "platform_snapshot_calls=1\\nplatform_register_observations=26\\nobserver_retries=0", 1),
    ("provider_snapshots=0\\nprotected_clock_reads=0", "provider_snapshots=1\\nprovider_samples=2\\nprovider_i2c_reads=10\\nprovider_i2c_writes=0\\nprotected_clock_reads=0", 1),
    ("candidate-a72-platform-snapshot-${RAW_SHA256:0:8}", "candidate-a72-platform-provider-snapshot-${RAW_SHA256:0:8}", 1),
    ("validation=a72-platform-snapshot-candidate-build", "validation=a72-platform-provider-snapshot-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe platform/provider builder derivation: expected {count}, found {actual}: {old}"
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
