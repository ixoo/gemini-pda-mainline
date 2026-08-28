#!/usr/bin/env bash

# Source-pin the serviceable one-shot runner and bind it to the exact
# ATAG-prerequisite candidate, live boot ID, and private evidence name.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a5b8c3541de5a72ad286c4cec9ffa6f2a61383ca7681a282cc589ed159244ef3
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"; done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P); repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_runner="$repo_root/experiments/2026-08-28-mainline-a72-admission-serviceable-one-shot/scripts/run-one-shot.sh"
[[ -f "$source_runner" && ! -L "$source_runner" ]] || die 'source runner is missing or unsafe'
[[ "$(sha256sum "$source_runner" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source runner changed'
derived=$(mktemp "$script_dir/.derived-run-a72-admission-atag.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }; trap cleanup EXIT HUP INT TERM
python3 - "$source_runner" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("2f645942f7d8dd7e5e87eed72c9b5ce8e81567be87f7650a7f4eaf793f16e493", "581f896a6093636b18ed1e8c6ada8482904abffbb623a46b5873008056f745c1", 1),
    ("999d7a55f0fdb4992061588b17ebcd46ed945210dd1ba8006a286febfee94a9f", "d7a32a17362a92712a164d87f36c240c4af8e0261a90c43b41d3763131f93cc2", 2),
    ("3f4cb51ad1405df620f447b6210aac795a0664171711f8ca38ddaf05e9113531", "6b582a040b5406f63fbd45bff7017eb19bd0c06ee50a040abe03ac654abb353e", 2),
    ("974315e58463c0430a2cdafdbdd978418e1fed866d492231d8b2cb2a658d298a", "2118803eac96ba77c89b7de5da7e86a88b52e402fbaaff2441a91c8a4520e7ef", 2),
    ("f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02", "fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0", 1),
    ("2026-08-28-mainline-a72-admission-serviceable-one-shot", "2026-08-28-mainline-a72-admission-atag-one-shot", 1),
    ("a72-admission-serviceable-one-shot-attempt-1", "a72-admission-atag-one-shot-attempt-1", 1),
    ("9c462f2c-84a5-490a-a26d-ce863a5ab50a", "09ed19d3-6ad9-4e65-b2d3-46ad56bc9bb7", 1),
    (".derived-serviceable-one-shot.XXXXXXXX", ".derived-atag-one-shot-inner.XXXXXXXX", 1),
    ("die 'derived collector changed'", "die \"derived collector changed: $(sha256sum \"$derived\" | awk '{print $1}')\"", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe ATAG runner derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e; /bin/bash "$derived" "$@"; rc=$?; set -e
cleanup; trap - EXIT HUP INT TERM; exit "$rc"
