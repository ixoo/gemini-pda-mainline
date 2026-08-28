#!/usr/bin/env bash

# Source-pin the one-shot USB/netcat collector and retarget its exact candidate,
# helpers, and evidence identity. The derived collector never retries a trigger.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=69e3290661820a4555a3b43c2451d63e6bf05f81013bae864704cfa0a458580e
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-28-mainline-a72-admission-live-trigger/scripts/collect-live-trigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-admission-softtrace.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("4e0f86885a16df2f8b0c1efb4dd2e67394938bad1ef720adabf70ff4635ec0ef",
     "83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0", 1),
    ("008a8e33cd67654dc4d3632277b6d1600ef9b565ef7e5b763bb481c424229b60",
     "f2b9dc49d4ba68af080e7119776f0ea758e6d9dbc9082bc661b5a37dc52b53d8", 1),
    ("93e6ee4b0dd84d6415a84a8bac400308b7fa7483aabab0b414b33016d1ae690b",
     "79bc42ca393f5726648be93b7a4e1d2378fd0b9c306007209d1901cf49824468", 1),
    ("906a404932f64ec3795f666b9adda0167f49777f24c52178c20ca0aaea953715",
     "9188f8b96bdfeedc1921df5043eeb6e0120b2383b9a8fa454c50b5ef1ed64f0a", 1),
    ("274b950c8c0dbd2ca3eb6fa7933fe692251de70bf7aadf735bc98d5c12d2886e",
     "033a80bd39a494d0b1d3d6f0773ca278112f2e98cffbd3d2fcdceab6db3b653f", 1),
    ("2026-08-28-mainline-a72-admission-live-trigger",
     "2026-08-28-mainline-a72-admission-trace-softfail", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe trace-softfail collector derivation: expected {count}, "
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
