#!/usr/bin/env bash

# Source-pin the guarded installer and retarget only the exact predecessor,
# P27 diagnostic candidate, artifact manifest, labels, and evidence.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=623aef4a6ed27034927434fb0404da5b588e40a76d435b234b953f331cc01d25
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-30-mainline-a72-ready-token-contract-repair/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-p27-attribution.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ('("7c96288818d6d3e0eb5547c675057bbe7789b0b62388b0a171681720da29f2a9", "a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", 1)',
     '("7c96288818d6d3e0eb5547c675057bbe7789b0b62388b0a171681720da29f2a9", "e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", 1)', 1),
    ('("2245c1c4056cfd849ff89ba8afa220bf0cf038f1ea23a324c1e717c6ea23d89b", "7c96288818d6d3e0eb5547c675057bbe7789b0b62388b0a171681720da29f2a9", 1)',
     '("2245c1c4056cfd849ff89ba8afa220bf0cf038f1ea23a324c1e717c6ea23d89b", "a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", 1)', 1),
    ("3109e145e478890797f67e07ac55d11f17769862c80978d797efb32305bc59c1", "d5b84687a4c30f1fbb772aa8d807973e0c64f32f6b51d631c2e43b72ffb6b4fe", 1),
    ("candidate-a72-ready-token-contract-repair-efe47cb1", "candidate-a72-p27-runtime-attribution-fbc299b0", 1),
    ('("a72-admission-trace", "a72-ready-token-contract-repair", 5)', '("a72-admission-trace", "a72-p27-runtime-attribution", 5)', 1),
    ("2026-08-30-mainline-a72-ready-token-contract-repair", "2026-08-30-mainline-a72-p27-runtime-attribution", 1),
    (".derived-install-a72-ready-contract.XXXXXXXX", ".derived-install-a72-p27-attribution-inner.XXXXXXXX", 1),
    ("unsafe READY-contract installer derivation", "unsafe P27 diagnostic installer derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P27 diagnostic installer derivation: expected {count}, found {actual}: {old}"
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
