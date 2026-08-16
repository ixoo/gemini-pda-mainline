#!/usr/bin/env bash

# Source-pin and mechanically derive the guarded installer for the exact
# module-policy serviceability control. The inherited policy resolves live GPT
# boot2, records but does not back up the predecessor, verifies a full
# readback, and powers off after success.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=31f0ef58410d6ce55a2569079e5ea40908b8a0a46ce0ac2d3dbb848ff456108d

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-15-da921x-provider-control/scripts/install-boot2.sh"
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
    ("# Source-pin and mechanically derive the guarded installer for the exact\n# matched DA921x provider-only control.",
     "# Source-pin and mechanically derive the guarded installer for the exact\n# module-policy serviceability control.", 1),
    ("readonly CANDIDATE_SHA256=3188d474f5d6989a0eb0782cdfac781efaf43dd42a0bd11481277050e735f8a2",
     "readonly CANDIDATE_SHA256=044461e57d207f5ddd6e68cc463ea3ee1dd65260c27afe5fd00730137d13a2ff", 1),
    ("readonly ARTIFACT_MANIFEST_SHA256=48025fc088c20d6b28eeabb27c118ce695625e29d6a232d92fe34050b4f28d19",
     "readonly ARTIFACT_MANIFEST_SHA256=1c2e591e3b9c130febb491ef5d243ea9d6b1b7d6b60b5830ab67e32e332a155b", 1),
    ("readonly ARTIFACT_NAME=candidate-da921x-provider-control-76d32c74",
     "readonly ARTIFACT_NAME=candidate-da921x-module-policy-control-782850c4", 1),
    ("da921x-provider-control-deployment-", "module-policy-control-deployment-", 1),
    (r"\.gemini-da921x-provider-control\.", r"\.gemini-module-policy-control\.", 1),
    ("/home/gemini/.gemini-da921x-provider-control.XXXXXXXX",
     "/home/gemini/.gemini-module-policy-control.XXXXXXXX", 1),
    ("experiment=2026-08-15-da921x-provider-control",
     "experiment=2026-08-15-mainline-module-policy-control", 1),
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
