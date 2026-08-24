#!/usr/bin/env bash

# Source-pin the guarded physical-source installer and retarget only its exact
# global-initcall candidate, evidence names, and experiment identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=5019ea5fb3859759be49690e3cd83f2abe583350a358ca3bc56aa189c4a789e4

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-24-mainline-a72-physical-source-observer/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-global-initcall.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    (
        "# Source-pin the guarded two-record installer and retarget only its exact\n"
        "# physical-source candidate, evidence names, and experiment identity.",
        "# Source-pin the guarded two-record installer and retarget only its exact\n"
        "# A72 global-initcall candidate, evidence names, and experiment identity.",
        1,
    ),
    (
        ".derived-install-boot2-a72-physical-source.XXXXXXXX",
        ".derived-install-boot2-a72-global-initcall.XXXXXXXX",
        2,
    ),
    ("exact A72 physical-source", "exact A72 global-initcall", 1),
    (
        "aa02ab666e63e7011139c1057bda99cdbab89245d41f9cad59dae30743b41246",
        "e9d565021de9ed1164aa78a78795d6a3dabd7af656aaa3df791e23424e66125a",
        1,
    ),
    (
        "683adfea30e7b7c82eb304705fe699b579ebbb0525c38ee57b296df75f0652ed",
        "39a1b062065b2da89b4ab8561001b37e8d444a6884367d8571bbf177b62d8840",
        1,
    ),
    (
        "candidate-a72-physical-source-1d0c1420",
        "candidate-a72-global-initcall-41a181f6",
        1,
    ),
    (
        "a72-physical-source-deployment-",
        "a72-global-initcall-deployment-",
        1,
    ),
    (
        r"\.gemini-a72-physical-source\.",
        r"\.gemini-a72-global-initcall\.",
        1,
    ),
    (
        "/home/gemini/.gemini-a72-physical-source.XXXXXXXX",
        "/home/gemini/.gemini-a72-global-initcall.XXXXXXXX",
        1,
    ),
    (
        "experiment=2026-08-24-mainline-a72-physical-source-observer",
        "experiment=2026-08-24-mainline-a72-global-initcall-ledger",
        1,
    ),
    (
        "unsafe A72 physical-source installer derivation",
        "unsafe A72 global-initcall installer derivation",
        1,
    ),
    (
        "unsafe physical-source installer derivation",
        "unsafe global-initcall installer derivation",
        1,
    ),
    (
        "live A72 physical-source preflight failed",
        "live A72 global-initcall preflight failed",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe global-initcall installer derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"

set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
