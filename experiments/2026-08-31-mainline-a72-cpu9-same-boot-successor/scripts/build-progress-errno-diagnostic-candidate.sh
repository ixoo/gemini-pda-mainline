#!/usr/bin/env bash

# Source-pin the mapping-fix assembler and retarget only the exact progress
# errno diagnostic package, provenance leaf, and output container.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=6bca103205a2f18b364595db3ca04ae87b4bcac4a965eccf6da8373fa316da6b
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/build-mapping-fix-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source mapping-fix builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source mapping-fix builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-cpu9-progress-errno.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("6f72e3ddd64610274886009324bc025064a2731c",
     "adfa6b85f4324e24130da45ec28ccc3ce3d8769f", 1),
    ("d03981881acbfe8d75c7f638849bd4433dc63bfbbadfec7b1e8a4ec70bee2e48",
     "e348f2cc678eb9ae65cf7e4b1450d9e15f63f467568c1fcf43aea2838484108f", 1),
    ("bd2224a8b92352fc5b53ab964ce627ac4cd311be7d99f15c85480878968d6c62",
     "6d98a45b7bb2c0feaed906af3127a01530154e34cca6c8da85c5fd6185d49d99", 1),
    ("21c594120e9103d4a76c7f5b9f7721f960bd1c311428c4a9e292abeb685eef01",
     "a31332ce57c992c52fd8b67048d91918b53b1dabae5ac83c767e45e861166889", 1),
    ("fd8b67c205dc168fdfd0fa9e8fbab820f1ed7384a47d3726ed44feff6e586a79",
     "af17847f7167c9be52b5535b599b76284aac89a2a17b015297c9fb60cbc53d98", 1),
    ("f999758ed62380e339725b78f930660828bfe5a80cd6d33d2719755d57a8510d",
     "f54e94498b91c8216142d245f2652b7f480534e1fc2c6a05e1477d455790e312", 1),
    ("a7290cdb2e131f64b8483615e3dd613c92fe2b46d2c0e731b42971a9a1fe4d11",
     "32d304dcd478bdc4069f41252120cc2feb866324794b18a6b67490afeccd0570", 1),
    ("c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0",
     "4bf74874cbfe900576ae891d32b5e8996d5c66ed599b6fca09c7310e87cdeae8", 1),
    ("ef d3 6c 8e e7 68 ad 7d a1 68 7a 62 64 b af 65 e3 85 58 74 c5 28 7c 69 38 a3 dc 31 be fd 1f 39",
     "65 d0 97 24 a7 a7 50 4f 24 52 bd 55 b 0 1d 8f 50 59 ed de ca f 5a 1c e 32 55 6 f8 83 92 d1", 1),
    (r"variant=cpu9-progress-reader-mapping-fix",
     r"variant=cpu9-progress-errno-diagnostic", 1),
    ('output_name="candidate-a72-cpu9-mapping-fix-${RAW_SHA256:0:8}"',
     'output_name="candidate-a72-cpu9-progress-errno-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-cpu9-mapping-fix-build",
     "validation=a72-cpu9-progress-errno-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress errno candidate derivation: expected "
            f"{count}, found {actual}: {old}"
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
