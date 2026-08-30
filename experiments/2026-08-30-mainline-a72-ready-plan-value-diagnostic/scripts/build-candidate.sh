#!/usr/bin/env bash

# Source-pin the proven predicate observer assembler and retarget only the
# value-observer package, provenance leaf, exact candidate identity, and labels.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=b03533bc463b5dd2a60ab9646bf7540d1df35a103783ef69e7587b7a90fec3db
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-30-mainline-a72-ready-plan-predicate-diagnostic/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-ready-plan-value.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("1df0f12f2e9a4b976e03ec4de674b1185e7d90ba", "e33dfbce2a5f0050403e827ff4b105790069848b", 1),
    ("8f195d672ad6a5cc85ec6cb2bfdac2d406b956521145696914cb2343023a6a08", "0b65b23388a03c4114e76f935013dfdcda21f764eb1000829bcbc38b9c1a64b8", 1),
    ("48dd68028ad3121b900156b3f86cab8cec1075332e39741050c7df2f2815d353", "2c82e22419db7571b4dccef8d633fe2dfb65786d682b47a0a8195ce2597e50ed", 1),
    ("8cd85c3ff004d7545217f4bc352e41c61562ccda54ebdfa2ba2629c4faf6b8c8", "1c0a04c7ccf95603c072694c5d58f2c85bb45a5d4ac60a48eddb29797ca657e2", 1),
    ("df4cfec102d5032abec3ee1ccb8c4d076eb0939e20adc343da4b18f205680069", "10848fb119857b1906ba820507205a77dcb11e0f9e2aecf674274445bc351ee8", 1),
    ("4797280183c39572ba55b6edcb32ef9b502faac860534f00131f3ca966a5461f", "a24875b0d8377a34c4ec9b1a61559e2ab288a996e2cd76df0aeb4bd271953baa", 1),
    ("818dece52aa4361840d99525e3f439476a10d32bfa6a67db3f8c7479f89d69df", "5e0baee1743961e381496e8ce31239bd10879c425716c2b42222695732be8b7c", 1),
    ("08eec751391a48b59a32abdac8a5c2ff1aefd970395d444a94a6f003ea45626d", "42f760a7e66a1e0d55c8d148699ba01160d3545d26f5ff99b0bc5156ecbc9df3", 1),
    ("7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272", "1c08f1fc9c2153965983eb469ea58babe7740fc4e3e7f14d799a060a44649d28", 1),
    ("4e 40 c2 f1 ce 53 2c ac df 9 79 8d 52 4e e4 8b b9 e1 93 d3 98 a8 26 aa c3 a9 db 24 3c 44 2f 49", "ca 78 d9 92 82 ff 97 11 f1 f3 20 bb f5 40 db 3 a6 5b e3 f4 19 b4 f4 f3 6c 1a 8d d8 63 cf 48 36", 1),
    ("gemini-mt6797-a72-ready-plan-predicate-diagnostic.boot.img", "gemini-mt6797-a72-ready-plan-value-diagnostic.boot.img", 1),
    (".derived-build-a72-ready-plan-diagnostic.XXXXXXXX", ".derived-build-a72-ready-plan-value-inner.XXXXXXXX", 1),
    ("experiment=2026-08-30-mainline-a72-ready-plan-predicate-diagnostic", "experiment=2026-08-30-mainline-a72-ready-plan-value-diagnostic", 1),
    ("validation=ready-plan-predicate-diagnostic-package", "validation=ready-plan-value-diagnostic-package", 1),
    ('output_name="candidate-a72-ready-plan-predicate-diagnostic-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-ready-plan-value-diagnostic-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-ready-plan-predicate-diagnostic-build", "validation=a72-ready-plan-value-diagnostic-build", 1),
    ("unsafe predicate-diagnostic candidate derivation", "unsafe value-diagnostic candidate derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe value-diagnostic candidate derivation: expected {count}, found {actual}: {old}"
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
