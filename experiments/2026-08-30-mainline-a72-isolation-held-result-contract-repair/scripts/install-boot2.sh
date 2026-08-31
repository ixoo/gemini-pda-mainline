#!/usr/bin/env bash

# Source-pin the guarded P27-repair installer and retarget only the exact
# isolation-result successor, predecessor, artifact manifest, and evidence.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=4e7513b3cb2643b101ec5de2629fe569b275051fe6a5954625c64c4dedad4961
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-30-mainline-a72-p27-held-result-contract-repair/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-isolation-held-result-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        '("e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", "fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5", 1),',
        '("e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", "510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726", 1),',
        1,
    ),
    ("b3cbb2817acdc4ed3be4c5ba465a41acbbb6f5f76b6cc20d6752c8e7b6869e19", "4d1607238546ef4d01e8f15ee0d787108b24b220edc181f21f9fcb68cd92f64d", 1),
    (
        '("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", "e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", 1),',
        '("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", "fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5", 1),',
        1,
    ),
    ("candidate-a72-p27-held-result-contract-repair-df243481", "candidate-a72-isolation-held-result-contract-repair-53b52ffc", 1),
    ("experiment=2026-08-30-mainline-a72-p27-held-result-contract-repair", "experiment=2026-08-30-mainline-a72-isolation-held-result-contract-repair", 1),
    ("a72-p27-held-result-contract-repair", "a72-isolation-held-result-contract-repair", 1),
    (".derived-install-a72-p27-held-result-repair-inner.XXXXXXXX", ".derived-install-a72-isolation-held-result-repair-inner.XXXXXXXX", 1),
    ("P27 held-result repair candidate", "isolation held-result repair candidate", 1),
    ("P27 held-result repair installer derivation", "isolation held-result repair installer derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe isolation held-result repair installer derivation: expected "
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
