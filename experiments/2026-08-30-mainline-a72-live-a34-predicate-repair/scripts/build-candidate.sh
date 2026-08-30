#!/usr/bin/env bash

# Source-pin the proven provenance/serviceability assembler and retarget only
# the repaired package, provenance leaf, exact candidate identity, and labels.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=6296d289d39e508b2d61b67d4df8ddde1e704c5bba555d2e7e7d350665dc5a67
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-30-mainline-a72-provenance-serviceability-composition/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-live-a34-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("5abde763316ab358d7f5cb1a3b6a461eb0a2ed99", "f361a704af745e503388bdaf63c4e161c7bb50fe", 1),
    ("68b04b4dc3a46cd61310678d2f772450dccf42087e64fa4902cb9f8439dd8d9c", "f9210bf11c6861977427f3af0d748c515c71ed70f935ba7e90ef2f8567bdb76d", 1),
    ("2b0ef4482e92d734385cfd794b49ed7cd65a4415731c7f9c3ee276fe603730ce", "717302bda5819b3ad5e0e824c28726d10f0099c8072b86b71df97a87425eb22c", 1),
    ("073cf7b491e0ac3cf7925a3b2c73660554fd6597218a33e1655830eed59bda2b", "e883aee92a5f53a57142d6ad850d0d101e95e62c9945760919cff7aa68518a9f", 1),
    ("45b3dbeda5e3ff119e51d57c7e23dfef33d6ae9a9a6a493fbd5a5e9f58327bda", "4ee372c3b481a46f40ca548a5f7c0afa3db9eb26bdcf3016dec03de00ae376c7", 1),
    ("b17e485aa14119a7c56bea6ccc657b7d583ee1069642035b1201ae8848172634", "5751e3a36319866d6b84995945fc4fca291d65151e4e710e4031ee39c75a0dde", 1),
    ("8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2", "7f3a23acec8060642b7c0d52a16b30cdfb7d52a55a70c984a008becb35a09c99", 1),
    ("1921c30eba2e30da9d293d14efe3f2ac6e4f5a1aa6f633ea0567a21e987597fa", "8fb8194b975989700f0c48b5ce1ab621feed515e4a5174fd36f4fd2039698a80", 1),
    ("f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", "7c96288818d6d3e0eb5547c675057bbe7789b0b62388b0a171681720da29f2a9", 1),
    ("readonly RAW_SIZE=6948864", "readonly RAW_SIZE=6955008", 1),
    ("68 b8 64 d9 6a bb 58 fb 68 5f 41 45 82 7f fc c9 cc cc 37 2a 6c 26 95 ad d0 e1 44 98 ea 54 fc a", "a6 90 59 5f 89 c9 b4 e8 f2 27 ea c6 eb 8b fc 98 1b a9 f2 e 6c 61 8b 67 60 96 38 8e f1 b7 43 ca", 1),
    ("gemini-mt6797-a72-provenance-serviceability.boot.img", "gemini-mt6797-a72-live-a34-predicate-repair.boot.img", 1),
    (".derived-build-a72-provenance-serviceability.XXXXXXXX", ".derived-build-a72-live-a34-repair-inner.XXXXXXXX", 1),
    ("experiment=2026-08-30-mainline-a72-provenance-serviceability-composition", "experiment=2026-08-30-mainline-a72-live-a34-predicate-repair", 1),
    ("validation=provenance-serviceability-package", "validation=live-a34-predicate-repair-package", 1),
    ('output_name="candidate-a72-provenance-serviceability-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-live-a34-predicate-repair-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-provenance-serviceability-build", "validation=a72-live-a34-predicate-repair-build", 1),
    ("unsafe candidate derivation", "unsafe live-A34-repair candidate derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe live-A34-repair candidate derivation: expected {count}, found {actual}: {old}"
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
