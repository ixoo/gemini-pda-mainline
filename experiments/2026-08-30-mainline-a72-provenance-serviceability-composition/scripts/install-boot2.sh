#!/usr/bin/env bash

# Source-pin the proven guarded installer and retarget only the exact current
# predecessor, composed candidate, artifact manifest, and experiment identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=e1bbc80078d7d87e4f1cb76d26e67742a05656e71c25270029ba90beef120f96
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-30-mainline-a72-ready-admission/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-provenance-serviceability.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7",
     "f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", 1),
    ("0814c06b9bb41aa7ec666ad1abbb4bbf86e113e11878ac3de159d6cec3112f78",
     "8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7", 1),
    ("37ff44d6496d1ce8d4fc0cecb23d62c95a2a980e8c6c83a414399d260950045f",
     "388c099eaab6c4660db869fedf61e7e4b49c97de88b754c0dd407d4a88606f44", 1),
    ("candidate-a72-ready-admission-4c8cf8e0",
     "a72-provenance-serviceability-final/candidate-a72-provenance-serviceability-1921c30e", 1),
    ('("a72-admission-trace", "a72-ready-admission", 5)',
     '("a72-admission-trace", "a72-provenance-serviceability", 5)', 1),
    ("2026-08-30-mainline-a72-ready-admission",
     "2026-08-30-mainline-a72-provenance-serviceability-composition", 1),
    (".derived-install-a72-ready-admission-inner.XXXXXXXX",
     ".derived-install-a72-provenance-serviceability-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe composed-candidate installer derivation: expected {count}, found {actual}: {old}")
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
