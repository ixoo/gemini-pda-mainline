#!/usr/bin/env bash

# Source-pin the audited post-capabilities assembler and retarget it to the
# exact r0p1 expected-pair repair package and composed runtime DT.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=17cb3c3565e71cdf431537d424d7647b08f38c34c5f9a7b9daddd32a29b0c4b4
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-31-mainline-a72-post-capabilities-checkpoints/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-r0p1-expected-pair-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("590dbedc974c6a40f34c1d4c34e9bb571bc2a10d",
     "e0090fe57490eebe80750d2130a9411edb195e37", 1),
    ("b875484a9366d30889ccc823d0510d3982ea989cf03f6758817d25b61becadab",
     "f56c27ec06b02398cbb957344c539d271d6bf2d151bc379be3c7c684a937c79a", 1),
    ("a70d23c793ca41ac2a5d8043da8aba3ea432500a9f95c27d9c888db583bbef58",
     "809d910a9b93eaae8f5adea4a606229f0d8ff7bef2666f4e5c474990b2f5e50f", 1),
    ("c5023a5bada66f539a4ab4c3b1c6b7b6f5c0eeba63da20284ff0f551ba5db243",
     "e31d6b12d3ec35cd736ac9e2be1203c0e29ef7c3e5393c98cbdba9ee81fdd7c1", 1),
    ("d03c682f7c7f153f61cabab3f5d3a9f43bd80759ac49c14a1dbc1f02208de5bb",
     "3eb483065eaccd4ceab3fe40df044a312070235c0b66aeefa1bd2bf0ef3a655a", 1),
    ("68c57cb8c8eda745c2d42c179ef224821661940115d683e0e0d34e99ea81a0d3",
     "417111b329be60ff83a5adbca31231682728b679ca1ef23cda37ec9cee4cd617", 1),
    ("cb7c886e2cb9d225c75f413217394ae64a12661b36f7c1d18048d27ad338fc0c",
     "6083935bbfba438a36c8ce23e75165b68e503fa813361828c98abfb5e741d505", 1),
    ("9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630",
     "b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d", 1),
    ("readonly RAW_SIZE=6957056", "readonly RAW_SIZE=6957056", 1),
    ("gemini-mt6797-a72-post-capabilities-checkpoints.boot.img",
     "gemini-mt6797-a72-r0p1-expected-pair-repair.boot.img", 1),
    ("7c 6c 9a 78 5e 2c cf 27 7e 61 a1 55 2c 4c 2f b2 19 e3 37 1b 29 21 b0 b4 1a 9e da 1d 2f 7e a6 90",
     "74 69 23 c7 8b bf a6 63 4a 3d 5 92 55 7c ae ea 53 ee 82 5d cc e1 e4 b5 4b f2 17 6e 7d 88 44 d2", 1),
    ("experiment=2026-08-31-mainline-a72-post-capabilities-checkpoints",
     "experiment=2026-08-31-mainline-a72-r0p1-expected-pair-repair", 1),
    ("validation=post-capabilities-checkpoints-package",
     "validation=r0p1-expected-pair-repair-package", 1),
    ('output_name="candidate-a72-post-capabilities-checkpoints-${RAW_SHA256:0:8}"',
     'output_name="candidate-a72-r0p1-expected-pair-repair-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-post-capabilities-checkpoints-build",
     "validation=a72-r0p1-expected-pair-repair-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe r0p1 candidate derivation: expected {count}, "
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
