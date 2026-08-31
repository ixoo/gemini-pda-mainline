#!/usr/bin/env bash

# Source-pin the audited model-guard assembler and retarget it to the exact
# effect-plan stage-ledger package and composed runtime DT.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=af2496679a6263e6bc914295843f1cbb316f5d8ad2299478a7b23cbe2c7791c3
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-31-mainline-a72-expected-midr-model-guard-repair/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-effect-plan-stage-ledger.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("556540ed817e19105bf5a4a059dd3fef9eb6d02dc0ca525c0b23a15598c7a248",
     "3a8adb13b24e6842a35feca1ac3ca8779a1574331a6b7413c2f597d93152e6b5", 1),
    ("8810735dd86f88122821c3309e7a5be5386cd9b6",
     "6382feb58423c529d4c46ae98253661c158b7bc9", 1),
    ("bc552777470280765ff40101ac55d82764fb8ebe5e84253e65e4621fb0f978d1",
     "777bd911f0fcbd8f931a8dbbc11deb32270bb80a5361db8d6223b2c0790a7eb7", 1),
    ("a9c6eeb178283a49248b36bba86d50499ec49543058c7a73923a9214cb9c5fc3",
     "3e46f12cb6d899de3f00b277c7e18bf79fb765bd76667be20bf4211ff68d02ad", 1),
    ("3d28d47dbdbca0674581dbd8132876240dcea0c547e3dbf4b0f260c528bd2373",
     "9070b3140c9af07922ef75b3d309ebec767afc76fd5702b4212d9382e26f2455", 1),
    ("00546af2c517cbe6004a27560d8c28cd13d5eda5077e569a43738c71ed10578d",
     "fa6fe88f2704dc01cd5479274e21847467b9f37b2e31af78b784eb932d67fd09", 1),
    ("5ff252562aad8239ff27f0bd57b0fb19dfaa6fcdbaf16302c6f77d4ae000d894",
     "7116bc604fd732dad39e9365579d7fa0e42c185c201134364e699f5e572be964", 1),
    ("bf7ebec8193e6139cc544b0d3952154cdaabf895cd477d6552139245854ce83e",
     "37de54a0e8ef61b9b7f9e5a05bcec1a2f2ea869c1e38b509ddf20b27c4098496", 1),
    ("5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69",
     "b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1", 1),
    ("gemini-mt6797-a72-expected-midr-model-guard-repair.boot.img",
     "gemini-mt6797-a72-effect-plan-stage-ledger.boot.img", 1),
    ("88 c2 33 35 c6 89 7f d e6 aa df 7d ed 3d 7a 1f 42 aa 4f 13 df 14 1b 18 b4 3c 7 b2 fb 17 e9 85",
     "ef c5 25 ae 46 a8 d9 55 9a ad e5 14 9 73 80 bc 26 a8 20 d3 e3 a8 74 3 fb 1b 4b 9e 44 a8 2d 48", 1),
    ("experiment=2026-08-31-mainline-a72-expected-midr-model-guard-repair",
     "experiment=2026-08-31-mainline-a72-effect-plan-stage-ledger", 1),
    ("validation=expected-midr-model-guard-repair-package",
     "validation=effect-plan-stage-ledger-package", 1),
    ('output_name="candidate-a72-expected-midr-model-guard-repair-${RAW_SHA256:0:8}"',
     'output_name="candidate-a72-effect-plan-stage-ledger-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-expected-midr-model-guard-repair-build",
     "validation=a72-effect-plan-stage-ledger-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe effect-plan candidate derivation: expected {count}, "
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
