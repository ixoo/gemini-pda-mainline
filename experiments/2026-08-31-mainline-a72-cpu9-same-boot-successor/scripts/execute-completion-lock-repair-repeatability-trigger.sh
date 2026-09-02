#!/usr/bin/env bash

# Spend the exact completion-lock trigger once on the separately named,
# fresh-boot repeatability capture.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=4c472374115c49977c484e0b25be38d1c4e0b914c62da8cd196878cb617b2de7
readonly FIRST_MAINLINE_BOOT_ID=5d2fe57a-b599-47bd-8b4e-33ae22f9f1cb
readonly EXPECTED_PRETRIGGER=artifacts/runtime-captures/a72-cpu9-completion-lock-repeatability-attempt-2

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$script_dir/execute-completion-lock-repair-trigger.sh"
[[ -f "$source_executor" && ! -L "$source_executor" ]] || \
	die 'source completion-lock executor is missing or unsafe'
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source completion-lock executor changed'

pretrigger=
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
	if [[ "${args[$i]}" == --pretrigger-dir ]]; then
		((i + 1 < ${#args[@]})) || die '--pretrigger-dir requires a value'
		pretrigger=${args[$((i + 1))]}
	fi
done
[[ "$pretrigger" == "$EXPECTED_PRETRIGGER" ]] || \
	die "repeatability pretrigger must be $EXPECTED_PRETRIGGER"

classification="$repo_root/$pretrigger/classification.txt"
[[ -f "$classification" && ! -L "$classification" ]] || \
	die 'repeatability classification is missing or unsafe'
boot_id=$(awk -F= '$1 == "boot_id" {print $2}' "$classification")
[[ -n "$boot_id" ]] || die 'repeatability boot ID is missing'
[[ "$boot_id" != "$FIRST_MAINLINE_BOOT_ID" ]] || \
	die 'repeatability boot reused the first mainline boot ID'

derived=$(mktemp "$script_dir/.derived-execute-a72-cpu9-completion-lock-repeatability.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "a72-cpu9-completion-lock-pretrigger-attempt-1"
new = "a72-cpu9-completion-lock-repeatability-attempt-2"
if text.count(old) != 1:
    raise SystemExit("unsafe repeatability executor derivation")
Path(sys.argv[2]).write_text(text.replace(old, new), encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
