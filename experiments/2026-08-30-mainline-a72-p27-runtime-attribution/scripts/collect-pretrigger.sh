#!/usr/bin/env bash

# Source-pin the bounded read-only collector and retarget only the exact P27
# candidate, materialized probe, validator, and private capture identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=28ab51b834d645497ef1a6f22dd301625f20411583eb1d549851d5f54802c200
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-30-mainline-a72-ready-token-contract-repair/scripts/collect-pretrigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-p27-attribution.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", "e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", 1),
    ("bbb041f98bad1fa071a2aebf1c22ebaa462d5f3e45bb8472c59afd6fc1e7d83d", "c7530fde97bc834bb6d8ae3e1a47ebbcffc21b1c78dbb9103c13bb9ef1198702", 1),
    ("ea8d422fca8cdfc8af5c5c3fc57f9d1988ccaaa700e1f4cceac0489f37053234", "d638ec37f77bcce968cf4a83a68ff7da6efbfaa0525487a13d9906560603abd9", 1),
    ("8feeb6e8c562278c0e76c284a757c8849dcc0d1e5eff705fee3434229c82eb52", "4513c845db329390eb778c07b866e723b3fba1638033536fcf5333958caef7a2", 1),
    ("a72-ready-token-contract-repair", "a72-p27-runtime-attribution", 2),
    ("ready-contract", "p27-attribution", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P27 collector derivation: expected {count}, found {actual}: {old}"
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
