#!/usr/bin/env bash

# Source-pin the production CPU9 progress assembler and retarget only the exact
# reader-mapping repair package, provenance leaf, and output container.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f1c8f880adc9a7e02d78fed0a066c953b3877549346c43c0fba8e3ccbbf43498
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/build-progress-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source progress builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source progress builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-cpu9-mapping-fix.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("630350185c9126f2c96be7295216c5ff1ee08c83",
     "6f72e3ddd64610274886009324bc025064a2731c", 1),
    ("c4e84c90a9843b8d5a7beaf8ce6c7874d1d8e972f14fa91a4e837800ecd0b5f6",
     "d03981881acbfe8d75c7f638849bd4433dc63bfbbadfec7b1e8a4ec70bee2e48", 1),
    ("4c4f43328c6c824045d118510183b1d7f2fdacd92ddeaf4f6b75a59ad76cf9b8",
     "bd2224a8b92352fc5b53ab964ce627ac4cd311be7d99f15c85480878968d6c62", 1),
    ("a657dd5c033d18b3d7638875e6603c6c9486fd9b13c2f9d9f4a9c60c82875534",
     "83183c4f2dfe62e541f8da0905cbcf1ac51262755400c81cb7dab4a3fa9966b6", 1),
    ("e262795a456a933a16b0658edb699bb3ea444e04bfa842488cf04d794f545a28",
     "21c594120e9103d4a76c7f5b9f7721f960bd1c311428c4a9e292abeb685eef01", 1),
    ("e36f8c48e29548f2156e8155fa0ef1136e9b2be17eaadb76044e554898e91f54",
     "fd8b67c205dc168fdfd0fa9e8fbab820f1ed7384a47d3726ed44feff6e586a79", 1),
    ("08ccef4ff3514162d945e12f7ac273a90efa88f71c7cb1fc0417d16b6524b2fd",
     "f999758ed62380e339725b78f930660828bfe5a80cd6d33d2719755d57a8510d", 1),
    ("85d3b591cdee4635cf0e5b889011459a4cb7e48f4ddd3ac2df0c20720e1c8833",
     "a7290cdb2e131f64b8483615e3dd613c92fe2b46d2c0e731b42971a9a1fe4d11", 1),
    ("ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72",
     "c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0", 1),
    ("ed 3a 4b f0 85 10 bd d5 c1 7 c1 10 18 3b 1c e9 85 df c5 59 4c 8a fa e5 4b df fe 0 6f b5 66 6",
     "ef d3 6c 8e e7 68 ad 7d a1 68 7a 62 64 b af 65 e3 85 58 74 c5 28 7c 69 38 a3 dc 31 be fd 1f 39", 1),
    (r"variant=cpu9-progress-ledger",
     r"variant=cpu9-progress-reader-mapping-fix", 1),
    ('output_name="candidate-a72-cpu9-progress-${RAW_SHA256:0:8}"',
     'output_name="candidate-a72-cpu9-mapping-fix-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-cpu9-progress-build",
     "validation=a72-cpu9-mapping-fix-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 mapping-fix candidate derivation: expected {count}, "
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
