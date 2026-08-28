#!/usr/bin/env bash

# Source-pin the guarded live-trigger installer and retarget only its exact
# candidate, predecessor, evidence names, and experiment identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=324cde7e6ba931412fec6536709d6435eef8468eeb65434e779b6f2d7eeb497d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-28-mainline-a72-admission-live-trigger/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-admission-softtrace.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ('("60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1",\n'
     '     "4e0f86885a16df2f8b0c1efb4dd2e67394938bad1ef720adabf70ff4635ec0ef", 2)',
     '("60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1",\n'
     '     "83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0", 2)', 1),
    ('("7cbaf0980b37f6efb49e3fe0e373be68afb7f2e7011e4bc6e5bd7fee141c1f1d",\n'
     '     "7a4c5eae292f2cd1766d2773e2d1b9d1fd660a120d9d5cdff9bad73ecbb97091", 2)',
     '("7cbaf0980b37f6efb49e3fe0e373be68afb7f2e7011e4bc6e5bd7fee141c1f1d",\n'
     '     "dec15778248b91bd4a2159ae677fad7d9c0ce5ef7c5ca77aa2915ef7985b13fd", 2)', 1),
    ('("fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0",\n'
     '     "60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1", 1)',
     '("fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0",\n'
     '     "fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0", 1)', 1),
    ('("candidate-a72-admission-trace-ed6fc529",\n'
     '     "candidate-a72-admission-live-633f897a", 2)',
     '("candidate-a72-admission-trace-ed6fc529",\n'
     '     "candidate-a72-admission-softtrace-9d1912aa", 2)', 1),
    ('("a72-admission-trace", "a72-admission-live", 5)',
     '("a72-admission-trace", "a72-admission-softtrace", 5)', 1),
    ('("2026-08-28-mainline-a72-admission-durable-candidate",\n'
     '     "2026-08-28-mainline-a72-admission-live-trigger", 1)',
     '("2026-08-28-mainline-a72-admission-durable-candidate",\n'
     '     "2026-08-28-mainline-a72-admission-trace-softfail", 1)', 1),
    (".derived-install-boot2-a72-admission-live.XXXXXXXX",
     ".derived-install-boot2-a72-admission-softtrace-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe trace-softfail installer derivation: expected {count}, "
            f"found {actual}: {old}"
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
