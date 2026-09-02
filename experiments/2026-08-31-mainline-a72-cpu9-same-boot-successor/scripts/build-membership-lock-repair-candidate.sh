#!/usr/bin/env bash

# Source-pin the production CPU9 progress assembler and retarget only the exact
# membership-begin lock-repair package, provenance leaf, and output container.
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
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source CPU9 progress builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source CPU9 progress builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-cpu9-membership-lock-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("630350185c9126f2c96be7295216c5ff1ee08c83",
     "635e5bcf8f111ddf6356fc3091a3273128e97b74", 1),
    ("c4e84c90a9843b8d5a7beaf8ce6c7874d1d8e972f14fa91a4e837800ecd0b5f6",
     "027a161a4f355a4c27f0a4dd42ba9386c9ace6d89a55596f82305cf6e13364a1", 1),
    ("4c4f43328c6c824045d118510183b1d7f2fdacd92ddeaf4f6b75a59ad76cf9b8",
     "98565008f0bbe0757c7e680788863720c3d1c9971f59d5d3ccd59b6cf2a216ca", 1),
    ("a657dd5c033d18b3d7638875e6603c6c9486fd9b13c2f9d9f4a9c60c82875534",
     "7d999ee089db280851329ca80550dbb5a2d39542852f0a3dcc9e31ccefe94597", 1),
    ("e262795a456a933a16b0658edb699bb3ea444e04bfa842488cf04d794f545a28",
     "a8d2bd604faec549ce17c746a4ac2b83c724e2579fdbd46c6c6e49cbe89ec552", 1),
    ("e36f8c48e29548f2156e8155fa0ef1136e9b2be17eaadb76044e554898e91f54",
     "f24403b0d0a04502643828feb2a9c2287eb4db1e7b003eebfda9cdbdd6b1e157", 1),
    ("08ccef4ff3514162d945e12f7ac273a90efa88f71c7cb1fc0417d16b6524b2fd",
     "a36dfc2c2cad2a300dd89b3cd4dd8662fe86152c6c2740467d95d149c6a1d279", 1),
    ("85d3b591cdee4635cf0e5b889011459a4cb7e48f4ddd3ac2df0c20720e1c8833",
     "44aacf58262a0c6f55462e168743f0ca7d7f92cabe9ca54c237998145a9fbfe6", 1),
    ("ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72",
     "65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c", 1),
    ('"readonly RAW_SIZE=6965248"', '"readonly RAW_SIZE=6969344"', 1),
    ("ed 3a 4b f0 85 10 bd d5 c1 7 c1 10 18 3b 1c e9 85 df c5 59 4c 8a fa e5 4b df fe 0 6f b5 66 6",
     "9f 80 b0 56 aa 87 bf 7b cc cb 49 c9 bc 56 6f c5 b6 23 5 b0 c3 bd cc f5 f1 d8 64 5d 6a f 41 0", 1),
    ("variant=cpu9-progress-ledger",
     "variant=cpu9-membership-lock-repair", 1),
    ("dt_semantics=unchanged-serviceability-admission-tree-plus-CPU9-progress-package-provenance-leaf",
     "dt_semantics=unchanged-serviceability-admission-tree-plus-membership-lock-repair-package-provenance-leaf", 1),
    ('output_name="candidate-a72-cpu9-progress-${RAW_SHA256:0:8}"',
     'output_name="candidate-a72-cpu9-membership-lock-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-cpu9-progress-build",
     "validation=a72-cpu9-membership-lock-repair-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe membership-lock candidate derivation: expected "
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
