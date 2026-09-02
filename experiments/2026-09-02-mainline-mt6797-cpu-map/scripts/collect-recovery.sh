#!/usr/bin/env bash

# Recover the exact retained CPU8/CPU9 terminal lanes and unchanged CPU-map
# candidate after a changed-ID return to Gemian.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=81c79389d754cded85c48494ccea80dec756c52aba3f4c5ca884b5dbde6a39ee
readonly EXPECTED_OUTPUT=artifacts/device-pstore/a72-mt6797-cpu-map-recovery-attempt-1
readonly PRIOR_GEMIAN_BOOT_IDS='d0ff9f03-a6ab-465f-91e8-1f6392d5bb07 187f5e44-917e-465b-998e-dbc6e29009be de44c0b2-2ff2-4423-8f0b-8d6e9b0b9e04'
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/collect-completion-lock-repair-recovery.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source completion-lock recovery collector is absent or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source completion-lock recovery collector changed'
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

derived=$(mktemp "$source_dir/.derived-collect-mt6797-cpu-map-recovery.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e",
     "68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393", 1),
    ("a72-cpu9-completion-lock-repair-deployment-1",
     "a72-mt6797-cpu-map-deployment-1", 1),
    ("a72-cpu9-completion-lock-repair-recovery-attempt-1",
     "a72-mt6797-cpu-map-recovery-attempt-1", 1),
    ("experiment=2026-08-31-mainline-a72-cpu9-completion-lock-repair",
     "experiment=2026-09-02-mainline-mt6797-cpu-map", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU-map recovery derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
/bin/bash "$derived" "$@"

summary="$repo_root/$output/recovery-summary.txt"
[[ -f "$summary" && ! -L "$summary" ]] || die 'recovery summary is absent or unsafe'
boot_id=$(awk -F= '$1 == "runtime_boot_id" { print $2; count++ } END { exit count != 1 }' "$summary") || \
	die 'Gemian recovery boot ID is absent or duplicated'
for prior in $PRIOR_GEMIAN_BOOT_IDS; do
	[[ "$boot_id" != "$prior" ]] || die "prior Gemian boot ID was reused: $boot_id"
done
printf 'fresh_gemian_boot_id=%s\n' "$boot_id"
printf '%s\n' prior_gemian_boot_ids_rejected=yes
