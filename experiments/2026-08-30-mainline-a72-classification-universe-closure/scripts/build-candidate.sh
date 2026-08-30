#!/usr/bin/env bash

# Source-pin the repaired READY assembler and retarget only the closure
# package, provenance leaf, exact candidate identity, and labels.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0889c32fc1ac2831e47ffe040e4d205d369a8b6120143218e046f5ef28cc5e47
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-30-mainline-a72-ready-plan-expectation-repair/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-classification-closure.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("a07d9c453e2ceaa3666db124ed1ebb712d00d07c", "787ff75a7d9c624a7f25abf69b50a45cfd8ebcc7", 1),
    ("31e78157ff0522ef8e2269f16f49de4e66cf45034c56c20b817d70340d81eb9d", "5293d9be0ff42439faa1c1b27b18c37e3e47edf4a1c7cd367e34bce9fc2b9e75", 1),
    ("a7e1b036ed2aa225b1b1b7be46176cf4945a18cb6cdbe257b241d6002741552e", "22bd67b98c6bf0d2fbd6c8dd1d33d9d74b1a121ac0ee33d5564534cb3c404a8f", 1),
    ("6bd498c321726f21f3e39adf22ccd0c5c10b6f932bd64a6ae2fe13cbc6e867dc", "c10171ccea82cb163e7a58f49462a3b8ddfa06ca820a4ba68df79e342b75b254", 1),
    ("44666a9cbc566cd5757311c8a01f787240195ad62ac42a882f5c998cd92f4fc6", "64b3634a751b8b2c4816a2178189b3d85e9a1d1a38b78991acbf46e4046526a5", 1),
    ("51b160a3fe951224e4afd7cb442bcf663e49f09e3efdf129acc8631d6b1298a5", "49b2319cc19047136416e2602176a8777815cbc76e5308a785ab8c3ee40d78ef", 1),
    ("0732a2cf00e04a71034a563dcb35a8a3e3414620cdf8d511767a17f9b552fcba", "a30dce8d957a2f8d79a244d599f899de15ea696129096e576260e17a0ac9f352", 1),
    ("982c4b50d3bdbe9d1a0d0218ded5c2a4bcd4b39e859d79b3048c1eab14ce3e0b", "9caea8fe255214dd5d36b2d6a975e41b143b00d757cc54e7ccead9d1b5c62c6c", 1),
    ("9abdd1c66b8665ed7ccd0b9ca8e0cc7b74ddd40ebce65b2fb5d7a37aef6571cc", "2245c1c4056cfd849ff89ba8afa220bf0cf038f1ea23a324c1e717c6ea23d89b", 1),
    ("ab 16 41 2a fe 28 33 e0 58 bf a 14 3 52 a6 f9 4a 79 29 12 a7 a9 4c ae dd 39 8 e0 ee 92 7c e2", "6e 41 9e 90 42 96 5e 11 62 4b ab c5 17 e3 62 93 40 c4 79 8d b a5 2 5c c5 ac 39 54 8 b4 db 9c", 1),
    ("gemini-mt6797-a72-ready-plan-expectation-repair.boot.img", "gemini-mt6797-a72-classification-universe-closure.boot.img", 1),
    (".derived-build-a72-ready-plan-repair.XXXXXXXX", ".derived-build-a72-classification-closure-inner.XXXXXXXX", 1),
    ("experiment=2026-08-30-mainline-a72-ready-plan-expectation-repair", "experiment=2026-08-30-mainline-a72-classification-universe-closure", 1),
    ("validation=ready-plan-expectation-repair-package", "validation=classification-universe-closure-package", 1),
    ('output_name="candidate-a72-ready-plan-expectation-repair-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-classification-universe-closure-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-ready-plan-expectation-repair-build", "validation=a72-classification-universe-closure-build", 1),
    ("unsafe READY-repair candidate derivation", "unsafe classification-closure candidate derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe classification-closure candidate derivation: expected {count}, found {actual}: {old}"
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
