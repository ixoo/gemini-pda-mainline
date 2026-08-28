#!/usr/bin/env bash

# Source-pin the latest guarded installer and retarget exact identities only.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=91d70b9e8c949ea126a22d3e5bcd1f5744338477ff78e620bd99bd10f486efac
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"; done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P); repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-28-mainline-a72-live-image-runtime-dt-control/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-admission-serviceable.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }; trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab", "f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02", 1),
    ("a029c258c19c96a234cb5cafe4c1bb35a36bac2beadbe8e2ea547da8870719d1", "c23cab60a1c9e8cf5715410c2af90828bd01d19f63a75dc9e313726ceb0f92d8", 1),
    (r'("fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0",\n     "4e0f86885a16df2f8b0c1efb4dd2e67394938bad1ef720adabf70ff4635ec0ef", 1)',
     r'("fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0",\n     "c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab", 1)', 1),
    ("candidate-a72-live-image-runtime-dt-control-35d0c6ef", "candidate-a72-admission-serviceable-b1ff92e8", 1),
    ('("a72-admission-trace", "a72-live-image-runtime-dt-control", 5)', '("a72-admission-trace", "a72-admission-serviceable", 5)', 1),
    ("2026-08-28-mainline-a72-live-image-runtime-dt-control", "2026-08-28-mainline-a72-admission-serviceability-restoration", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe serviceable installer derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e; /bin/bash "$derived" "$@"; rc=$?; set -e
cleanup; trap - EXIT HUP INT TERM; exit "$rc"
