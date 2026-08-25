#!/usr/bin/env bash

# Source-pin the guarded predecessor installer and retarget it to the exact
# provider-ready candidate. Accept only empty retained records or the exact
# before-provider/empty pair recovered from the predecessor attempt.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=21e4a7de9fa0736cb2ee4e2eb91c14be374b19ca8c45c9779d0700992c05cf92
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-25-mainline-a72-platform-provider-snapshot-second-read/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-platform-provider-ready.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        "# platform/provider candidate. Accept an empty retained pair or the exact\n"
        "# completed platform-snapshot pair that this experiment supersedes.",
        "# provider-ready candidate. Accept only an empty retained pair or the\n"
        "# exact before-provider/empty pair recovered from its predecessor.",
        1,
    ),
    ("readonly VALID_HEADER_1=444247437600000076000000", "readonly VALID_HEADER_1=444247437f0000007f000000", 1),
    ("readonly VALID_HEADER_2=444247437500000075000000", "readonly VALID_HEADER_2=444247430000000000000000", 1),
    ("readonly CONTROL_1_SHA256=116230552a3b7a0b3738618a5c8a7809de1a52f58353b0b94b132f383a0751e9", "readonly CONTROL_1_SHA256=047e5c5c6f3bfa3b8f86ba174c3e1ceb65926a190dbec7099f915ee5b7e371b2", 1),
    ("readonly CONTROL_2_SHA256=7f79d34ed0c91f1ab7a6686db3a631cc92ac446887418ab3717302af4a0d149c", "readonly CONTROL_2_SHA256=d58e2f4ee9541fa1f2a2d07247ffb6a1fa6a31fefaa83c3715fcfe4fd3ec9998", 1),
    ("state=exact-platform-snapshot-pair", "state=exact-before-provider-only-pair", 1),
    ("retained records are neither exact empty nor the exact platform-snapshot pair", "retained records are neither exact empty nor the exact predecessor before-provider-only pair", 1),
    ("ff902d12b95893872990ebf813f24ca298ca76c4f86d4650f3b696cbdc00d79f", "f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e", 1),
    ("929437b47a7128b661e98a9e49eb7d074e893839fc2c07e2d732add06455bd2a", "ffee91da5291546ce95c807cf22a659976fa10ef61546b4cb8084e80b8627458", 1),
    ("candidate-a72-platform-provider-snapshot-32059676", "candidate-a72-platform-provider-ready-041896e2", 1),
    ("a72-platform-provider-snapshot-deployment-", "a72-platform-provider-ready-deployment-", 1),
    (r"\.gemini-a72-platform-provider-snapshot\.", r"\.gemini-a72-platform-provider-ready\.", 1),
    ("/home/gemini/.gemini-a72-platform-provider-snapshot.XXXXXXXX", "/home/gemini/.gemini-a72-platform-provider-ready.XXXXXXXX", 1),
    ("experiment=2026-08-25-mainline-a72-platform-provider-snapshot-second-read", "experiment=2026-08-25-mainline-a72-platform-provider-deferred-bind-repair", 1),
    ("unsafe platform/provider installer derivation", "unsafe provider-ready installer derivation", 1),
    (".derived-install-boot2-a72-platform-provider-nested.XXXXXXXX", ".derived-install-boot2-a72-platform-provider-ready-nested.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe provider-ready installer wrapper: expected {count}, found {actual}: {old}"
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
