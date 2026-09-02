#!/usr/bin/env bash

# Admit exactly one repeatability namespace while preserving the proven
# completion-lock candidate collector and its pristine runtime gates.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0020bb5668edb0942e1f905ac4d4565f592709dd57c5f77e0b6757b7d1126a6a
readonly FIRST_MAINLINE_BOOT_ID=5d2fe57a-b599-47bd-8b4e-33ae22f9f1cb
readonly EXPECTED_OUTPUT=artifacts/runtime-captures/a72-cpu9-completion-lock-repeatability-attempt-2

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$script_dir/collect-completion-lock-repair-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || \
	die 'source completion-lock collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source completion-lock collector changed'

output=
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
	if [[ "${args[$i]}" == --output ]]; then
		((i + 1 < ${#args[@]})) || die '--output requires a value'
		output=${args[$((i + 1))]}
	fi
done
[[ "$output" == "$EXPECTED_OUTPUT" ]] || \
	die "repeatability output must be $EXPECTED_OUTPUT"

derived=$(mktemp "$script_dir/.derived-collect-a72-cpu9-completion-lock-repeatability.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "a72-cpu9-completion-lock-pretrigger-attempt-1"
new = "a72-cpu9-completion-lock-repeatability-attempt-2"
if text.count(old) != 1:
    raise SystemExit("unsafe repeatability collector derivation")
Path(sys.argv[2]).write_text(text.replace(old, new), encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
((rc == 0)) || exit "$rc"

classification="$repo_root/$output/classification.txt"
[[ -f "$classification" && ! -L "$classification" ]] || \
	die 'repeatability classification is missing or unsafe'
boot_id=$(awk -F= '$1 == "boot_id" {print $2}' "$classification")
[[ -n "$boot_id" ]] || die 'repeatability boot ID is missing'
[[ "$boot_id" != "$FIRST_MAINLINE_BOOT_ID" ]] || \
	die 'repeatability boot reused the first mainline boot ID'
printf 'repeatability_boot_id=%s\n' "$boot_id"
printf 'first_mainline_boot_id=%s\n' "$FIRST_MAINLINE_BOOT_ID"
printf '%s\n' 'repeatability_boot_id_fresh=yes'
