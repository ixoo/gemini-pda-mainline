#!/usr/bin/env bash

# Source-pin the guarded platform-state installer and retarget only the exact
# platform/provider candidate. Accept an empty retained pair or the exact
# completed platform-snapshot pair that this experiment supersedes.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=63d68dd576d7aaf7526f6ddaca9f28ae662d5dc48b4636ce57167c6c446a4918
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-24-mainline-a72-platform-state-only/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-platform-provider.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        "# platform-state-only candidate. Accept only an empty retained pair or the\n"
        "# exact Stage-27 control pair that this live-network experiment supersedes.",
        "# platform/provider candidate. Accept only an empty retained pair or the\n"
        "# exact completed platform-snapshot pair that this experiment supersedes.",
        1,
    ),
    (
        "readonly VALID_HEADER=444247437800000078000000",
        "readonly VALID_HEADER_1=444247437600000076000000\n"
        "readonly VALID_HEADER_2=444247437500000075000000",
        1,
    ),
    (
        "readonly CONTROL_1_SHA256=dd39c08c5de7d9cde7ccf9f62707521475ce1ff35b3833f06443939bcff79e06",
        "readonly CONTROL_1_SHA256=116230552a3b7a0b3738618a5c8a7809de1a52f58353b0b94b132f383a0751e9",
        1,
    ),
    (
        "readonly CONTROL_2_SHA256=ad7909f9294e69f1efc13354c997b864a40c89a5c9f1cef9a445aa4f9f58b239",
        "readonly CONTROL_2_SHA256=7f79d34ed0c91f1ab7a6686db3a631cc92ac446887418ab3717302af4a0d149c",
        1,
    ),
    (
        "VALID_HEADER='$VALID_HEADER' EMPTY_SHA256='$EMPTY_SHA256'",
        "VALID_HEADER_1='$VALID_HEADER_1' VALID_HEADER_2='$VALID_HEADER_2' EMPTY_SHA256='$EMPTY_SHA256'",
        1,
    ),
    (
        '"$header_1" == "$VALID_HEADER" && "$header_2" == "$VALID_HEADER"',
        '"$header_1" == "$VALID_HEADER_1" && "$header_2" == "$VALID_HEADER_2"',
        1,
    ),
    (
        "state=exact-stage27-control-pair",
        "state=exact-platform-snapshot-pair",
        1,
    ),
    (
        "retained records are neither exact empty nor the exact Stage-27 control pair",
        "retained records are neither exact empty nor the exact platform-snapshot pair",
        1,
    ),
    ("012f7eac6884e65baab075ef286929f610a63f2ea065eba45865bd046492a23f", "ff902d12b95893872990ebf813f24ca298ca76c4f86d4650f3b696cbdc00d79f", 1),
    ("07f89b083539be006efe1e8407694153daa00b581b95394e40844bd71d54c7da", "929437b47a7128b661e98a9e49eb7d074e893839fc2c07e2d732add06455bd2a", 1),
    ("candidate-a72-platform-state-only-f3210fb3", "candidate-a72-platform-provider-snapshot-32059676", 1),
    ("a72-platform-state-only-deployment-", "a72-platform-provider-snapshot-deployment-", 1),
    (r"\.gemini-a72-platform-state-only\.", r"\.gemini-a72-platform-provider-snapshot\.", 1),
    ("/home/gemini/.gemini-a72-platform-state-only.XXXXXXXX", "/home/gemini/.gemini-a72-platform-provider-snapshot.XXXXXXXX", 1),
    ("experiment=2026-08-24-mainline-a72-platform-state-only", "experiment=2026-08-25-mainline-a72-platform-provider-snapshot-second-read", 1),
    ("unsafe platform-state-only installer derivation", "unsafe platform/provider installer derivation", 1),
    (".derived-install-boot2-a72-platform-only.XXXXXXXX", ".derived-install-boot2-a72-platform-provider-nested.XXXXXXXX", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe platform/provider installer wrapper: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
