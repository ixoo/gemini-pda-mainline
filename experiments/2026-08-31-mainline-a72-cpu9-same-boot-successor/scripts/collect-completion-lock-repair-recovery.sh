#!/usr/bin/env bash

# Recover and classify the exact patch-0481 retained lanes after changed-ID Gemian.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=b9f3b87c8b0a004d85aa352863be6f622dbccbbecf85273eeed4a468029a4b34
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_collector="$script_dir/collect-membership-lock-repair-recovery.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || \
	die 'source membership-lock recovery collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source membership-lock recovery collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-cpu9-completion-lock-recovery.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c",
     "370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e", 1),
    ("a72-cpu9-membership-lock-repair-deployment-1",
     "a72-cpu9-completion-lock-repair-deployment-1", 1),
    ("a72-cpu9-membership-lock-repair-recovery-attempt-1",
     "a72-cpu9-completion-lock-repair-recovery-attempt-1", 1),
    ("64e17462c68829e993b6437a3a96c26f9ea57adc27e47a56fd8afc130939d02f",
     "705622b90611bab0fdd0e6b5e0a3399ac65ee8db5da6243c5f26d369100e8279", 1),
    ("classify-membership-lock-repair-recovery.py",
     "classify-completion-lock-repair-recovery.py", 1),
    ("experiment=2026-08-31-mainline-a72-cpu9-membership-lock-repair",
     "experiment=2026-08-31-mainline-a72-cpu9-completion-lock-repair", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe completion-lock recovery-collector derivation: "
            f"expected {count}, found {actual}: {old}"
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
