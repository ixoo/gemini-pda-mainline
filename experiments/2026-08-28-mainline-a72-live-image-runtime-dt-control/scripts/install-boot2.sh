#!/usr/bin/env bash

# Source-pin the latest guarded installer and retarget it to this exact control.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=324cde7e6ba931412fec6536709d6435eef8468eeb65434e779b6f2d7eeb497d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"; done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-28-mainline-a72-admission-live-trigger/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-live-image-runtime-dt.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ('("60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1",\n     "4e0f86885a16df2f8b0c1efb4dd2e67394938bad1ef720adabf70ff4635ec0ef", 2)',
     '("60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1",\n     "c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab", 2)', 1),
    ('("7cbaf0980b37f6efb49e3fe0e373be68afb7f2e7011e4bc6e5bd7fee141c1f1d",\n     "7a4c5eae292f2cd1766d2773e2d1b9d1fd660a120d9d5cdff9bad73ecbb97091", 2)',
     '("7cbaf0980b37f6efb49e3fe0e373be68afb7f2e7011e4bc6e5bd7fee141c1f1d",\n     "a029c258c19c96a234cb5cafe4c1bb35a36bac2beadbe8e2ea547da8870719d1", 2)', 1),
    ('("fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0",\n     "60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1", 1)',
     '("fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0",\n     "4e0f86885a16df2f8b0c1efb4dd2e67394938bad1ef720adabf70ff4635ec0ef", 1)', 1),
    ("candidate-a72-admission-live-633f897a", "candidate-a72-live-image-runtime-dt-control-35d0c6ef", 1),
    ('("a72-admission-trace", "a72-admission-live", 5)',
     '("a72-admission-trace", "a72-live-image-runtime-dt-control", 5)', 1),
    ("2026-08-28-mainline-a72-admission-live-trigger", "2026-08-28-mainline-a72-live-image-runtime-dt-control", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe control installer derivation: expected {count}, found {actual}: {old}")
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
