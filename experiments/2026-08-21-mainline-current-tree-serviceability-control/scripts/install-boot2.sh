#!/usr/bin/env bash

# Source-pin the guarded clock-entry-control installer for the exact current-
# tree serviceability candidate. The inherited workflow resolves live GPT
# boot2, verifies the whole partition, and shuts down without rebooting.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a64c85f35443cc4247df3023e61c50f8de4a71181d45621f0701c7f18ba99eb2

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-21-mainline-clock-entry-observation-control/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2-current-service.XXXXXXXX")"
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
        "fc2a9a1a53de1373cf75d14f163a5b9921219996882f58e0b5395595872230bf",
        "7084f2ee87af103dfcf1dfad9956f54c2a9df8d37b5f6d0388ba45464d8d52a3",
        1,
    ),
    (
        "5932e3dd90903b48342126131ddd433107ed8d6b10c9d49b285cc9ccc383e9c3",
        "22ce8bd6947018aac619614eca5e933b5fe6ce14f393651b0ce92ffebbce9632",
        1,
    ),
    (
        "candidate-clock-entry-control-a36425f3",
        "candidate-current-service-control-691ff883",
        1,
    ),
    (
        "clock-entry-observation-control-deployment-",
        "current-tree-serviceability-control-deployment-",
        1,
    ),
    (r"\.gemini-clock-entry-control\.", r"\.gemini-current-service-control\.", 1),
    (
        "/home/gemini/.gemini-clock-entry-control.XXXXXXXX",
        "/home/gemini/.gemini-current-service-control.XXXXXXXX",
        1,
    ),
    (
        "experiment=2026-08-21-mainline-clock-entry-observation-control",
        "experiment=2026-08-21-mainline-current-tree-serviceability-control",
        1,
    ),
    (
        ".derived-install-boot2-clock-entry-control.XXXXXXXX",
        ".derived-install-boot2-current-service-inner.XXXXXXXX",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe service-control installer derivation: expected {count} "
            f"occurrences, found {actual}: {old}"
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
