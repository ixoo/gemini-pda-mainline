#!/usr/bin/env bash

# Source-pin and mechanically derive the guarded installer for the exact GAEL
# kernel plus disabled-SCP-node LK handoff candidate. The inherited policy
# resolves live GPT boot2, records but does not back up the predecessor,
# verifies a full readback, and powers off after success.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=9145d506a309cb13cde1d37c39a55f13e3a624940824c3c8eec4e36d947ece8b

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-16-mainline-current-dtb-usb-observation/scripts/install-boot2.sh"
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
    ("current-DT USB-observation candidate",
     "disabled-SCP-node LK handoff candidate", 2),
    ("fa107a988d860f017905c61a4b52110bc8dc3cc1ce5f407424fa3dd47c9b8b87",
     "73be76fd4eb26d6d1d718bb4c0a77653839ca40e00267a5a35defb5b8a45b0f7", 1),
    ("bfdfe4596ee015adbcb8d1c6c718cffdfec31a75e4e522575a7bda6be7882291",
     "2bc9c53da18bb0e0276d7d86eb617d8e96a6259f01a556ed47d1883ee72f657a", 1),
    ("candidate-current-dtb-usb-observation-a9d4f951",
     "candidate-mainline-scp-handoff-node-d13f110a", 1),
    ("current-dtb-usb-observation-deployment-",
     "mainline-scp-handoff-node-deployment-", 1),
    (r"\.gemini-current-dtb-usb-observation\.",
     r"\.gemini-mainline-scp-handoff-node\.", 1),
    ("/home/gemini/.gemini-current-dtb-usb-observation.XXXXXXXX",
     "/home/gemini/.gemini-mainline-scp-handoff-node.XXXXXXXX", 1),
    ("experiment=2026-08-16-mainline-current-dtb-usb-observation",
     "experiment=2026-08-16-mainline-scp-handoff-node", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe installer derivation: expected {count} occurrences, found {actual}: {old}"
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
