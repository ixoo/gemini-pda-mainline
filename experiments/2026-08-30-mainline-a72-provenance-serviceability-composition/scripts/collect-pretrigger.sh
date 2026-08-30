#!/usr/bin/env bash

# Source-pin the proven read-only READY collector and retarget it to the exact
# provenance/serviceability composition candidate. This script never sends the
# trigger token.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=2fbfc66c6f87200a9de7f068b07ce829399daa88f3802201bbb6197e1a9adde5
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-30-mainline-a72-ready-admission/scripts/collect-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'
derived=$(mktemp "$script_dir/.derived-collect-a72-provenance-pretrigger.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7", "f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", 1),
    ("08d3c9d2780c59dd871f710e735a96181027978cb1d502cf76c162297638d0c9", "5826658d983313d2ddb7b032dc80f8a7a3844076aaf346e36f852702e7cec010", 1),
    ("68cbb6af510c45ee69b320246ccee04e2a2c5f3ec88f7bde0d0daf7e374a97f9", "3a728b7fb16c9d9c58580311d5e80f29d17a92d8f69c849d5e5c33d81cb8477d", 1),
    ("b012426e2e3bc912da63655dc9e325b4d3113d8db73e41959b1746e2815aae80", "c617550e84260388144e702bb3361d44291ed62f0ef0bb425b80b08555705406", 1),
    ("a72-ready-admission-pretrigger-attempt-1", "a72-provenance-serviceability-pretrigger-attempt-1", 1),
    (".gemini-a72-ready-probe.XXXXXXXX", ".gemini-a72-provenance-probe.XXXXXXXX", 1),
    (".gemini-a72-ready-command.XXXXXXXX", ".gemini-a72-provenance-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe provenance pre-trigger collector derivation: expected {count}, found {actual}: {old}"
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
