#!/usr/bin/env bash

# Source-pin the guarded CPU9 installer to the exact configuration-identity
# repair candidate and require the first production CPU9 candidate on boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=d1929a7ae6770e1abee71bf74083bbd37b8f0e708992d522582128b1092c2874
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-cpu9-config-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("fb473d2f3240137ec05f901163bb0374ef3015b66c42558eca6f1085cbd83468",
     "118096351905936e8f7c1fe9b186dadb191808bc94092cbd7a67a0b936a00562", 1),
    ("f6a1ea0b96243207a1d8b6742fae2ecbfb87dda210320b5e214025a596db895a",
     "5f8b1722c664c81d9c168c388c1f80037ea4dc16369ca94d04081cf897fc1c93", 1),
    ("candidate-a72-cpu9-controller-dd4b9358",
     "candidate-a72-cpu9-config-repair-e7ea9113", 1),
    ("cpu9-same-boot-successor", "cpu9-config-identity-repair", 1),
    ("CPU9 same-boot successor", "CPU9 configuration-identity repair", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe repaired CPU9 installer derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
predecessor = "42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee"
new_predecessor = "fb473d2f3240137ec05f901163bb0374ef3015b66c42558eca6f1085cbd83468"
if text.count(predecessor) != 2:
    raise SystemExit("unsafe repaired CPU9 installer derivation: predecessor chain changed")
offset = text.rfind(predecessor)
text = text[:offset] + new_predecessor + text[offset + len(predecessor):]
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
