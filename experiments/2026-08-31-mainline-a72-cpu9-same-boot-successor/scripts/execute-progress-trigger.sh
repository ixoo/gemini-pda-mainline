#!/usr/bin/env bash

# Source-pin the proven one-shot executor and retarget the exact progress
# candidate, tooling identities, evidence namespace, and A72 request bounds.
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
[[ -f "$source_executor" && ! -L "$source_executor" ]] || \
	die 'source executor is missing or unsafe'
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-cpu9-progress.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179",
     "ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72", 1),
    ("620c6273e59286f65e67084bb071ae60cd53b27e9634188492cc47611d6f37d2",
     "2e8a307a837741ead989284b3c74832504a7c4e64fbf55c9b0b2e3dc4878a609", 1),
    ("3d5bfa25d84239232d765b4fba000ffa89246bf20ed636bca19e3afe92d1f9dd",
     "90e58cb4b7223cc038023cbf3f89ca351fbd805bbacd465d00ac1b95bcf21943", 1),
    ("8feeb6e8c562278c0e76c284a757c8849dcc0d1e5eff705fee3434229c82eb52",
     "4ad80105fd840ea02ca57c3dff1dd9fbe10b81047d06169b3981f4caa130867e", 1),
    ("2026-08-30-mainline-a72-ready-token-contract-repair",
     "2026-08-31-mainline-a72-cpu9-same-boot-successor", 2),
    ("a72-ready-token-contract-repair-pretrigger-attempt-1",
     "a72-cpu9-progress-attempt-pretrigger-attempt-1", 1),
    ('trigger_wrapper="$script_dir/remote-trigger.sh"',
     'trigger_wrapper="$script_dir/remote-progress-trigger.sh"', 1),
    ('classifier="$script_dir/classify-attempt.py"',
     'classifier="$script_dir/classify-progress-attempt.py"', 1),
    ('validator="$script_dir/validate-pretrigger.py"',
     'validator="$script_dir/validate-progress-pretrigger.py"', 1),
    (".gemini-a72-ready-contract-validation.XXXXXXXX",
     ".gemini-a72-cpu9-progress-validation.XXXXXXXX", 1),
    (".gemini-a72-ready-contract-trigger.XXXXXXXX",
     ".gemini-a72-cpu9-progress-trigger.XXXXXXXX", 1),
    (".gemini-a72-ready-contract-command.XXXXXXXX",
     ".gemini-a72-cpu9-progress-command.XXXXXXXX", 1),
    (
        "then sends the CPU8 token in exactly one netcat session bound to the\n"
        "same boot ID. It never retries, requests CPU9, requests CPU_OFF, or reboots.",
        "then sends the CPU8-to-CPU9 controller token in exactly one netcat session\n"
        "bound to the same boot ID. It permits at most one request for each A72 CPU\n"
        "and never retries, requests CPU_OFF, or reboots.",
        1,
    ),
    (
        "printf 'trigger_maximum=1\\ntrigger_retried=no\\ncpu9_requests=0\\n'",
        "printf 'trigger_maximum=1\\ntrigger_retried=no\\n'\n"
        "\t\tprintf 'cpu8_request_maximum=1\\ncpu9_request_maximum=1\\n'",
        1,
    ),
    (
        "printf 'cpu9_requests=0\\ncpu_off_requests=0\\nretries=0\\nreboot_requested=no\\n'",
        "printf 'cpu8_request_maximum=1\\ncpu9_request_maximum=1\\n'\n"
        "\tprintf 'cpu_off_requests=0\\nretries=0\\nreboot_requested=no\\n'",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress executor derivation: expected {count}, "
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
