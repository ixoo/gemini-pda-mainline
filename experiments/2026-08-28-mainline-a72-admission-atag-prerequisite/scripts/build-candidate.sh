#!/usr/bin/env bash

# Source-pin the serviceable full-admission assembler and retarget only its
# Buildbox kernel package to the config-restored ATAG-prerequisite build.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=5d14678f79964de7e0e18251b9eb1c072c8aead5d0de282fc3a1a5dec1bbf954
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"; done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P); repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-28-mainline-a72-admission-serviceability-restoration/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'
derived=$(mktemp "$script_dir/.derived-build-a72-admission-atag.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }; trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
anchor = "replacements = (\n"
injected = '''replacements = (
    ("c147e2ddc1acc93827b59f8e3bb38b9b2f4d3fb2", "296ce7f4f1fc88fc04d4aa58bbb1317648149154", 1),
    ("96c86abe4084333bf462f028c217c41eb0342ad080dae3014b439eef0f0cab18", "58f47adde2079155fd56991f0d4271218c07a2124389fc7dc818febe4d2526f4", 1),
    ("4b884c0176d4d3e7d96c35f84ce36f0e591b2b7a411fe217f43427824f8377f4", "0c4609d7cf35d40921202e064be03f1e245dd6ce41daefaa5380d98861ea2eba", 1),
    ("265f610b5200dff9184cd0dcca3c6993b572e167316e149a9856f05723c9eebd", "9b9118fd53b7b290803c52745b5fb8ab2559c0ba83765d30b6111d1bd01914d7", 1),
    ("4d6e3ad347b755907a99b0c7dc0f1cb91fff00f533f21baeab663e77373731bd", "38b9ce8a49510403531778de774a50d2d8fa6cf27d236f1c9d72369b67164182", 1),
    ("c1009fab6642739161d913bdb676fb027d7849dd60c61e1291ec04a8c2541241", "7190b805ef72806c6fa9ed8f8c9f1896af678b5fb0eee17e81c909087ba07c9d", 1),
    ("0b6c85b3d6d870c22513f64d3b61d0944a3e9729ad26c0297b4d29414d561f41", "548c79023851bfb6efd474a228e21df8977c6b247730b00f33ff3f82bac5fb6c", 1),
    ("readonly RAW_SIZE=6934528", "readonly RAW_SIZE=6942720", 1),
'''
if text.count(anchor) != 1:
    raise SystemExit("unsafe ATAG-candidate derivation: replacement anchor changed")
text = text.replace(anchor, injected, 1)
replacements = (
    ("b1ff92e8c21aff6b850ed5ac68854b06e0f2059719cb0d50f0924b22345c3e68", "6971ee829af37a8515331ddf293eb8007829dd5d52e4abaf81f12754b5da0fcd", 1),
    ("f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02", "fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0", 1),
    ("gemini-mt6797-a72-admission-serviceable.boot.img", "gemini-mt6797-a72-admission-atag-prerequisite.boot.img", 1),
    (".a72-admission-serviceability.XXXXXXXX", ".a72-admission-atag-prerequisite.XXXXXXXX", 1),
    ("experiment=2026-08-28-mainline-a72-admission-serviceability-restoration", "experiment=2026-08-28-mainline-a72-admission-atag-prerequisite", 1),
    ("validation=admission-serviceability-restoration-package", "validation=admission-atag-prerequisite-package", 1),
    ('output_name="candidate-a72-admission-serviceable-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-admission-atag-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-admission-serviceability-restoration-build", "validation=a72-admission-atag-prerequisite-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe ATAG-candidate wrapper derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e; /bin/bash "$derived" "$@"; rc=$?; set -e
cleanup; trap - EXIT HUP INT TERM; exit "$rc"
