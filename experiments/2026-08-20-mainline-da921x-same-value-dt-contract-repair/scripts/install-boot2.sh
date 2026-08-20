#!/usr/bin/env bash

# Source-pin the guarded installer for the DT-contract-repaired candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=78be6ee06d4b562bf91a6a6ced6ddf78d5ab601079050688fad6666087d62d3f
readonly SLOW_TRANSPORT_SHA256=1859f2658ce4b097f312ac1db5019f37a2420383b0db6702edc2a819c235a797

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
slow_transport="$script_dir/slow-transport-bin/ssh"
source_installer="$repo_root/experiments/2026-08-19-mainline-da921x-same-value-write-implementation/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is unsafe'
[[ -x "$slow_transport" && ! -L "$slow_transport" ]] || die 'slow transport wrapper is unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'
[[ "$(sha256sum "$slow_transport" | awk '{print $1}')" == "$SLOW_TRANSPORT_SHA256" ]] ||
	die 'slow transport wrapper identity changed'
transport_bin="$(dirname -- "$slow_transport")"
export PATH="$transport_bin:$PATH"

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
    ("same-value-write candidate", "same-value-write DT-contract-repaired candidate", 2),
    ("b81813d13acc970c7b9203b89ec034921ef6f7e1017539a0c228754619af7b22",
     "85dbd8d020cc6d3527743f05d4a1071a8f573407a5519ae1584127e55e33bae9", 1),
    ("e5e5ff3e0a1828e59381117d33ee539d2be19c7c234c5150fadea888e705b068",
     "7bb232821422675197197915f69f321cc3e3027e71a6b32c99706beedfb7aea0", 1),
    ("candidate-mainline-da921x-same-value-write-b84f3ba8",
     "candidate-mainline-da921x-same-value-dt-repair-87b38fc4", 1),
    ("mainline-da921x-same-value-write-deployment-",
     "mainline-da921x-same-value-dt-repair-deployment-", 1),
    ("gemini-mainline-da921x-same-value-write",
     "gemini-mainline-da921x-same-value-dt-repair", 1),
    ("2026-08-19-mainline-da921x-same-value-write-implementation",
     "2026-08-20-mainline-da921x-same-value-dt-contract-repair", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe installer derivation: expected {count}, found {actual}: {old}")
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
