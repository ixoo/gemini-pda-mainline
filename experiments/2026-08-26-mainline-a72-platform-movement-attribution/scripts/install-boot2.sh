#!/usr/bin/env bash

# Source-pin the passed live-GPT/TEE installer and retarget it to the exact
# movement-attribution candidate and retired failure-stage predecessor.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=48e60a645fca43ec811f8c5769d2629745c149389e044b634b0cffc3e748496b
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-25-mainline-a72-platform-provider-failure-stage-attribution/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-boot2-platform-movement.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb", "9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78", 1),
    ("1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2", "8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb", 1),
    ("1a73373660e3b07d8ee830f940ab7fb31e0f791406e877b6c9824f133ce363ea", "ace809cb0da37d977f36f9db5c0618b153103767a89cd796e1ed02d783831b48", 1),
    ("candidate-a72-platform-provider-clock-stage-8ca14ec2", "candidate-a72-platform-movement-fd070a56", 1),
    ("a72-platform-provider-clock-stage-deployment-", "a72-platform-movement-deployment-", 1),
    (r"\.gemini-a72-platform-provider-clock-stage\.", r"\.gemini-a72-platform-movement\.", 1),
    ("/home/gemini/.gemini-a72-platform-provider-clock-stage.XXXXXXXX", "/home/gemini/.gemini-a72-platform-movement.XXXXXXXX", 1),
    ("2026-08-25-mainline-a72-platform-provider-failure-stage-attribution", "2026-08-26-mainline-a72-platform-movement-attribution", 1),
    ("retired third-reader predecessor", "retired failure-stage predecessor", 1),
    (".derived-install-boot2-a72-platform-provider-clock-stage-generic.XXXXXXXX", ".derived-install-boot2-platform-movement-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe movement installer derivation: expected {count}, found {actual}: {old}"
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
