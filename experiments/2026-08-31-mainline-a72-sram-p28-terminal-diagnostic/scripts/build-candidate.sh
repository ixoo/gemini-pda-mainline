#!/usr/bin/env bash

# Source-pin the proven isolation-repair assembler and retarget only the
# diagnostic package, provenance leaf, exact candidate identities, and labels.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=deb78bc0e45ed31e78ac411795af1e0326d0d5fe57b5bf9ad4a8b04c27609114
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-30-mainline-a72-isolation-held-result-contract-repair/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-sram-p28-diagnostic.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
size_anchor = '    ("fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5", "510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726", 1),'
size_replacement = (
    '    ("readonly RAW_SIZE=6957056", "readonly RAW_SIZE=6955008", 1),\n'
    + size_anchor
)
replacements = (
    ("62557cd201438802cbbc0034e7635f16a716b191", "3508f303275c461c728a500c307ad0d9d2074f28", 1),
    ("d806a4900bc005c02a2470c2617700493b3e6a0c7ceed89e1e903b39227d6368", "4325c2fe7119bffc2f8f199c11b6193bb4d7d579889b4c9d479a87d90fc8d8be", 1),
    ("387a36725b7769a87228408c2735ae883e0b1f9393f99e61674136832fceae22", "09887d8091b565c91d84663585b4338276141ff2442543ab99e286f3ac92893e", 1),
    ("9cd410101eb8e3e7470b9d2b777bf8fa96a9bc0050f3f55d7bf57fd7a0a936cc", "299b5d527b5c0136aec32ac78254fa1cb6a7059bffc5df3163951f70dfbfa564", 1),
    ("bb206991024a8b9f0b477b326b07bd61e880ebac964ed331495cf857f0225636", "d07f2eccbc332b1b12894967e96c90b56f6b08bc1cf764bb979a008a180dd69a", 1),
    ("dba7276e80a2b7a00606ee7ed3c78588c20b9aed321cfb7fd9b403e05087571b", "b2c9104d41e2205f10ef29fcb126e76a8574195b6a9764ffde27f892370ec0ea", 1),
    ("57fb4aae9cf3f5767e7b3d8ae95238d806e3ed55bfe2298d587f7fc550a3c7dd", "8346f271280739437a013e04a3f9992981adbaa302e2c44add844008f832902d", 1),
    ("53b52ffcbe700866e4d96c3ae84e6cc98910ae0dc45a000c815f212a4ba9662f", "0e1be4e07472e5050ab52e91558bd6cf89a5fa509a009c5746085547dc6599f1", 1),
    (size_anchor, size_replacement, 1),
    ("510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726", "7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3", 1),
    ("29 5d 1b 4e b6 2c bf 1f ad d2 c2 c8 3c db 15 12 a4 52 1a 23 4d 72 84 27 13 21 f9 48 a1 9e ce 16", "fe 81 d bc e4 86 b6 b9 77 53 58 79 b3 72 d3 21 6b 5e c5 76 55 1c fc af 1c 4a c4 55 3f 35 63 42", 1),
    ("gemini-mt6797-a72-isolation-held-result-contract-repair.boot.img", "gemini-mt6797-a72-sram-p28-terminal-diagnostic.boot.img", 1),
    (".derived-build-a72-isolation-held-result-repair-inner.XXXXXXXX", ".derived-build-a72-sram-p28-diagnostic-inner.XXXXXXXX", 1),
    ("experiment=2026-08-30-mainline-a72-isolation-held-result-contract-repair", "experiment=2026-08-31-mainline-a72-sram-p28-terminal-diagnostic", 1),
    ("validation=isolation-held-result-contract-repair-package", "validation=sram-p28-terminal-diagnostic-package", 1),
    ('output_name="candidate-a72-isolation-held-result-contract-repair-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-sram-p28-terminal-diagnostic-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-isolation-held-result-contract-repair-build", "validation=a72-sram-p28-terminal-diagnostic-build", 1),
    ("unsafe isolation-result repair candidate derivation", "unsafe SRAM/P28 diagnostic candidate derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe SRAM/P28 diagnostic candidate derivation: expected "
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
