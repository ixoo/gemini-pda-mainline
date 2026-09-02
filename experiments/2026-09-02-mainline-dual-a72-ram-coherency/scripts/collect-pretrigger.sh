#!/usr/bin/env bash

# Admit one fresh current-mainline boot under the proven pristine gate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0020bb5668edb0942e1f905ac4d4565f592709dd57c5f77e0b6757b7d1126a6a
readonly FIRST_MAINLINE_BOOT_ID=5d2fe57a-b599-47bd-8b4e-33ae22f9f1cb
readonly SECOND_MAINLINE_BOOT_ID=aa713784-c702-49f5-bbe0-ea1b86dcd158
readonly EXPECTED_OUTPUT=artifacts/runtime-captures/a72-dual-ram-coherency-attempt-1
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/collect-completion-lock-repair-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is absent or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'
source_dir=$(cd -- "$(dirname -- "$source_collector")" && pwd -P)

output=
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
	if [[ "${args[$i]}" == --output ]]; then
		((i + 1 < ${#args[@]})) || die '--output requires a value'
		output=${args[$((i + 1))]}
	fi
done
[[ "$output" == "$EXPECTED_OUTPUT" ]] || die "output must be $EXPECTED_OUTPUT"

derived=$(mktemp "$source_dir/.derived-collect-dual-a72-ram-pretrigger.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "a72-cpu9-completion-lock-pretrigger-attempt-1"
new = "a72-dual-ram-coherency-attempt-1"
if text.count(old) != 1:
    raise SystemExit("unsafe pre-trigger collector derivation")
Path(sys.argv[2]).write_text(text.replace(old, new), encoding="utf-8")
PY
chmod 0700 "$derived"
/bin/bash "$derived" "$@"

classification="$repo_root/$output/classification.txt"
boot_id=$(awk -F= '$1 == "boot_id" { print $2; count++ } END { exit count != 1 }' "$classification") || \
	die 'fresh boot ID is absent or duplicated'
[[ "$boot_id" != "$FIRST_MAINLINE_BOOT_ID" ]] || die 'first mainline boot ID was reused'
[[ "$boot_id" != "$SECOND_MAINLINE_BOOT_ID" ]] || die 'second mainline boot ID was reused'
printf 'fresh_mainline_boot_id=%s\n' "$boot_id"
printf '%s\n' prior_mainline_boot_ids_rejected=yes
