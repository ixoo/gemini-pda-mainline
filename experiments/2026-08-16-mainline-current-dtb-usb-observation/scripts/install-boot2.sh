#!/usr/bin/env bash

# Source-pin and mechanically derive the guarded installer for the exact GAEL
# kernel plus current-DT USB-observation candidate. The inherited policy
# resolves live GPT boot2, records but does not back up the predecessor,
# verifies a full readback, and powers off after success.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a228166ee732ea17ba8e1dcb99471f672bdfbf8dfe14ecce94057ed379bab684

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-16-mainline-lk-handoff-dtb-control/scripts/install-boot2.sh"
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
    ("# GAEL kernel plus runtime-proven Stage-27 DTB control candidate.",
     "# GAEL kernel plus current-DT USB-observation candidate.", 2),
    ("68515e0ecbb073b4ee18b318bd869fd5b7dea1c3ac838681ceb42b7451dc1c67",
     "fa107a988d860f017905c61a4b52110bc8dc3cc1ce5f407424fa3dd47c9b8b87", 1),
    ("c7ac138cc3bcc500c531ab8fa507b5c0771e0a8c3e9bb463758fef52483459cf",
     "bfdfe4596ee015adbcb8d1c6c718cffdfec31a75e4e522575a7bda6be7882291", 1),
    ("candidate-lk-handoff-dtb-control-e96d0cc2",
     "candidate-current-dtb-usb-observation-a9d4f951", 1),
    ("lk-handoff-dtb-control-deployment-",
     "current-dtb-usb-observation-deployment-", 1),
    (r"\.gemini-lk-handoff-dtb-control\.",
     r"\.gemini-current-dtb-usb-observation\.", 1),
    ("/home/gemini/.gemini-lk-handoff-dtb-control.XXXXXXXX",
     "/home/gemini/.gemini-current-dtb-usb-observation.XXXXXXXX", 1),
    ("experiment=2026-08-16-mainline-lk-handoff-dtb-control",
     "experiment=2026-08-16-mainline-current-dtb-usb-observation", 1),
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
