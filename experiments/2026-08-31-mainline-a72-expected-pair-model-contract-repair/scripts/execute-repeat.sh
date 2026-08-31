#!/usr/bin/env bash

# Derive the audited single-session executor for the candidate's second boot.
# It accepts only the attempt-2 pretrigger directory and never retries.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=7708a624e7831d1e09d18dddaf1e9c3cd6865fb88dac670fb6e40d2fe51d3fca
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-30-mainline-a72-ready-token-contract-repair/scripts/execute-trigger.sh"
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-expected-pair-repeat.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179",
     "42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee", 1),
    ("620c6273e59286f65e67084bb071ae60cd53b27e9634188492cc47611d6f37d2",
     "313ba8b4cd06cca00e0ada3d138e5201d350258802a71e5d44889fa7c96e86ef", 1),
    ("3d5bfa25d84239232d765b4fba000ffa89246bf20ed636bca19e3afe92d1f9dd",
     "b103158a5f4da63cec4f1a37092b071139fa0774e209519afe609850f6a8acd9", 1),
    ("8feeb6e8c562278c0e76c284a757c8849dcc0d1e5eff705fee3434229c82eb52",
     "6ed44a37f0b7c495c01ef24fdb91cd469da2fbe5323c81e18db1a6355ce962c4", 1),
    ("a72-ready-token-contract-repair-pretrigger-attempt-1",
     "a72-expected-pair-model-contract-repair-pretrigger-attempt-2", 1),
    ("2026-08-30-mainline-a72-ready-token-contract-repair",
     "2026-08-31-mainline-a72-expected-pair-model-contract-repair", 2),
    ('trigger_wrapper="$script_dir/remote-trigger.sh"',
     'trigger_wrapper="$script_dir/remote-repeat-trigger.sh"', 1),
    ('classifier="$script_dir/classify-attempt.py"',
     'classifier="$script_dir/classify-repeat.py"', 1),
    ("experiment's collect-pretrigger.sh",
     "experiment's collect-repeat-pretrigger.sh", 1),
    ("ready-contract", "expected-pair-repeat", 3),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe repeat executor derivation: expected {count}, "
            f"found {actual}: {old}"
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
