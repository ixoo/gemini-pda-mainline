#!/usr/bin/env bash

# Source-pin the config-restored ATAG candidate assembler and retarget only its
# Buildbox package and exact output identities to the READY-bound CPU8 build.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=bbc454eaff15123a34f75b20c5486769e0766f9b8a20e1b6016dcb8a5cba84c9
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"; done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P); repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-28-mainline-a72-admission-atag-prerequisite/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'
derived=$(mktemp "$script_dir/.derived-build-a72-ready-admission.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }; trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("296ce7f4f1fc88fc04d4aa58bbb1317648149154", "5abde763316ab358d7f5cb1a3b6a461eb0a2ed99", 1),
    ("58f47adde2079155fd56991f0d4271218c07a2124389fc7dc818febe4d2526f4", "68b04b4dc3a46cd61310678d2f772450dccf42087e64fa4902cb9f8439dd8d9c", 1),
    ("0c4609d7cf35d40921202e064be03f1e245dd6ce41daefaa5380d98861ea2eba", "2b0ef4482e92d734385cfd794b49ed7cd65a4415731c7f9c3ee276fe603730ce", 1),
    ("38b9ce8a49510403531778de774a50d2d8fa6cf27d236f1c9d72369b67164182", "073cf7b491e0ac3cf7925a3b2c73660554fd6597218a33e1655830eed59bda2b", 1),
    ("7190b805ef72806c6fa9ed8f8c9f1896af678b5fb0eee17e81c909087ba07c9d", "45b3dbeda5e3ff119e51d57c7e23dfef33d6ae9a9a6a493fbd5a5e9f58327bda", 1),
    ("548c79023851bfb6efd474a228e21df8977c6b247730b00f33ff3f82bac5fb6c", "b17e485aa14119a7c56bea6ccc657b7d583ee1069642035b1201ae8848172634", 1),
    ("readonly RAW_SIZE=6942720", "readonly RAW_SIZE=6948864", 1),
    ("6971ee829af37a8515331ddf293eb8007829dd5d52e4abaf81f12754b5da0fcd", "4c8cf8e05666919e261d1f09ae1b3194f6ba1e444d3ed1b52bc59321ff638d47", 1),
    ("fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0", "8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7", 1),
    ("gemini-mt6797-a72-admission-atag-prerequisite.boot.img", "gemini-mt6797-a72-ready-admission.boot.img", 1),
    (".a72-admission-atag-prerequisite.XXXXXXXX", ".a72-ready-admission.XXXXXXXX", 1),
    ("experiment=2026-08-28-mainline-a72-admission-atag-prerequisite", "experiment=2026-08-30-mainline-a72-ready-admission", 1),
    ("validation=admission-atag-prerequisite-package", "validation=a72-ready-admission-package", 1),
    ('output_name="candidate-a72-admission-atag-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-ready-admission-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-admission-atag-prerequisite-build", "validation=a72-ready-admission-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe READY-candidate derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e; /bin/bash "$derived" "$@"; rc=$?; set -e
cleanup; trap - EXIT HUP INT TERM; exit "$rc"
