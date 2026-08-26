#!/usr/bin/env bash

# Source-pin the passed third-reader assembler and retarget only the exact
# package, release, marker, and output identities for failure-stage attribution.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0987f63de0d97102f14a94469896eb311f0e642a6dc73691b06767a40ab0bc0b
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-25-mainline-a72-platform-provider-protected-clock-third-read/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-failure-stage.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
old_marker_tail = r'''\t'GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1 state=complete provider_ready_gate=passed clock_ready_gate=passed valid=%u clock_returned=%u after_checkpoint=%u platform_calls=1 platform_samples=2 platform_register_observations=26 provider_snapshots=1 provider_samples=2 provider_i2c_reads=10 provider_i2c_writes=0 retained_write_attempts=2 protected_clock_calls=1 protected_clock_ret=%d protected_clock_abi=%u protected_clock_generation=%llu clock_gate_pairs=1 explicit_mmio_writes_maximum=401 explicit_mmio_reads_maximum=419 observer_retries=0 bigidvfs_reads=0 secure_calls=0 provider_acquires=0 provider_releases=0 publisher_calls=0 owner_mutations=0 cpu_requests=0'; do'''
new_marker_tail = r'''\t'GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1 state=complete provider_ready_gate=passed clock_ready_gate=passed valid=%u clock_returned=%u after_checkpoint=%u platform_calls=1 platform_samples=2 platform_register_observations=26 provider_snapshots=1 provider_samples=2 provider_i2c_reads=10 provider_i2c_writes=0 retained_write_attempts=2 protected_clock_calls=1 protected_clock_ret=%d protected_clock_abi=%u protected_clock_generation=%llu clock_gate_pairs=1 explicit_mmio_writes_maximum=401 explicit_mmio_reads_maximum=419 observer_retries=0 bigidvfs_reads=0 secure_calls=0 provider_acquires=0 provider_releases=0 publisher_calls=0 owner_mutations=0 cpu_requests=0' \\
\t'platform/provider/clock capture failed: stage=%s ret=%d'; do'''
replacements = (
    ("5e4b0d584f76d4bf5a5e7e924b886d6b65ed4bd5", "53398b8a4689e6a4150ec450e5c1e8a5ce37c6bc", 1),
    ("a72-platform-provider-clock-candidate", "a72-platform-provider-clock-stage-candidate", 4),
    ("7.1.3-gemini-a72-clock-third", "7.1.3-gemini-a72-clock-stage", 1),
    ("845fbcaf68e847d18f5f4e4dce2981f93b5d1106cf396308515e5372d0ba9c62", "0088c87bbf39acdbb8147ba185687e87233c4c8e3c30daad633d57311e4885f8", 1),
    ("c3a7a0f583c925c93537463d84c7fb0a04bb715c232a2595e920f8504d79c4ad", "b158c810f117f62259c890dad517f769225e5ad7862d89ddfacd659aa68319b3", 1),
    ("2facfaaec397287267701d3cc74a3362418f34b793a96dbcd88920e730f63755", "d45758d0175786447635192d0ee0eff6d81f29df10482bc5828f1c3ac34b1265", 1),
    ("1ae62d5eaf09ac4d990cb4e81cce6101721ea332aa182821b266667729701d02", "3dc5719f9684a44770b23f8e8f71c2a299db06da230d3616ac756e4bc94b8057", 1),
    ("407be8f6f60f22f6c42d850f5006803086d611b7c279167b3791743560243340", "bb39b46229db4ecda930c56e29cce1dd8607baaf769f653baf853b532c307e86", 1),
    ("fc28c627cacc5c234937d85d8d3e5a342c66a2f35a3903a618a2ec1d741fedf0", "c586b6692d20fc9c4a11f768c13492b8073d8fefd37b5c54173881b8e18efaf6", 1),
    ("d2f4d2bdecbac924eaf4b6d2a4732b6e6be2847391b974da3b4bc6d2beeb3139", "8ca14ec2960b6934a7b1062de7c6013dc4e9dd3875c42d7cc96c0d7506e42429", 1),
    ("1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2", "8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb", 1),
    ("-gemini-a72-clock-third", "-gemini-a72-clock-stage", 1),
    ("gemini-mt6797-a72-platform-provider-clock-third-read.boot.img", "gemini-mt6797-a72-platform-provider-clock-stage.boot.img", 1),
    ("candidate-a72-platform-provider-clock-", "candidate-a72-platform-provider-clock-stage-", 1),
    ("2026-08-25-mainline-a72-platform-provider-protected-clock-third-read", "2026-08-25-mainline-a72-platform-provider-failure-stage-attribution", 1),
    ("one-protected-clock-snapshot-after-passed-platform-provider-prefix", "one-preclock-failure-stage-after-qualified-prefix", 1),
    ("dtb_delta_from_provider_ready=replace-observer-plus-clock-phandle", "dtb_delta_from_retired_third_reader=none-byte-identical", 1),
    (old_marker_tail, new_marker_tail, 0),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe failure-stage builder derivation: expected {count}, found {actual}: {old}"
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
