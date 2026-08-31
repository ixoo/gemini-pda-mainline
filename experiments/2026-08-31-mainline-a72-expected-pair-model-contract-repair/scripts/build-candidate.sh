#!/usr/bin/env bash

# Source-pin the audited stage-ledger assembler and retarget it to the exact
# expected-pair model-contract repair package and composed runtime DT.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=9165b6d9b557b157da9ea91c202d14d5bbada88c9064e9ce312d5a430ae1b35e
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-31-mainline-a72-effect-plan-stage-ledger/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-expected-pair-model-contract.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("3a8adb13b24e6842a35feca1ac3ca8779a1574331a6b7413c2f597d93152e6b5",
     "228ef7be660b62e43a5debce8b0bf496673b612312218968b94e51aab0d22697", 1),
    ("6382feb58423c529d4c46ae98253661c158b7bc9",
     "aa2efd3f00f9b632a5a2c570e4319e6c987e3d90", 1),
    ("777bd911f0fcbd8f931a8dbbc11deb32270bb80a5361db8d6223b2c0790a7eb7",
     "68c0fb09b8ad32c4c32921f7d05e57ea991c133df31094644d9fdc180562e7c2", 1),
    ("3e46f12cb6d899de3f00b277c7e18bf79fb765bd76667be20bf4211ff68d02ad",
     "d847bd0ccd3800ea0f2e32964303103ea64c0dbeef7c9b63df2d748addc4811a", 1),
    ("9070b3140c9af07922ef75b3d309ebec767afc76fd5702b4212d9382e26f2455",
     "dd4705b7d4fbaea5f4d30e47d8f20ef91e40195e6ecfe832f470c2a683fb5c76", 1),
    ("fa6fe88f2704dc01cd5479274e21847467b9f37b2e31af78b784eb932d67fd09",
     "52d97b159b9b356580a0d6bef221bb8fb1ace6d9a6c03e3ef8bde28ea9666965", 1),
    ("7116bc604fd732dad39e9365579d7fa0e42c185c201134364e699f5e572be964",
     "cab076e835a98fc7fe247ddb502df1cb7cec8e971552c5f6ef7fb5a5153314ff", 1),
    ("37de54a0e8ef61b9b7f9e5a05bcec1a2f2ea869c1e38b509ddf20b27c4098496",
     "c66c24c626decb416d1bdeb9818d0bb379ae464f812e323c39a415a9313a1fe1", 1),
    ("b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1",
     "42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee", 1),
    ("gemini-mt6797-a72-effect-plan-stage-ledger.boot.img",
     "gemini-mt6797-a72-expected-pair-model-contract-repair.boot.img", 1),
    ("ef c5 25 ae 46 a8 d9 55 9a ad e5 14 9 73 80 bc 26 a8 20 d3 e3 a8 74 3 fb 1b 4b 9e 44 a8 2d 48",
     "2d 48 ba f8 66 62 d8 13 a c2 76 b6 d8 22 65 8b 47 8f 1e 6c 87 33 f0 a6 c8 2d 92 8c c4 b1 e1 bc", 1),
    ("experiment=2026-08-31-mainline-a72-effect-plan-stage-ledger",
     "experiment=2026-08-31-mainline-a72-expected-pair-model-contract-repair", 1),
    ("validation=effect-plan-stage-ledger-package",
     "validation=expected-pair-model-contract-repair-package", 1),
    ('output_name="candidate-a72-effect-plan-stage-ledger-${RAW_SHA256:0:8}"',
     'output_name="candidate-a72-expected-pair-model-contract-repair-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-effect-plan-stage-ledger-build",
     "validation=a72-expected-pair-model-contract-repair-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe expected-pair candidate derivation: expected {count}, "
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
