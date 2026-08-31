#!/usr/bin/env bash

# Source-pin the proven SRAM diagnostic assembler and retarget only the
# selector-mask repair package, provenance leaf, identities, and labels.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=aef275541854639098a67bf3b9c09edd56e6d6b574ae6a836b50fa51787403bb
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-31-mainline-a72-sram-p28-terminal-diagnostic/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-selector-mask-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("3508f303275c461c728a500c307ad0d9d2074f28", "2d682d8a48c7169a8f5ab5928ff6d61263e5fa64", 1),
    ("4325c2fe7119bffc2f8f199c11b6193bb4d7d579889b4c9d479a87d90fc8d8be", "6fb2dabde0d8056011d0b3ef166ec4e7cf621e7c016ce1ff06b0e76b933adb88", 1),
    ("09887d8091b565c91d84663585b4338276141ff2442543ab99e286f3ac92893e", "d9b45182645c4a37a7f38d37597c54c59d8d6749db672331c2dfadc1b1eb2b6f", 1),
    ("299b5d527b5c0136aec32ac78254fa1cb6a7059bffc5df3163951f70dfbfa564", "795f8d1066ca39eaa6ee750aa9a13ba9e61d3705959d266dc07f6fb928f69f92", 1),
    ("d07f2eccbc332b1b12894967e96c90b56f6b08bc1cf764bb979a008a180dd69a", "339e3d0e7254798abcda39258595623dc826e0982330754e481f8027e410f3d9", 1),
    ("b2c9104d41e2205f10ef29fcb126e76a8574195b6a9764ffde27f892370ec0ea", "ce0fe8ca71c5c770ca8271f6eb5ced2f1e5f2f1d008a7525d603625dbebe5a36", 1),
    ("8346f271280739437a013e04a3f9992981adbaa302e2c44add844008f832902d", "9e0445cc404cd76aff96cfbfb7a9305b91cd1ff71918aaf6ca451f6f11780be3", 1),
    ("0e1be4e07472e5050ab52e91558bd6cf89a5fa509a009c5746085547dc6599f1", "add111acedb0850983371efed982c1b569adc8fc181cad86402643d426371942", 1),
    ("7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3", "cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743", 1),
    ("fe 81 d bc e4 86 b6 b9 77 53 58 79 b3 72 d3 21 6b 5e c5 76 55 1c fc af 1c 4a c4 55 3f 35 63 42", "91 d3 28 ee 1 ba c2 16 64 e0 ae fc 68 9d 69 1 c5 5a b1 6a 97 3e d6 1b 66 30 99 4d f1 1 49 65", 1),
    ("gemini-mt6797-a72-sram-p28-terminal-diagnostic.boot.img", "gemini-mt6797-a72-sram-selector-mask-contract-repair.boot.img", 1),
    (".derived-build-a72-sram-p28-diagnostic.XXXXXXXX", ".derived-build-a72-selector-mask-repair-inner.XXXXXXXX", 1),
    ("experiment=2026-08-31-mainline-a72-sram-p28-terminal-diagnostic", "experiment=2026-08-31-mainline-a72-sram-selector-mask-contract-repair", 1),
    ("validation=sram-p28-terminal-diagnostic-package", "validation=sram-selector-mask-contract-repair-package", 1),
    ('output_name="candidate-a72-sram-p28-terminal-diagnostic-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-sram-selector-mask-contract-repair-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-sram-p28-terminal-diagnostic-build", "validation=a72-sram-selector-mask-contract-repair-build", 1),
    ("unsafe SRAM/P28 diagnostic candidate derivation", "unsafe selector-mask repair candidate derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe selector-mask repair candidate derivation: expected "
            f"{count}, found {actual}: {old}"
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
