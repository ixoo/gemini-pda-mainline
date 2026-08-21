#!/usr/bin/env bash

# Source-pin the guarded call-ledger installer for the exact probe/gate-ledger
# candidate and retain its bounded live empty-slot preflight before delegation.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=c50d192b65ceda483e3fa3def5e1bf21d93eb7e64425effd120192c17197f4e9

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-21-mainline-protected-readback-call-ledger/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2-probe-gate-ledger.XXXXXXXX")"
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
        "# Source-pin the guarded protected-readback installer for the exact call-ledger\n"
        "# candidate and require a bounded live empty-slot preflight before delegation.",
        "# Source-pin the guarded protected-readback installer for the exact probe/gate-ledger\n"
        "# candidate and require a bounded live empty-slot preflight before delegation.",
        1,
    ),
    (
        "3ce494c971c24c9edab73aac592d0ba8dd0bbd25f06051245f7846f95d0c715a",
        "6cb729efacea914b993221f0f85a1ab7e67eb6bca915802a8236bb31edab2e62",
        1,
    ),
    (
        "a4c5f0f463071aa46613230d1d9d1fb364664bb6722f701f218099402860c545",
        "57144fa24ad69a6b2b69817fad86c66c0dda0eed1bf1b005db13cfa01748854a",
        1,
    ),
    (
        "candidate-protected-readback-ledger-199e618a",
        "candidate-protected-readback-probe-gate-c04de416",
        1,
    ),
    (
        "protected-readback-call-ledger-deployment-",
        "protected-readback-probe-gate-ledger-deployment-",
        1,
    ),
    (
        r"\.gemini-protected-readback-ledger\.",
        r"\.gemini-protected-readback-probe-gate\.",
        1,
    ),
    (
        "/home/gemini/.gemini-protected-readback-ledger.XXXXXXXX",
        "/home/gemini/.gemini-protected-readback-probe-gate.XXXXXXXX",
        1,
    ),
    (
        "experiment=2026-08-21-mainline-protected-readback-call-ledger",
        "experiment=2026-08-21-mainline-protected-readback-probe-gate-ledger",
        1,
    ),
    (
        ".derived-install-boot2-call-ledger.XXXXXXXX",
        ".derived-install-boot2-probe-gate-ledger-inner.XXXXXXXX",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe probe/gate installer derivation: expected {count} occurrences, "
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
