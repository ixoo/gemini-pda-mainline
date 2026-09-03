#!/usr/bin/env bash

# Source-pin the guarded live-GPT installer for the topology-repeat candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=523197127f2e7bc84005576b4d3e3b25046e8a71bdb562075a595eb85f6ee29b
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/scripts/install-stage-binding-fix-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source stage-binding-fix installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-topology-repeat.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("c84aea47c6dc4a9745687536b3a99c4e434af5826b10a5a83bae3f8171a81271",
     "6ba8c9538dcff6559066088da943d96aaa8ad32d10a93b34c8bbeddc97464f75", 1),
    ("0a4434843507ef43c7c2e0b16ca2b453e758d32d8fd198c2c757ee1af128f820",
     "650581d9884741659ab69370b41cff1d61cc8cae799cad589dd6a885f47bd722", 1),
    ("candidate-a72-stage-binding-fix-09c4f0b7",
     "candidate-a72-topology-repeat-e02bfd85", 1),
    ("a72-stage-binding-fix", "a72-topology-repeat", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe topology-repeat installer derivation: expected {count}, "
            f"found {actual}: {old}"
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
