#!/usr/bin/env bash

# Admit one fresh exact CPU-map boot under the proven pristine gate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=28ab51b834d645497ef1a6f22dd301625f20411583eb1d549851d5f54802c200
readonly EXPECTED_OUTPUT=artifacts/runtime-captures/a72-mt6797-cpu-map-attempt-1
readonly PRIOR_BOOT_IDS='5d2fe57a-b599-47bd-8b4e-33ae22f9f1cb aa713784-c702-49f5-bbe0-ea1b86dcd158 ce55410c-cf39-4028-b248-052865eb161c'
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-30-mainline-a72-ready-token-contract-repair/scripts/collect-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source pristine-state collector is absent or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source pristine-state collector changed'

output=
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
	if [[ "${args[$i]}" == --output ]]; then
		((i + 1 < ${#args[@]})) || die '--output requires a value'
		output=${args[$((i + 1))]}
	fi
done
[[ "$output" == "$EXPECTED_OUTPUT" ]] || die "output must be $EXPECTED_OUTPUT"

derived=$(mktemp "$script_dir/.derived-collect-mt6797-cpu-map.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179",
     "68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393", 1),
    ("bbb041f98bad1fa071a2aebf1c22ebaa462d5f3e45bb8472c59afd6fc1e7d83d",
     "172328659393cb8ddeb931cf0bf89d9a01f96a2a008dc2eee8db5f06511bb16a", 1),
    ("ea8d422fca8cdfc8af5c5c3fc57f9d1988ccaaa700e1f4cceac0489f37053234",
     "3e43ba835b1a2c554298a9b1972da910aa58b61d264639d065f3b8a7aba78222", 1),
    ("8feeb6e8c562278c0e76c284a757c8849dcc0d1e5eff705fee3434229c82eb52",
     "9e1617b8121f33f45b67749fa0b5cf195557bbedd57b279ff47b800f0e9d5ab5", 1),
    ("__GEMINI_A72_READY_CONTRACT_PRETRIGGER_SCRIPT__",
     "__GEMINI_MT6797_CPU_MAP_PRETRIGGER_SCRIPT__", 1),
    ("a72-ready-token-contract-repair-pretrigger-attempt-1",
     "a72-mt6797-cpu-map-attempt-1", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU-map collector derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
/bin/bash "$derived" "$@"

classification="$repo_root/$output/classification.txt"
boot_id=$(awk -F= '$1 == "boot_id" { print $2; count++ } END { exit count != 1 }' "$classification") || \
	die 'fresh boot ID is absent or duplicated'
for prior in $PRIOR_BOOT_IDS; do
	[[ "$boot_id" != "$prior" ]] || die "prior mainline boot ID was reused: $boot_id"
done
printf 'fresh_mainline_boot_id=%s\n' "$boot_id"
printf '%s\n' prior_mainline_boot_ids_rejected=yes
