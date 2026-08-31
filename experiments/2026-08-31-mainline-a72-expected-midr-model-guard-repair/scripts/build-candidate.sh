#!/usr/bin/env bash

# Source-pin the audited r0p1 assembler and retarget it to the exact
# expected-MIDR model-guard repair package and composed runtime DT.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=914879f48cfcd5a56004a630d5ba696d7078b1c8528cbcd94bc050f3a43f1201
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-31-mainline-a72-r0p1-expected-pair-repair/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-expected-midr-model-guard.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("replacements = (\n",
     "replacements = (\n"
     "    (\"5d7b936aebcfdc73af86ae3158fba672532da6c567eb0628e1ea3c1bc0821659\",\n"
     "     \"556540ed817e19105bf5a4a059dd3fef9eb6d02dc0ca525c0b23a15598c7a248\", 1),\n",
     1),
    ("e0090fe57490eebe80750d2130a9411edb195e37",
     "8810735dd86f88122821c3309e7a5be5386cd9b6", 1),
    ("f56c27ec06b02398cbb957344c539d271d6bf2d151bc379be3c7c684a937c79a",
     "bc552777470280765ff40101ac55d82764fb8ebe5e84253e65e4621fb0f978d1", 1),
    ("809d910a9b93eaae8f5adea4a606229f0d8ff7bef2666f4e5c474990b2f5e50f",
     "a9c6eeb178283a49248b36bba86d50499ec49543058c7a73923a9214cb9c5fc3", 1),
    ("e31d6b12d3ec35cd736ac9e2be1203c0e29ef7c3e5393c98cbdba9ee81fdd7c1",
     "3d28d47dbdbca0674581dbd8132876240dcea0c547e3dbf4b0f260c528bd2373", 1),
    ("3eb483065eaccd4ceab3fe40df044a312070235c0b66aeefa1bd2bf0ef3a655a",
     "00546af2c517cbe6004a27560d8c28cd13d5eda5077e569a43738c71ed10578d", 1),
    ("417111b329be60ff83a5adbca31231682728b679ca1ef23cda37ec9cee4cd617",
     "5ff252562aad8239ff27f0bd57b0fb19dfaa6fcdbaf16302c6f77d4ae000d894", 1),
    ("6083935bbfba438a36c8ce23e75165b68e503fa813361828c98abfb5e741d505",
     "bf7ebec8193e6139cc544b0d3952154cdaabf895cd477d6552139245854ce83e", 1),
    ("b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d",
     "5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69", 1),
    ("gemini-mt6797-a72-r0p1-expected-pair-repair.boot.img",
     "gemini-mt6797-a72-expected-midr-model-guard-repair.boot.img", 1),
    ("74 69 23 c7 8b bf a6 63 4a 3d 5 92 55 7c ae ea 53 ee 82 5d cc e1 e4 b5 4b f2 17 6e 7d 88 44 d2",
     "88 c2 33 35 c6 89 7f d e6 aa df 7d ed 3d 7a 1f 42 aa 4f 13 df 14 1b 18 b4 3c 7 b2 fb 17 e9 85", 1),
    ("experiment=2026-08-31-mainline-a72-r0p1-expected-pair-repair",
     "experiment=2026-08-31-mainline-a72-expected-midr-model-guard-repair", 1),
    ("validation=r0p1-expected-pair-repair-package",
     "validation=expected-midr-model-guard-repair-package", 1),
    ('output_name="candidate-a72-r0p1-expected-pair-repair-${RAW_SHA256:0:8}"',
     'output_name="candidate-a72-expected-midr-model-guard-repair-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-r0p1-expected-pair-repair-build",
     "validation=a72-expected-midr-model-guard-repair-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe model-guard candidate derivation: expected {count}, "
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
