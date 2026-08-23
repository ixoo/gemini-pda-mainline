#!/usr/bin/env bash

# Source-pin the proven read-free clock candidate assembler and retarget it to
# the exact coexistence package, DT, release, and attributable marker.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=390964a7a783a5ff73a3c638fe9785fb48fdef86cfffdf545f48f12444315505

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-23-mainline-clock-backend-first-dmesg-entry/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] ||
	die 'source candidate builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source candidate builder identity changed'

derived="$(mktemp "$script_dir/.derived-build-candidate-clock-cspm.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("d8d98fccee89a77fd5a6bc1da3f55cb3d1366b60", "67e40d761f9e83063742a8e36ffb001c6fa3d38e", 1),
    ("da921x-clock-entry-first-dmesg", "da921x-clock-cspm-coexistence", 1),
    ("7.1.3-gemini-clock-entry-first-dmesg", "7.1.3-gemini-clock-cspm-coexist", 1),
    ("984acb29964a7e111da333d457d1bea48c6952cad2fd95c61b9bedf89d1d0c0e", "35dbdc28c22850d1d72ff15dc0f9f3db091256f8abe024c40ed7eb02316dbc0e", 1),
    ("fd5e77c8194834b5da39f397bea2d4873ad8372e2802c8b6ec640518407b430e", "c68756f4521e2cba57a112189a0bf27e8e086ab8feb82ac87ec4fd74eef86cc2", 1),
    ("7c1d5f69924a8280e36ff111b411c4fbecd32243e8d0da9e9f6f4b333a21e100", "8033f913a4cfd78c2fca9d901c5838285717e9929fc577ea369d7066423c2126", 1),
    ("0a19f77a527e15997430311358e5ae499271eb03573cf6785b2dffdaf52427a7", "0c6b20c57c0fe64f067b9fc1a216a372e1e6ef3ffb6f51e536196f3816490304", 1),
    ("df7f396405c06aca97b8ebe866bb86cd17459636a83affd8f35220d28c0af099", "15605e77e949d73753ab229d1a7ff695f13da6c494aa0a81e780f922f762d303", 1),
    ("7e3e5c81e128b4a5b565fe47d8186b19b7c663f59b3ed266d95ed02d9a6e30bd", "1f062bce27bc48e50ac96df2bcdf1a4c5eb2be99f7de7b6d46fa8832f1cd8104", 1),
    ("37a41e9dd67235e154f918e4f7db930dbbe8566448c6afd4f1a1de2e49b92f5e", "703ceb7815c4e443f4504000be2c032eb452ff5aa941bfb3da56d3225933e4c2", 1),
    ("251e792573bd9961d3f2b90563cff85d851c6502008d97e1ae502fbacda49b83", "dc09377159237c99ef779fbc24824df6c14b8258a9dd237cb7a113e9ed61e6f2", 1),
    ("40b7c663b835bcf4c48f4149f14aa416343e3e322ab78a0aa38448afff9455b4", "ae4010449e72ed4d02643616073e8d74f7cad25adb4afb5db69030d39eb324e7", 1),
    ("6899712", "6897664", 1),
    ("gemini-clkfdm", "gemini-clkcspm", 1),
    ("gemini-mt6797-clock-entry-first-dmesg.boot.img", "gemini-mt6797-clock-cspm-coexistence.boot.img", 1),
    ("-gemini-clock-entry-first-dmesg", "-gemini-clock-cspm-coexist", 1),
    ("portable-fetched-clock-entry-first-dmesg-package", "portable-fetched-clock-cspm-coexistence-package", 1),
    (".clock-entry-first-dmesg.XXXXXXXX", ".clock-cspm-coexistence.XXXXXXXX", 1),
    ("experiment=2026-08-23-mainline-clock-backend-first-dmesg-entry", "experiment=2026-08-23-mainline-clock-backend-cspm-coexistence", 1),
    ("runtime_hypothesis=clock-driver-registration-and-read-free-probe-entry", "runtime_hypothesis=single-handoff-owned-cspm-restores-clock-i2c6-da921x-coexistence", 1),
    ("candidate-clock-entry-first-dmesg-${RAW_SHA256:0:8}", "candidate-clock-cspm-coexistence-${RAW_SHA256:0:8}", 1),
    ("clock-backend-first-dmesg-candidate-build", "clock-backend-cspm-coexistence-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe candidate derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

old = """[[ "$(grep -aFo 'GEMINI_CLOCK_BACKEND_FIRST_DMESG_LIVE_V1' "$image" |
\twc -l | tr -d ' ')" == 3 ]] || die 'live marker count changed'
"""
new = old + """[[ "$(grep -aFo 'GEMINI_CLOCK_BACKEND_CSPM_COEXISTENCE_V1' "$image" |
\twc -l | tr -d ' ')" == 1 ]] || die 'coexistence marker count changed'
"""
if text.count(old) != 1:
    raise SystemExit("unsafe candidate derivation: live marker gate changed")
text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"

set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
