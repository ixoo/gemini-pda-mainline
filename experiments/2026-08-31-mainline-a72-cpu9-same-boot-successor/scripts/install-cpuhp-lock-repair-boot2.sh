#!/usr/bin/env bash

# Source-pin the guarded CPU9 installer to the exact CPUHP lock-repair
# candidate and require the retired raw-lane image on inactive boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=172ba9adfdf34f1cf5d48946bebd2b27575f9841d1f1d38ae7169c2091327e21
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/install-progress-raw-lane-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source progress raw-lane installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source progress raw-lane installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-cpu9-cpuhp-lock-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("1cf367e021351f8a26643d827866786a879a8d6a3e68d8143cfce40bd1db52f7",
     "0904c5a293fea22f6993cb25ab8d775ed539d57c8fac7a7a6c50b67e2916f293", 1),
    ("099757f497ee4e94ce5518c1d2c3974a2952df307bf82fb692f24cd949e5f422",
     "2769dba806def496822adc6b65ab6634dcc4be53e4394224b96534d6add05429", 1),
    ("candidate-a72-cpu9-progress-raw-lane-243ddc6e",
     "candidate-a72-cpu9-cpuhp-lock-56986d08", 1),
    ("cpu9-progress-raw-lane-repair",
     "cpu9-cpuhp-lock-repair", 1),
    ("CPU9 progress raw-lane repair",
     "CPU9 CPUHP lock repair", 1),
    ('new_predecessor = "4bf74874cbfe900576ae891d32b5e8996d5c66ed599b6fca09c7310e87cdeae8"',
     'new_predecessor = "1cf367e021351f8a26643d827866786a879a8d6a3e68d8143cfce40bd1db52f7"', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPUHP lock-repair installer derivation: expected "
            f"{count}, found {actual}: {old}"
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
