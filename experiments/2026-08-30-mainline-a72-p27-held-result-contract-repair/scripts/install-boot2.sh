#!/usr/bin/env bash

# Source-pin the guarded P27 installer and retarget only the exact successor
# candidate, predecessor, artifact manifest, labels, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=7a178fe9e29ad711d4a4b2f60dd203679c2d4f4c98ff7a71e24ba8a4bb6aeac8
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-30-mainline-a72-p27-runtime-attribution/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-p27-held-result-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", "fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5", 1),
    ("d5b84687a4c30f1fbb772aa8d807973e0c64f32f6b51d631c2e43b72ffb6b4fe", "b3cbb2817acdc4ed3be4c5ba465a41acbbb6f5f76b6cc20d6752c8e7b6869e19", 1),
    ("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", "e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", 1),
    ("candidate-a72-p27-runtime-attribution-fbc299b0", "candidate-a72-p27-held-result-contract-repair-df243481", 1),
    ("experiment=2026-08-30-mainline-a72-p27-runtime-attribution", "experiment=2026-08-30-mainline-a72-p27-held-result-contract-repair", 1),
    ("a72-p27-runtime-attribution", "a72-p27-held-result-contract-repair", 1),
    (".derived-install-a72-p27-attribution.XXXXXXXX", ".derived-install-a72-p27-held-result-repair-inner.XXXXXXXX", 1),
    ("P27 diagnostic candidate", "P27 held-result repair candidate", 1),
    ("P27 diagnostic installer derivation", "P27 held-result repair installer derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P27 held-result repair installer derivation: expected "
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
