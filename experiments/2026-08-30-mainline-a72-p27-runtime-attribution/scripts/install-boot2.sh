#!/usr/bin/env bash

# Source-pin the guarded durable-record installer and retarget only the exact
# predecessor, known retained record, P27 diagnostic candidate, and evidence.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=095247d8d77eb34e9d4f44c0831b778cf7e08827db0139738dc54fec523009ea
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-28-mainline-a72-admission-durable-candidate/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-p27-attribution.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        'ledger_validator="$script_dir/validate-transition-ledger.py"',
        'ledger_validator="$repo_root/experiments/2026-08-28-mainline-a72-admission-durable-candidate/scripts/validate-transition-ledger.py"',
        1,
    ),
    (
        'trace_validator="$script_dir/validate-admission-trace.py"',
        'trace_validator="$repo_root/experiments/2026-08-28-mainline-a72-admission-durable-candidate/scripts/validate-admission-trace.py"',
        1,
    ),
    ("60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1",
     "e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", 2),
    ("7cbaf0980b37f6efb49e3fe0e373be68afb7f2e7011e4bc6e5bd7fee141c1f1d",
     "d5b84687a4c30f1fbb772aa8d807973e0c64f32f6b51d631c2e43b72ffb6b4fe", 2),
    (
        "readonly EXPECTED_PREDECESSOR_SHA256="
        "fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0\n",
        "readonly EXPECTED_PREDECESSOR_SHA256="
        "a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179\n"
        "readonly EXPECTED_RETAINED_LEDGER_HEX="
        "4442474348000000480000004737544c09000100010000000000000003000000"
        "010000000200000000000000b00178994737544c090001000100000000000000"
        "04000000030000000200000003000000b4c80f9a\n",
        1,
    ),
    ("candidate-a72-admission-trace-ed6fc529",
     "candidate-a72-p27-runtime-attribution-fbc299b0", 2),
    ("a72-admission-trace", "a72-p27-runtime-attribution", 5),
    ("experiment=2026-08-28-mainline-a72-admission-durable-candidate",
     "experiment=2026-08-30-mainline-a72-p27-runtime-attribution", 1),
    (
        "# Source-pin the live-GPT/TEE installer, retarget it to the exact durable CPU8\n"
        "# admission candidate, require all three retained records to be logical-empty,\n"
        "# and confirm TCP/22 closure after the verified write and clean shutdown.\n",
        "# Source-pin the live-GPT/TEE installer, retarget it to the exact CPU8 P27\n"
        "# diagnostic, accept only the published predecessor ledger plus empty traces,\n"
        "# and confirm TCP/22 closure after the verified write and clean shutdown.\n",
        1,
    ),
    (
        "grep -Fqx 'transition_ledger_state=logical-empty' <<<\"$ledger_output\" ||\n"
        "\tdie 'transition ledger is not exact logical-empty'",
        "[[ \"$ledger_hex\" == \"$EXPECTED_RETAINED_LEDGER_HEX\" ]] ||\n"
        "\tdie 'transition ledger is not the exact published predecessor record'\n"
        "for expected in transition_ledger_state=committed-valid \\\n"
        "\ttransition_ledger_latest_copy=1 transition_ledger_latest_attempt_id=1 \\\n"
        "\ttransition_ledger_latest_generation=4 transition_ledger_latest_phase=3 \\\n"
        "\ttransition_ledger_latest_stage=2 transition_ledger_latest_terminal=3; do\n"
        "\tgrep -Fqx \"$expected\" <<<\"$ledger_output\" ||\n"
        "\t\tdie 'transition ledger classification changed'\n"
        "done",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P27 diagnostic installer derivation: expected {count}, found {actual}: {old}"
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
