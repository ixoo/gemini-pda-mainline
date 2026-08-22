#!/usr/bin/env bash

# Source-pin the guarded manual-checkpoint installer and specialize its exact
# live-GPT boot2 write/readback/shutdown workflow for the stage candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=55aa4aaab9ac18c444625c44a65fdd3fab47bdb9b15ee46e25e77c52b5091a68

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-21-mainline-manual-checkpoint-control/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2-manual-stage.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c",
     "43e7f44eeef694ef876f7686ae03e2a779a118141e7f9efa060ccc1182c8eac3", 1),
    ("14b92d7864899601f9d7bd889ecf837483ffc58ced5d880b03eee727d81a4107",
     "4af6a32d400a74299743ac921818f125fa1152fec867ab203abd3c4eff736c4a", 1),
    ("candidate-manual-checkpoint-control-4338ac1e",
     "candidate-manual-checkpoint-stage-control-07d2f185", 1),
    ("manual-checkpoint-control-deployment-", "manual-checkpoint-stage-control-deployment-", 1),
    (r"\.gemini-manual-checkpoint-control\.", r"\.gemini-manual-checkpoint-stage-control\.", 1),
    ("/home/gemini/.gemini-manual-checkpoint-control.XXXXXXXX",
     "/home/gemini/.gemini-manual-checkpoint-stage-control.XXXXXXXX", 1),
    ("experiment=2026-08-21-mainline-manual-checkpoint-control",
     "experiment=2026-08-21-mainline-manual-checkpoint-stage-control", 1),
    (".derived-install-boot2-manual-checkpoint-inner.XXXXXXXX",
     ".derived-install-boot2-manual-stage-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage installer derivation: expected {count}, found {actual}: {old}"
        )
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
