#!/usr/bin/env bash

# Derive the bounded read-only collector for the second independent boot of
# the exact candidate. The historical attempt-1 evidence remains untouched.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=28ab51b834d645497ef1a6f22dd301625f20411583eb1d549851d5f54802c200
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-30-mainline-a72-ready-token-contract-repair/scripts/collect-pretrigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-expected-pair-repeat.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179",
     "42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee", 1),
    ("bbb041f98bad1fa071a2aebf1c22ebaa462d5f3e45bb8472c59afd6fc1e7d83d",
     "a303ab237d22d2ae55d1df656cd963698152937dc7d122f87f5896eb7c7ae561", 1),
    ("ea8d422fca8cdfc8af5c5c3fc57f9d1988ccaaa700e1f4cceac0489f37053234",
     "56e3800749e7c6ba7c791db349a5a11d81f4e293ba8d983c15b858a6f51e6616", 1),
    ("8feeb6e8c562278c0e76c284a757c8849dcc0d1e5eff705fee3434229c82eb52",
     "6ed44a37f0b7c495c01ef24fdb91cd469da2fbe5323c81e18db1a6355ce962c4", 1),
    ("a72-ready-token-contract-repair-pretrigger-attempt-1",
     "a72-expected-pair-model-contract-repair-pretrigger-attempt-2", 2),
    ("ready-contract", "expected-pair-repeat", 2),
    ("__GEMINI_A72_READY_CONTRACT_PRETRIGGER_SCRIPT__",
     "__GEMINI_A72_EXPECTED_PAIR_REPEAT_PRETRIGGER_SCRIPT__", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe repeat collector derivation: expected {count}, "
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
