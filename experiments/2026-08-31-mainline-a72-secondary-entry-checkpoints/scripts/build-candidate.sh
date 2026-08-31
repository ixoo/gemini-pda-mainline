#!/usr/bin/env bash

# Source-pin the audited P30E assembler and retarget it to the exact
# secondary-entry checkpoint package and composed runtime DT.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=44403f251e1c04f1aa2c6887ce6d6f4cc1b6c81ac7bf285f799b3e01efa0debf
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-31-mainline-a72-p30e-ready-identity-repair/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-secondary-entry-checkpoints.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        'replacements = (\n    ("23b21b6f4f8cbb3af0cefd610d5d0e5961f7fa51",',
        'replacements = (\n'
        '    ("135703294fb2dfdecbf200b83e6dfb5d4e49241cbe64a27712d6e055772b35bc", "5ac27f7a280aa87ed28644eeba756af80a02832da96725433800aebc09493e23", 1),\n'
        '    ("23b21b6f4f8cbb3af0cefd610d5d0e5961f7fa51",',
        1,
    ),
    ("8fa0757b9e0c2e926906d3ac15ece2a7673b5b47", "e91394af4bae2e131fd5e56ae122c7ef765058ee", 1),
    ("12b8781c203858b5442e9774e98eed4d1825c92e7adb379bc2716a72a9972d07", "01ad6f80d3e12b25a7d6bd46cc988ee1fa04b98bbb14d9665b1904a83af67644", 1),
    ("eef224a19223886721ff6e58225dab26039c52080bf4e267fc1acb02df052e49", "b588e88e2d285da4935c8604d35ae1db37f62ecd3e30004de2073e238c5a97c0", 1),
    ("50b8f400dd672ae1ebb584c125eca88c11c64c89a9ec8cd97a03b6a1ff6ab238", "231c631e010ecda7ae95269862d6bac9aaebe9a9b78162ee7bb5509471365bc9", 1),
    ("e9027e099089208cde7109e2123304aa2263dca4c0e3d28b2ef29890669bd088", "621d1fd4305b35d1b564a9b566cc78109d1041053a4b33cb1df280af457fb435", 1),
    ("614556198ae2459459d849d6428347009f343582a678f056802b7775224c3137", "1bc12e8dacff2cef9f248276de80c4e0d37ebd50d5a4e42ed9dc0164837b4046", 1),
    ("417d911fa11b746e4ee2ba3c279e24c7308659b00b5af3c7a9572131f047eaba", "fdf302e80ea4bb9dc9c0766151a4d3d6fe7ffb7e9f43dc13b3dcec481a9956be", 1),
    ("459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16", "6d0bf75b55ef981a915ba0b9a8d305d5713476acc4fc2ee95e4201f234b2253f", 1),
    ("gemini-mt6797-a72-p30e-ready-identity-repair.boot.img", "gemini-mt6797-a72-secondary-entry-checkpoints.boot.img", 1),
    ("bb 56 3 f 37 5 71 7 9b d2 21 ad f4 9d d8 f3 2f 6b e7 25 1f 13 40 6b 90 d4 a0 61 58 27 40 9a", "4e f5 c8 8c f6 4f 26 d6 1e 51 50 58 57 7c 85 7f 3 b1 4 9f 75 4b 28 23 47 5e 18 61 98 9a 15 82", 1),
    ("experiment=2026-08-31-mainline-a72-p30e-ready-identity-repair", "experiment=2026-08-31-mainline-a72-secondary-entry-checkpoints", 1),
    ("validation=p30e-ready-identity-repair-package", "validation=secondary-entry-checkpoints-package", 1),
    ('output_name="candidate-a72-p30e-ready-identity-repair-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-secondary-entry-checkpoints-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-p30e-ready-identity-repair-build", "validation=a72-secondary-entry-checkpoints-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe entry-checkpoint candidate derivation: expected {count}, "
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
