#!/usr/bin/env bash

# Source-pin the proven boot-bound executor and retarget the exact CPU9
# candidate, tooling identities, evidence namespace, and request bounds.
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

derived=$(mktemp "$script_dir/.derived-execute-a72-cpu9.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179",
     "fb473d2f3240137ec05f901163bb0374ef3015b66c42558eca6f1085cbd83468", 1),
    ("620c6273e59286f65e67084bb071ae60cd53b27e9634188492cc47611d6f37d2",
     "32e1b61a3b005d0cbb2d14a6253b74ed2bd8daa66a6562c64dc92156ad8cf5cf", 1),
    ("3d5bfa25d84239232d765b4fba000ffa89246bf20ed636bca19e3afe92d1f9dd",
     "aaa118785b74e6f88f3412f6b8a2e958cdf6c989ed5672762ffd972923af3130", 1),
    ("8feeb6e8c562278c0e76c284a757c8849dcc0d1e5eff705fee3434229c82eb52",
     "70c3ef9ae11b849c0826022463ccde4bd311554743aa318f2cfe8749d5c40878", 1),
    ("2026-08-30-mainline-a72-ready-token-contract-repair",
     "2026-08-31-mainline-a72-cpu9-same-boot-successor", 2),
    ("a72-ready-token-contract-repair-pretrigger-attempt-1",
     "a72-cpu9-same-boot-successor-pretrigger-attempt-1", 1),
    (".gemini-a72-ready-contract-validation.XXXXXXXX",
     ".gemini-a72-cpu9-validation.XXXXXXXX", 1),
    (".gemini-a72-ready-contract-trigger.XXXXXXXX",
     ".gemini-a72-cpu9-trigger.XXXXXXXX", 1),
    (".gemini-a72-ready-contract-command.XXXXXXXX",
     ".gemini-a72-cpu9-command.XXXXXXXX", 1),
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
            f"unsafe CPU9 executor derivation: expected {count}, "
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
