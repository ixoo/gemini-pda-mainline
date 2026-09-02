#!/usr/bin/env bash

# Recover the exact completion-lock retained proof into the separately named
# attempt-2 namespace and reject the first attempt's Gemian recovery cycle.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=81c79389d754cded85c48494ccea80dec756c52aba3f4c5ca884b5dbde6a39ee
readonly FIRST_GEMIAN_BOOT_ID=d0ff9f03-a6ab-465f-91e8-1f6392d5bb07
readonly EXPECTED_OUTPUT=artifacts/device-pstore/a72-cpu9-completion-lock-repair-repeatability-recovery-attempt-2

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$script_dir/collect-completion-lock-repair-recovery.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || \
	die 'source completion-lock recovery collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source completion-lock recovery collector changed'

output=
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
	if [[ "${args[$i]}" == --output-dir ]]; then
		((i + 1 < ${#args[@]})) || die '--output-dir requires a value'
		output=${args[$((i + 1))]}
	fi
done
[[ "$output" == "$EXPECTED_OUTPUT" ]] || \
	die "repeatability recovery output must be $EXPECTED_OUTPUT"

derived=$(mktemp "$script_dir/.derived-collect-a72-cpu9-completion-lock-repeatability-recovery.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "a72-cpu9-completion-lock-repair-recovery-attempt-1"
new = "a72-cpu9-completion-lock-repair-repeatability-recovery-attempt-2"
if text.count(old) != 1:
    raise SystemExit("unsafe repeatability recovery derivation")
Path(sys.argv[2]).write_text(text.replace(old, new), encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
((rc == 0)) || exit "$rc"

summary="$repo_root/$output/recovery-summary.txt"
[[ -f "$summary" && ! -L "$summary" ]] || \
	die 'repeatability recovery summary is missing or unsafe'
boot_id=$(awk -F= '$1 == "runtime_boot_id" {print $2}' "$summary")
[[ -n "$boot_id" ]] || die 'repeatability Gemian boot ID is missing'
[[ "$boot_id" != "$FIRST_GEMIAN_BOOT_ID" ]] || \
	die 'repeatability recovery reused the first Gemian boot ID'
printf 'repeatability_gemian_boot_id=%s\n' "$boot_id"
printf 'first_gemian_boot_id=%s\n' "$FIRST_GEMIAN_BOOT_ID"
printf '%s\n' 'repeatability_gemian_boot_id_fresh=yes'
