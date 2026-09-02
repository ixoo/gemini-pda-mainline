#!/usr/bin/env bash

# Recover the terminal CPU8/CPU9 lanes after the bounded RAM observation and
# reject both earlier Gemian recovery boot IDs.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=81c79389d754cded85c48494ccea80dec756c52aba3f4c5ca884b5dbde6a39ee
readonly FIRST_GEMIAN_BOOT_ID=d0ff9f03-a6ab-465f-91e8-1f6392d5bb07
readonly SECOND_GEMIAN_BOOT_ID=187f5e44-917e-465b-998e-dbc6e29009be
readonly EXPECTED_OUTPUT=artifacts/device-pstore/a72-dual-ram-coherency-recovery-attempt-1

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/collect-completion-lock-repair-recovery.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source recovery collector is absent or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source recovery collector changed'
source_dir=$(cd -- "$(dirname -- "$source_collector")" && pwd -P)

output=
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
	if [[ "${args[$i]}" == --output-dir ]]; then
		((i + 1 < ${#args[@]})) || die '--output-dir requires a value'
		output=${args[$((i + 1))]}
	fi
done
[[ "$output" == "$EXPECTED_OUTPUT" ]] || die "recovery output must be $EXPECTED_OUTPUT"

derived=$(mktemp "$source_dir/.derived-collect-dual-a72-ram-recovery.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "a72-cpu9-completion-lock-repair-recovery-attempt-1"
new = "a72-dual-ram-coherency-recovery-attempt-1"
if text.count(old) != 1:
    raise SystemExit("unsafe recovery-collector derivation")
Path(sys.argv[2]).write_text(text.replace(old, new), encoding="utf-8")
PY
chmod 0700 "$derived"
/bin/bash "$derived" "$@"

summary="$repo_root/$output/recovery-summary.txt"
[[ -f "$summary" && ! -L "$summary" ]] || die 'recovery summary is absent or unsafe'
boot_id=$(awk -F= '$1 == "runtime_boot_id" { print $2; count++ } END { exit count != 1 }' "$summary") || \
	die 'Gemian recovery boot ID is absent or duplicated'
[[ "$boot_id" != "$FIRST_GEMIAN_BOOT_ID" ]] || die 'first Gemian boot ID was reused'
[[ "$boot_id" != "$SECOND_GEMIAN_BOOT_ID" ]] || die 'second Gemian boot ID was reused'
printf 'fresh_gemian_boot_id=%s\n' "$boot_id"
printf '%s\n' prior_gemian_boot_ids_rejected=yes
