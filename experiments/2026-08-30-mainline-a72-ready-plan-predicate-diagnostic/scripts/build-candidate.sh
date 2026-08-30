#!/usr/bin/env bash

# Source-pin the proven serviceability assembler and retarget only the diagnostic package,
# provenance leaf, exact candidate identity, and experiment labels.
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

derived=$(mktemp "$script_dir/.derived-build-a72-ready-plan-diagnostic.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("5abde763316ab358d7f5cb1a3b6a461eb0a2ed99", "1df0f12f2e9a4b976e03ec4de674b1185e7d90ba", 1),
    ("68b04b4dc3a46cd61310678d2f772450dccf42087e64fa4902cb9f8439dd8d9c", "8f195d672ad6a5cc85ec6cb2bfdac2d406b956521145696914cb2343023a6a08", 1),
    ("2b0ef4482e92d734385cfd794b49ed7cd65a4415731c7f9c3ee276fe603730ce", "48dd68028ad3121b900156b3f86cab8cec1075332e39741050c7df2f2815d353", 1),
    ("073cf7b491e0ac3cf7925a3b2c73660554fd6597218a33e1655830eed59bda2b", "8cd85c3ff004d7545217f4bc352e41c61562ccda54ebdfa2ba2629c4faf6b8c8", 1),
    ("45b3dbeda5e3ff119e51d57c7e23dfef33d6ae9a9a6a493fbd5a5e9f58327bda", "df4cfec102d5032abec3ee1ccb8c4d076eb0939e20adc343da4b18f205680069", 1),
    ("b17e485aa14119a7c56bea6ccc657b7d583ee1069642035b1201ae8848172634", "4797280183c39572ba55b6edcb32ef9b502faac860534f00131f3ca966a5461f", 1),
    ("8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2", "818dece52aa4361840d99525e3f439476a10d32bfa6a67db3f8c7479f89d69df", 1),
    ("1921c30eba2e30da9d293d14efe3f2ac6e4f5a1aa6f633ea0567a21e987597fa", "08eec751391a48b59a32abdac8a5c2ff1aefd970395d444a94a6f003ea45626d", 1),
    ("f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", "7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272", 1),
    ("readonly RAW_SIZE=6948864", "readonly RAW_SIZE=6950912", 1),
    ("68 b8 64 d9 6a bb 58 fb 68 5f 41 45 82 7f fc c9 cc cc 37 2a 6c 26 95 ad d0 e1 44 98 ea 54 fc a", "4e 40 c2 f1 ce 53 2c ac df 9 79 8d 52 4e e4 8b b9 e1 93 d3 98 a8 26 aa c3 a9 db 24 3c 44 2f 49", 1),
    ("gemini-mt6797-a72-provenance-serviceability.boot.img", "gemini-mt6797-a72-ready-plan-predicate-diagnostic.boot.img", 1),
    (".derived-build-a72-provenance-serviceability.XXXXXXXX", ".derived-build-a72-ready-plan-diagnostic-inner.XXXXXXXX", 1),
    ("experiment=2026-08-30-mainline-a72-provenance-serviceability-composition", "experiment=2026-08-30-mainline-a72-ready-plan-predicate-diagnostic", 1),
    ("validation=provenance-serviceability-package", "validation=ready-plan-predicate-diagnostic-package", 1),
    ('output_name="candidate-a72-provenance-serviceability-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-ready-plan-predicate-diagnostic-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-provenance-serviceability-build", "validation=a72-ready-plan-predicate-diagnostic-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe predicate-diagnostic candidate derivation: expected {count}, found {actual}: {old}"
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
