#!/usr/bin/env bash

# Source-pin the proven serviceable-candidate installer and retarget only its
# candidate, predecessor, evidence names, and experiment identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=2744665428e1ccdcff4741e3090524df9184bb974a754a0aca49c484f2158e05
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"; done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P); repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-28-mainline-a72-admission-serviceability-restoration/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-admission-atag.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }; trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02", "fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0", 1),
    (r'("fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0",\n     "c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab", 1)',
     r'("fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0",\n     "f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02", 1)', 1),
    ("c23cab60a1c9e8cf5715410c2af90828bd01d19f63a75dc9e313726ceb0f92d8", "80f9be2b58437b6edfcb630bb78fe218e7a70b70dd32d3e8b819f7c3767327b3", 1),
    ("candidate-a72-admission-serviceable-b1ff92e8", "candidate-a72-admission-atag-6971ee82", 1),
    ('("a72-admission-trace", "a72-admission-serviceable", 5)', '("a72-admission-trace", "a72-admission-atag-prerequisite", 5)', 1),
    ("2026-08-28-mainline-a72-admission-serviceability-restoration", "2026-08-28-mainline-a72-admission-atag-prerequisite", 1),
    (".derived-install-a72-admission-serviceable.XXXXXXXX", ".derived-install-a72-admission-atag-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe ATAG installer derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e; /bin/bash "$derived" "$@"; rc=$?; set -e
cleanup; trap - EXIT HUP INT TERM; exit "$rc"
