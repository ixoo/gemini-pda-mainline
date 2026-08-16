#!/usr/bin/env bash

# Source-pin and mechanically derive the guarded installer for the exact
# post-ramoops checkpoint candidate. The inherited policy resolves live GPT
# boot2, records but does not back up the predecessor, verifies a full
# readback, and powers off after success.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=2b61e21cb835a493a5857443e8bfc2a01b3f75b7462e58d981489f1434e84495

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-15-mainline-module-policy-control/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("# module-policy serviceability control.", "# post-ramoops checkpoint candidate.", 2),
    ("044461e57d207f5ddd6e68cc463ea3ee1dd65260c27afe5fd00730137d13a2ff",
     "ae6b354d51a9e5096b9f6f74ee9037c47ba026e00895e6f4c8028f15bc9bd348", 1),
    ("1c2e591e3b9c130febb491ef5d243ea9d6b1b7d6b60b5830ab67e32e332a155b",
     "a375c3c99ad4a7531e93343e3676c109fe2aadc2a0f1821d940fcb1a603b829d", 1),
    ("candidate-da921x-module-policy-control-782850c4",
     "candidate-post-ramoops-checkpoint-e16405f0", 1),
    ("module-policy-control-deployment-", "post-ramoops-checkpoint-deployment-", 1),
    (r"\.gemini-module-policy-control\.", r"\.gemini-post-ramoops-checkpoint\.", 1),
    ("/home/gemini/.gemini-module-policy-control.XXXXXXXX",
     "/home/gemini/.gemini-post-ramoops-checkpoint.XXXXXXXX", 1),
    ("experiment=2026-08-15-mainline-module-policy-control",
     "experiment=2026-08-15-mainline-post-ramoops-checkpoint", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe installer derivation: expected {count} occurrences, found {actual}: {old}"
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
