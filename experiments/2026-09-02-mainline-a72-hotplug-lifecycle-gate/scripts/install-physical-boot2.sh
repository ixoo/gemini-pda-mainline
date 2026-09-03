#!/usr/bin/env bash

# Source-pin the live-GPT installer for the exact physical hotplug candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=deaa0e886a881132dd49ee1e3d5b0e6f776400f51fa86a8d0b7c791e979d12a8
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-physical-hotplug.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("ea603c1b1a64d4f1aa9cac3e53957a3e858a7ce04127f1aef36d4b0e8173cb02",
     "9b60b576efe1e1c7496953c098748205a8ec2ca4eaa322d9d6466fa8285a2136", 1),
    ("ad92d496dfb4fd183c35e6e0f32ce626b2045528657fb2567d8561dd02540f1a",
     "b2f7acb8da7d96661ae560ccd41596c2839d79026a392128851bc3de3264f88a", 1),
    ("gemian-runtime-provenance-observer-rndis-1d303dda10b4",
     "candidate-a72-hotplug-physical-6e133cee", 1),
    ("2026-08-14-mt6797-runtime-provenance-observer",
     "2026-09-02-mainline-a72-hotplug-lifecycle-gate", 1),
    ("provenance-observer", "a72-physical-hotplug", 7),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe physical-hotplug installer derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
