#!/usr/bin/env bash

# Source-pin the proven ATAG-prerequisite installer and retarget only its exact
# candidate, predecessor, evidence names, and experiment identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=16621a20ce5d12d3b7ada40ea8bbce71c60719fc28105b037d2e3acfc0db8f2a
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"; done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P); repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-28-mainline-a72-admission-atag-prerequisite/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-ready-admission.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }; trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0", "8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7", 1),
    (r'("fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0",\n     "f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02", 1)',
     r'("fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0",\n     "0814c06b9bb41aa7ec666ad1abbb4bbf86e113e11878ac3de159d6cec3112f78", 1)', 1),
    ("80f9be2b58437b6edfcb630bb78fe218e7a70b70dd32d3e8b819f7c3767327b3", "37ff44d6496d1ce8d4fc0cecb23d62c95a2a980e8c6c83a414399d260950045f", 1),
    ("candidate-a72-admission-atag-6971ee82", "candidate-a72-ready-admission-4c8cf8e0", 1),
    ('("a72-admission-trace", "a72-admission-atag-prerequisite", 5)', '("a72-admission-trace", "a72-ready-admission", 5)', 1),
    ("2026-08-28-mainline-a72-admission-atag-prerequisite", "2026-08-30-mainline-a72-ready-admission", 1),
    (".derived-install-a72-admission-atag-inner.XXXXXXXX", ".derived-install-a72-ready-admission-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe READY installer derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e; /bin/bash "$derived" "$@"; rc=$?; set -e
cleanup; trap - EXIT HUP INT TERM; exit "$rc"
