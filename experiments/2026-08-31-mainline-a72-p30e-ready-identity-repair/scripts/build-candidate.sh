#!/usr/bin/env bash

# Source-pin the audited P30E assembler and retarget it to the exact
# READY-identity repair package and composed runtime DT.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=1f909041374f4d5272b4478c43c46f21d3f76be8938a9fb12c1e938feccc0f3d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-31-mainline-a72-p30e-entry-diagnostic/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-p30e-ready-identity-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("23b21b6f4f8cbb3af0cefd610d5d0e5961f7fa51", "8fa0757b9e0c2e926906d3ac15ece2a7673b5b47", 1),
    ("c59324bcd04b358a4563bd39d1dcb9c03a47ecef087b57a6b1d5b4cf03f4a82b", "12b8781c203858b5442e9774e98eed4d1825c92e7adb379bc2716a72a9972d07", 1),
    ("f629b74a5dc999d2e353bd25be4710d7bf696bc7dcc9b9558bda9e2f1edded74", "eef224a19223886721ff6e58225dab26039c52080bf4e267fc1acb02df052e49", 1),
    ("7f5bf270c09b7f603c4f449a3c0e28fd63e6145c3a053bf36119c58753e399aa", "50b8f400dd672ae1ebb584c125eca88c11c64c89a9ec8cd97a03b6a1ff6ab238", 1),
    ("d8b1c5161d0b545ac5f3873929bfed12d0a0bb50fd459c7c093af2824d7d8961", "e9027e099089208cde7109e2123304aa2263dca4c0e3d28b2ef29890669bd088", 1),
    ("461e2d1c4b88a79740747d6755d2c402bab6367c240380e8c2a20c6a47055de3", "614556198ae2459459d849d6428347009f343582a678f056802b7775224c3137", 1),
    ("b80dfc49dd22a7830afdadbe3138c0e5131a2da1cbca7012d6c90ad09002e463", "417d911fa11b746e4ee2ba3c279e24c7308659b00b5af3c7a9572131f047eaba", 1),
    ("a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453", "459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16", 1),
    ("gemini-mt6797-a72-p30e-entry-diagnostic.boot.img", "gemini-mt6797-a72-p30e-ready-identity-repair.boot.img", 1),
    ("96 fe 21 66 17 bc fb 42 15 94 f4 d1 f9 60 ef f9 62 ae 8a 92 2 11 cf 41 16 9b 30 f7 ed 55 94 55", "bb 56 3 f 37 5 71 7 9b d2 21 ad f4 9d d8 f3 2f 6b e7 25 1f 13 40 6b 90 d4 a0 61 58 27 40 9a", 1),
    ("experiment=2026-08-31-mainline-a72-p30e-entry-diagnostic", "experiment=2026-08-31-mainline-a72-p30e-ready-identity-repair", 1),
    ("validation=p30e-entry-diagnostic-package", "validation=p30e-ready-identity-repair-package", 1),
    ('die \\"raw candidate changed: sha=$raw_sha\\"', 'die \\"raw candidate changed: size=$(stat -f \'%z\' \\"$stage/$BOOT_FILE\\" 2>/dev/null || stat -c \'%s\' \\"$stage/$BOOT_FILE\\") sha=$raw_sha\\"', 1),
    ('output_name="candidate-a72-p30e-entry-diagnostic-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-p30e-ready-identity-repair-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-p30e-entry-diagnostic-build", "validation=a72-p30e-ready-identity-repair-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E READY-identity candidate derivation: expected {count}, "
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
