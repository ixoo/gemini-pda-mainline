#!/usr/bin/env bash

# Source-pin the audited P30E assembler and retarget it to the exact
# post-capabilities checkpoint package and composed runtime DT.
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

derived=$(mktemp "$script_dir/.derived-build-a72-post-capabilities-checkpoints.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("23b21b6f4f8cbb3af0cefd610d5d0e5961f7fa51",
     "590dbedc974c6a40f34c1d4c34e9bb571bc2a10d", 1),
    ("c59324bcd04b358a4563bd39d1dcb9c03a47ecef087b57a6b1d5b4cf03f4a82b",
     "b875484a9366d30889ccc823d0510d3982ea989cf03f6758817d25b61becadab", 1),
    ("f629b74a5dc999d2e353bd25be4710d7bf696bc7dcc9b9558bda9e2f1edded74",
     "a70d23c793ca41ac2a5d8043da8aba3ea432500a9f95c27d9c888db583bbef58", 1),
    ("135703294fb2dfdecbf200b83e6dfb5d4e49241cbe64a27712d6e055772b35bc",
     "5d7b936aebcfdc73af86ae3158fba672532da6c567eb0628e1ea3c1bc0821659", 1),
    ("7f5bf270c09b7f603c4f449a3c0e28fd63e6145c3a053bf36119c58753e399aa",
     "c5023a5bada66f539a4ab4c3b1c6b7b6f5c0eeba63da20284ff0f551ba5db243", 1),
    ("d8b1c5161d0b545ac5f3873929bfed12d0a0bb50fd459c7c093af2824d7d8961",
     "d03c682f7c7f153f61cabab3f5d3a9f43bd80759ac49c14a1dbc1f02208de5bb", 1),
    ("461e2d1c4b88a79740747d6755d2c402bab6367c240380e8c2a20c6a47055de3",
     "68c57cb8c8eda745c2d42c179ef224821661940115d683e0e0d34e99ea81a0d3", 1),
    ("b80dfc49dd22a7830afdadbe3138c0e5131a2da1cbca7012d6c90ad09002e463",
     "cb7c886e2cb9d225c75f413217394ae64a12661b36f7c1d18048d27ad338fc0c", 1),
    ("a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453",
     "9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630", 1),
    ("readonly RAW_SIZE=6955008", "readonly RAW_SIZE=6957056", 1),
    ("gemini-mt6797-a72-p30e-entry-diagnostic.boot.img",
     "gemini-mt6797-a72-post-capabilities-checkpoints.boot.img", 1),
    ("96 fe 21 66 17 bc fb 42 15 94 f4 d1 f9 60 ef f9 62 ae 8a 92 2 11 cf 41 16 9b 30 f7 ed 55 94 55",
     "7c 6c 9a 78 5e 2c cf 27 7e 61 a1 55 2c 4c 2f b2 19 e3 37 1b 29 21 b0 b4 1a 9e da 1d 2f 7e a6 90", 1),
    (
        "arm64_mt6797_a72_p30e_target_claim arm64_mt6797_a72_p30e_target_publish",
        "arm64_mt6797_a72_p30e_target_claim arm64_mt6797_a72_p30e_target_checkpoint arm64_mt6797_a72_p30e_target_publish",
        1,
    ),
    ("experiment=2026-08-31-mainline-a72-p30e-entry-diagnostic",
     "experiment=2026-08-31-mainline-a72-post-capabilities-checkpoints", 1),
    ("validation=p30e-entry-diagnostic-package",
     "validation=post-capabilities-checkpoints-package", 1),
    ('output_name="candidate-a72-p30e-entry-diagnostic-${RAW_SHA256:0:8}"',
     'output_name="candidate-a72-post-capabilities-checkpoints-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-p30e-entry-diagnostic-build",
     "validation=a72-post-capabilities-checkpoints-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe post-capabilities candidate derivation: expected {count}, "
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
