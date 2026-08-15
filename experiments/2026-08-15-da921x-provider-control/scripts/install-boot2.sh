#!/usr/bin/env bash

# Source-pin and mechanically derive the guarded installer for the exact
# matched DA921x provider-only control. The inherited policy resolves live GPT
# boot2, records but does not back up the predecessor, verifies a full
# readback, and powers off after success.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=deaa0e886a881132dd49ee1e3d5b0e6f776400f51fa86a8d0b7c791e979d12a8

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("# Install the exact validated provenance-observer container to inactive boot2.",
     "# Install the exact validated DA921x provider-only control to inactive boot2.", 1),
    ("readonly CANDIDATE_SHA256=ea603c1b1a64d4f1aa9cac3e53957a3e858a7ce04127f1aef36d4b0e8173cb02",
     "readonly CANDIDATE_SHA256=3188d474f5d6989a0eb0782cdfac781efaf43dd42a0bd11481277050e735f8a2", 1),
    ("readonly ARTIFACT_MANIFEST_SHA256=ad92d496dfb4fd183c35e6e0f32ce626b2045528657fb2567d8561dd02540f1a",
     "readonly ARTIFACT_MANIFEST_SHA256=48025fc088c20d6b28eeabb27c118ce695625e29d6a232d92fe34050b4f28d19", 1),
    ("readonly ARTIFACT_NAME=gemian-runtime-provenance-observer-rndis-1d303dda10b4",
     "readonly ARTIFACT_NAME=candidate-da921x-provider-control-76d32c74", 1),
    ("provenance-observer-deployment-", "da921x-provider-control-deployment-", 3),
    (r"\.gemini-provenance-observer\.", r"\.gemini-da921x-provider-control\.", 2),
    ("/home/gemini/.gemini-provenance-observer.XXXXXXXX",
     "/home/gemini/.gemini-da921x-provider-control.XXXXXXXX", 1),
    ("experiment=2026-08-14-mt6797-runtime-provenance-observer",
     "experiment=2026-08-15-da921x-provider-control", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe installer derivation: expected {count} occurrences, found {actual}: {old}")
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
