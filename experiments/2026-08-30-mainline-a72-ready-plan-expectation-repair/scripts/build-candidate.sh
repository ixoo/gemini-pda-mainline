#!/usr/bin/env bash

# Source-pin the value-observer assembler and retarget only the repaired
# package, provenance leaf, exact candidate identity, and labels.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=1defcca962720f9449ac20b3bd6c0d8dfa7b97f3448cb93a52128d398be60968
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-30-mainline-a72-ready-plan-value-diagnostic/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-ready-plan-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("e33dfbce2a5f0050403e827ff4b105790069848b", "a07d9c453e2ceaa3666db124ed1ebb712d00d07c", 1),
    ("0b65b23388a03c4114e76f935013dfdcda21f764eb1000829bcbc38b9c1a64b8", "31e78157ff0522ef8e2269f16f49de4e66cf45034c56c20b817d70340d81eb9d", 1),
    ("2c82e22419db7571b4dccef8d633fe2dfb65786d682b47a0a8195ce2597e50ed", "a7e1b036ed2aa225b1b1b7be46176cf4945a18cb6cdbe257b241d6002741552e", 1),
    ("1c0a04c7ccf95603c072694c5d58f2c85bb45a5d4ac60a48eddb29797ca657e2", "6bd498c321726f21f3e39adf22ccd0c5c10b6f932bd64a6ae2fe13cbc6e867dc", 1),
    ("10848fb119857b1906ba820507205a77dcb11e0f9e2aecf674274445bc351ee8", "44666a9cbc566cd5757311c8a01f787240195ad62ac42a882f5c998cd92f4fc6", 1),
    ("a24875b0d8377a34c4ec9b1a61559e2ab288a996e2cd76df0aeb4bd271953baa", "51b160a3fe951224e4afd7cb442bcf663e49f09e3efdf129acc8631d6b1298a5", 1),
    ("5e0baee1743961e381496e8ce31239bd10879c425716c2b42222695732be8b7c", "0732a2cf00e04a71034a563dcb35a8a3e3414620cdf8d511767a17f9b552fcba", 1),
    ("42f760a7e66a1e0d55c8d148699ba01160d3545d26f5ff99b0bc5156ecbc9df3", "982c4b50d3bdbe9d1a0d0218ded5c2a4bcd4b39e859d79b3048c1eab14ce3e0b", 1),
    ("1c08f1fc9c2153965983eb469ea58babe7740fc4e3e7f14d799a060a44649d28", "9abdd1c66b8665ed7ccd0b9ca8e0cc7b74ddd40ebce65b2fb5d7a37aef6571cc", 1),
    ("ca 78 d9 92 82 ff 97 11 f1 f3 20 bb f5 40 db 3 a6 5b e3 f4 19 b4 f4 f3 6c 1a 8d d8 63 cf 48 36", "ab 16 41 2a fe 28 33 e0 58 bf a 14 3 52 a6 f9 4a 79 29 12 a7 a9 4c ae dd 39 8 e0 ee 92 7c e2", 1),
    ("gemini-mt6797-a72-ready-plan-value-diagnostic.boot.img", "gemini-mt6797-a72-ready-plan-expectation-repair.boot.img", 1),
    (".derived-build-a72-ready-plan-value.XXXXXXXX", ".derived-build-a72-ready-plan-repair-inner.XXXXXXXX", 1),
    ("experiment=2026-08-30-mainline-a72-ready-plan-value-diagnostic", "experiment=2026-08-30-mainline-a72-ready-plan-expectation-repair", 1),
    ("validation=ready-plan-value-diagnostic-package", "validation=ready-plan-expectation-repair-package", 1),
    ('output_name="candidate-a72-ready-plan-value-diagnostic-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-ready-plan-expectation-repair-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-ready-plan-value-diagnostic-build", "validation=a72-ready-plan-expectation-repair-build", 1),
    ("unsafe value-diagnostic candidate derivation", "unsafe READY-repair candidate derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe READY-repair candidate derivation: expected {count}, found {actual}: {old}"
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
