#!/usr/bin/env bash

# Source-pin the proven bounded collector and retarget the exact CPU9 progress
# candidate, read-only probe, validator, and private evidence namespace.
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
[[ -f "$source_collector" && ! -L "$source_collector" ]] || \
	die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-cpu9-progress.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179",
     "ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72", 1),
    ("bbb041f98bad1fa071a2aebf1c22ebaa462d5f3e45bb8472c59afd6fc1e7d83d",
     "ed6bbde65f0ce7dd0c5dd4bb53e1535c3cb624671b12904f27fe62edf03b5f99", 1),
    ("ea8d422fca8cdfc8af5c5c3fc57f9d1988ccaaa700e1f4cceac0489f37053234",
     "5f010324729e4735b3e6df2fdbe2333cec88e3acdbe36b86cf36ba8ab8c7b2cb", 1),
    ("8feeb6e8c562278c0e76c284a757c8849dcc0d1e5eff705fee3434229c82eb52",
     "4ad80105fd840ea02ca57c3dff1dd9fbe10b81047d06169b3981f4caa130867e", 1),
    ("__GEMINI_A72_READY_CONTRACT_PRETRIGGER_SCRIPT__",
     "__GEMINI_A72_CPU9_PROGRESS_PRETRIGGER_SCRIPT__", 1),
    ("remote-pretrigger.sh", "remote-progress-pretrigger.sh", 1),
    ("validate-pretrigger.py", "validate-progress-pretrigger.py", 1),
    ("a72-ready-token-contract-repair-pretrigger-attempt-1",
     "a72-cpu9-progress-attempt-pretrigger-attempt-1", 2),
    (".gemini-a72-ready-contract-probe.XXXXXXXX",
     ".gemini-a72-cpu9-progress-probe.XXXXXXXX", 1),
    (".gemini-a72-ready-contract-command.XXXXXXXX",
     ".gemini-a72-cpu9-progress-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress collector derivation: expected {count}, "
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
