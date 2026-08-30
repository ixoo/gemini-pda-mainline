#!/usr/bin/env bash

# Source-pin the guarded installer and retarget only the exact predecessor,
# repaired READY-token candidate, artifact manifest, labels, and evidence.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=3aca1ae2071507aefcdc7ab0dc1ebf0ba93615b343368313f4f9e69a42388b08
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-30-mainline-a72-live-a34-predicate-repair/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-ready-contract.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("7c96288818d6d3e0eb5547c675057bbe7789b0b62388b0a171681720da29f2a9", "a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", 1),
    ("2245c1c4056cfd849ff89ba8afa220bf0cf038f1ea23a324c1e717c6ea23d89b", "7c96288818d6d3e0eb5547c675057bbe7789b0b62388b0a171681720da29f2a9", 1),
    ("0085efd39fd5c62ad56dfe18108ba7e4f70221a1e6a26d785f66b2cf7fb3680d", "3109e145e478890797f67e07ac55d11f17769862c80978d797efb32305bc59c1", 1),
    ("candidate-a72-live-a34-predicate-repair-8fb8194b", "candidate-a72-ready-token-contract-repair-efe47cb1", 1),
    ('("a72-admission-trace", "a72-live-a34-predicate-repair", 5)', '("a72-admission-trace", "a72-ready-token-contract-repair", 5)', 1),
    ("2026-08-30-mainline-a72-live-a34-predicate-repair", "2026-08-30-mainline-a72-ready-token-contract-repair", 1),
    (".derived-install-a72-live-a34-repair.XXXXXXXX", ".derived-install-a72-ready-contract-inner.XXXXXXXX", 1),
    ("unsafe live-A34-repair installer derivation", "unsafe READY-contract installer derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe READY-contract installer derivation: expected {count}, found {actual}: {old}"
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
