#!/usr/bin/env bash

# Source-pin the bounded changed-ID recovery collector and retarget only the
# exact provider-ready candidate and classifier identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=35b56fad447ad4548993e24b1727f34e15244da855179cf4127c46167a5e5134
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-25-mainline-a72-platform-provider-snapshot-second-read/scripts/collect-recovery.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source recovery collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source recovery collector changed'

derived=$(mktemp "$script_dir/.derived-collect-recovery-provider-ready.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("CLASSIFIER_SHA256=489e848182924c91f6249717fbb4f05d8aa99f0a8c4a5b5e47d9c6eaa1d079b3", "CLASSIFIER_SHA256=76e464516df2f68b0ac4c79b687203d725932481b931a2cb2658721f3b79c101", 1),
    ("ff902d12b95893872990ebf813f24ca298ca76c4f86d4650f3b696cbdc00d79f", "f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e", 1),
    ("a72-platform-provider-snapshot-attempt-1-recovery", "a72-platform-provider-ready-attempt-1-recovery", 1),
    (".a72-platform-provider-recovery.XXXXXXXX", ".a72-platform-provider-ready-recovery.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe provider-ready recovery collector derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
