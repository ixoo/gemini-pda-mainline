#!/usr/bin/env bash

# Source-pin the boot-bound one-shot executor and retarget only the exact P27
# candidate, local tooling identities, capture identity, and evidence labels.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=7708a624e7831d1e09d18dddaf1e9c3cd6865fb88dac670fb6e40d2fe51d3fca
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-30-mainline-a72-ready-token-contract-repair/scripts/execute-trigger.sh"
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-p27-attribution.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", "e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", 1),
    ("620c6273e59286f65e67084bb071ae60cd53b27e9634188492cc47611d6f37d2", "d8016c61216d16a64d35850eb6ec95a4dd011b1dae62afedd7345de2a41caa81", 1),
    ("3d5bfa25d84239232d765b4fba000ffa89246bf20ed636bca19e3afe92d1f9dd", "ee53bef775ae2b3c16a77de63e916dfda06fca22cd871a62f37cf065f1badb1f", 1),
    ("8feeb6e8c562278c0e76c284a757c8849dcc0d1e5eff705fee3434229c82eb52", "4513c845db329390eb778c07b866e723b3fba1638033536fcf5333958caef7a2", 1),
    ("2026-08-30-mainline-a72-ready-token-contract-repair", "2026-08-30-mainline-a72-p27-runtime-attribution", 2),
    ("a72-ready-token-contract-repair", "a72-p27-runtime-attribution", 1),
    ("ready-contract", "p27-attribution", 3),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P27 executor derivation: expected {count}, found {actual}: {old}"
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
