#!/usr/bin/env bash

# Source-pin the bounded collector and retarget the exact CPU9 candidate,
# read-only probe, validator, and private evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a789d68c0a9b90ce2a17ca600c607a6f3e715ddfcce254033f11e8f6252b535d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-31-mainline-a72-expected-pair-model-contract-repair/scripts/collect-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-cpu9.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee",
     "fb473d2f3240137ec05f901163bb0374ef3015b66c42558eca6f1085cbd83468", 1),
    ("a303ab237d22d2ae55d1df656cd963698152937dc7d122f87f5896eb7c7ae561",
     "5bbb04846c3e984af3f8ed54c2c39f874adddfe892e9bb311d602c2744c378fe", 1),
    ("56e3800749e7c6ba7c791db349a5a11d81f4e293ba8d983c15b858a6f51e6616",
     "b0a30a2bd4540593f6513bf2ba4f9d5141f1845e68c006cb1684e583f7c80057", 1),
    ("6ed44a37f0b7c495c01ef24fdb91cd469da2fbe5323c81e18db1a6355ce962c4",
     "70c3ef9ae11b849c0826022463ccde4bd311554743aa318f2cfe8749d5c40878", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-expected-pair-model-contract-repair", 1),',
     '("a72-isolation-held-result-contract-repair", "a72-cpu9-same-boot-successor", 1),', 1),
    (".derived-collect-a72-expected-pair-model-contract-inner.XXXXXXXX",
     ".derived-collect-a72-cpu9-inner.XXXXXXXX", 1),
    ("expected-pair model-contract collector derivation",
     "CPU9 same-boot collector derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 collector derivation: expected {count}, "
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
