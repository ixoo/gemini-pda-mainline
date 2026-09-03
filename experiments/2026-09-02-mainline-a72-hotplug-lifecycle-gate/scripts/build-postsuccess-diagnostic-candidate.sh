#!/usr/bin/env bash

# Source-pin the P30E-rearm candidate builder and retarget its exact inputs to
# the post-success diagnostic production package and composed DT.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f7b6ce3883af9add881088e9f34170750c2643ab5ce5bc521e5eceb35830d4e1
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/scripts/build-p30e-rearm-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source P30E-rearm builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-postsuccess-diagnostic.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("d2161a1eb166d469e5b5e690e5eb4bf3ff2b4f9d",
     "35170505f3c42fcdfa6a79c843f8492b9da0fd52", 1),
    ("e1b58f196a25e2a05b456d645ba34d0c35eae313e69ec44f964cd11ca3df926e",
     "084c2e8176b86a2037d8f2bcf11006daaf211c794694df0f2be2935d65e43b33", 1),
    ("a04aafbb670a833cd72952cd9397e311344db971d400782b15d2a2a04f26e843",
     "84b221e659586e8fd56f805abc0b2a2618d9737aac6f51865d32fc80a02b55ce", 1),
    ("1850874148e045ee429c797d11ba57c66b4186efbf4942c5707fa71d866b09c9",
     "3575c11feb630252edd5bf3e13319a8c597994f4ff349164a2a43a4bb638a4e3", 1),
    ("ebb46a9910b567e5d70a3897768aa48ed5f575d42a8308bc5734099f8527b8b3",
     "9094abdc86db61ef0c4a06670cbce1ef350a8f0b02817fd3b9e5621e2105f89a", 1),
    ("8cdb95a9dd89850ab3bd4af6168a1a6ad6e6df830375021f0052cc91733719cf",
     "27b5fc867d5db56246a84a42e25ea103da6bb3d6904ebd19732e00c2f6538122", 1),
    ("1396b2e81dd23f4298df86dd3449acf7dfa519d3655b280d79b64c03595b0933",
     "959247f1300578b1ec1652eb4cb1d9a36d7c91c6a82228ccd6a2afb9f136136b", 1),
    ("c1cf7d7ae7734e3a540b68bc119c82669ad177e63212dee32219e1e442d30294",
     "fd015493b0e1df550d2da500b82e9009c96dbcabe867c411846d8dd06e4ae14f", 1),
    ("7ffd60d082633c21ae65fa3c0bb4b2dcbd69c0abfa04d6212788f7b7ae4daf9d",
     "fe333d46ece958c7015a034c8cc8d2afd5ffd9b334dff47ff4bb33295d625671", 1),
    ("readonly RAW_SIZE=6981632", "readonly RAW_SIZE=6983680", 1),
    ("gemini-a72p30e", "gemini-a72post", 1),
    ("gemini-mt6797-a72-p30e-rearm.boot.img",
     "gemini-mt6797-a72-postsuccess-diagnostic.boot.img", 1),
    ("d4 3e 1 94 75 84 1a 26 9 7c 49 e3 9f ab e0 b4 5e 68 59 84 8b 21 c3 e3 df 62 d1 36 11 a1 8d 10",
     "4f 53 65 b9 7c ab d4 4e 8e 42 75 de f7 88 4b cb 35 33 ca 4f 6 0 12 67 d4 d7 b3 f2 31 9d 5b e4", 1),
    ("candidate-a72-p30e-rearm-", "candidate-a72-postsuccess-diagnostic-", 1),
    ("validation=a72-p30e-rearm-package",
     "validation=a72-postsuccess-diagnostic-package", 1),
    ("validation=a72-p30e-rearm-build",
     "validation=a72-postsuccess-diagnostic-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe post-success candidate derivation: expected {count}, "
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
