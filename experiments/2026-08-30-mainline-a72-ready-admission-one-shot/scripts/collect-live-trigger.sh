#!/usr/bin/env bash

# Source-pin the trace-aware one-shot collector and retarget only the exact
# READY candidate, boot-bound helpers, and experiment identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a49713d80cf263663cb61e324fc685bb4e8ed1c4024f1d7a2c87200d05eca826
readonly PRETRIGGER_SHA256=b0537c7b5df1005d4c3946eb559e90e986c05e56dd1581fb1a60e9909aa33f0b
readonly TRIGGER_SHA256=79bc42ca393f5726648be93b7a4e1d2378fd0b9c306007209d1901cf49824468
readonly VALIDATOR_SHA256=2146400b929218bdc7d91b609fa2ea166922be78ee81802918f68c0af7c89dd9
readonly CLASSIFIER_SHA256=6bc47b78562d9ff9ce8ad1527ac6a2f0f143944fd7fb497dff547fbb290b50bf
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod install mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-28-mainline-a72-admission-trace-softfail/scripts/collect-live-trigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'
while read -r path expected; do
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || die "support source changed: $path"
done <<EOF
$script_dir/remote-pretrigger.sh $PRETRIGGER_SHA256
$script_dir/remote-trigger.sh $TRIGGER_SHA256
$script_dir/validate-pretrigger.py $VALIDATOR_SHA256
$script_dir/classify-attempt.py $CLASSIFIER_SHA256
EOF

derived=$(mktemp "$script_dir/.derived-collect-a72-ready-one-shot.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0",
     "8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7", 1),
    ("f2b9dc49d4ba68af080e7119776f0ea758e6d9dbc9082bc661b5a37dc52b53d8",
     "b0537c7b5df1005d4c3946eb559e90e986c05e56dd1581fb1a60e9909aa33f0b", 1),
    ("9188f8b96bdfeedc1921df5043eeb6e0120b2383b9a8fa454c50b5ef1ed64f0a",
     "2146400b929218bdc7d91b609fa2ea166922be78ee81802918f68c0af7c89dd9", 1),
    ("033a80bd39a494d0b1d3d6f0773ca278112f2e98cffbd3d2fcdceab6db3b653f",
     "6bc47b78562d9ff9ce8ad1527ac6a2f0f143944fd7fb497dff547fbb290b50bf", 1),
    ("2026-08-28-mainline-a72-admission-trace-softfail",
     "2026-08-30-mainline-a72-ready-admission-one-shot", 1),
    (".derived-collect-a72-admission-softtrace.XXXXXXXX",
     ".derived-collect-a72-ready-one-shot-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe READY one-shot collector derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"

if [[ ${1:-} == --materialize ]]; then
	[[ $# == 2 && ! -e "$2" && ! -L "$2" ]] || die 'usage: collect-live-trigger.sh --materialize NEW_FILE'
	install -m 0600 "$derived" "$2"
	cleanup
	trap - EXIT HUP INT TERM
	exit 0
fi

set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
