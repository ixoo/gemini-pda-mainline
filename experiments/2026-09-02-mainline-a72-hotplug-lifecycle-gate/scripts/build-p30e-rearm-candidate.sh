#!/usr/bin/env bash

# Source-pin the physical CPU9 candidate builder and retarget its exact inputs
# to the P30E-rearm production package and composed DT.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=8a44a30f30dc73280ea7ffa8fb84f58a77ff6768229110da2c4623212c20fcb7
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/scripts/build-physical-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source physical-hotplug builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-p30e-rearm.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("819d8f0d5a431c852ef5d7f8947585f3dcb167f6",
     "d2161a1eb166d469e5b5e690e5eb4bf3ff2b4f9d", 1),
    ("c64ead6c6d6fb31acbab558de73006a70c908ba989eace7c2757783243dfccb0",
     "e1b58f196a25e2a05b456d645ba34d0c35eae313e69ec44f964cd11ca3df926e", 1),
    ("af5dbc32273f7ee08b47cd68f0008fe47a38d5c22b6b70f00bacd2856d3f4f18",
     "a04aafbb670a833cd72952cd9397e311344db971d400782b15d2a2a04f26e843", 1),
    ("8c085cfe815581dfd4b21b940d51473af464a5e15529c20f72577a41fd41646b",
     "1850874148e045ee429c797d11ba57c66b4186efbf4942c5707fa71d866b09c9", 1),
    ("9a1cad35ff62f970c84e282ce6e9bf37c64bc1eb5ffbed5ef0708c5c21778db9",
     "ebb46a9910b567e5d70a3897768aa48ed5f575d42a8308bc5734099f8527b8b3", 1),
    ("9c6b745cc153922cf4624739fed7dfcfdf7799895c8afb7cf2a169b65aa11cb9",
     "8cdb95a9dd89850ab3bd4af6168a1a6ad6e6df830375021f0052cc91733719cf", 1),
    ("902762c2a1badd9e71ebb25c842b0135fbf0076837956da1da73b42a38bbedcd",
     "1396b2e81dd23f4298df86dd3449acf7dfa519d3655b280d79b64c03595b0933", 1),
    ("f411b55d89b7343e9bd53b9087012322c969fe9344411a192262e9ae0845cdc2",
     "c1cf7d7ae7734e3a540b68bc119c82669ad177e63212dee32219e1e442d30294", 1),
    ("44e1b42c2dbec86c5da4a3f6cdc0ac1a06d47405b953bdc5401d01facf1d7d09",
     "7ffd60d082633c21ae65fa3c0bb4b2dcbd69c0abfa04d6212788f7b7ae4daf9d", 1),
    ("readonly RAW_SIZE=6983680", "readonly RAW_SIZE=6981632", 1),
    ("gemini-a72prov", "gemini-a72p30e", 1),
    ("gemini-mt6797-a72-hotplug-physical.boot.img",
     "gemini-mt6797-a72-p30e-rearm.boot.img", 1),
    ("4b 19 fb 83 2a 58 7c d c3 89 fe 8f 4c 15 ed ec 4b 2f a4 e 8a e0 c5 d 99 32 12 87 8b 50 88 3d",
     "d4 3e 1 94 75 84 1a 26 9 7c 49 e3 9f ab e0 b4 5e 68 59 84 8b 21 c3 e3 df 62 d1 36 11 a1 8d 10", 1),
    ("candidate-a72-hotplug-physical-", "candidate-a72-p30e-rearm-", 1),
    ("validation=a72-physical-hotplug-package",
     "validation=a72-p30e-rearm-package", 1),
    ("validation=a72-physical-hotplug-build",
     "validation=a72-p30e-rearm-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E-rearm candidate derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
