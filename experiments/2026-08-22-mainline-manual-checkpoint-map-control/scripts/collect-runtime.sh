#!/usr/bin/env bash

# Source-pin the proven prefix-control observer and specialize it for one
# unique mapping-model result plus bounded changed-ID Gemian retained recovery.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=14e9a974f1e3477ea318705926b77d66b6549896604ec8775cf2cedeaf78427c

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-21-mainline-manual-checkpoint-prefix-control/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector identity changed'

derived="$(mktemp "$script_dir/.derived-manual-checkpoint-map-collector.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("one exact prefix reason and serviceability pass",
     "one exact mapping-model result and serviceability pass", 1),
    ("2c96d3b6a096b68bb18522fc35b7550f593d6e541c6ab33d7029810c4fec35dd",
     "c9ee55ddc6f558f734e5400e8e689004b6767869fcbd2da3b474465cf69d7acf", 1),
    ("a4d88ba70410ab53529d1d74f5f342a6bb082043cd15a9f936426f9482c6dd48",
     "04ee5557c5b06b0c0a2f8598fd602b9803039678a1c8831d0ccb28a2d1fe15a9", 1),
    ("1f2f886225240b5cb738784cd88ed0499f0b97121830a3a8fc8468afddb7899a",
     "83f249449fc52741e4e5d09a10957b2345b6794968e93e654d766a7b23f54b10", 1),
    ("ced1f56fc56833ce47b63a98205a373276f5d666007190ec0d3bd5adb98f3901",
     "dd513384c78ee8378e1e4bf515f89b99ca87ed6ed86c1d38ec37f8aadd693b5b", 1),
    ("manual-checkpoint-prefix-control-attempt-1",
     "manual-checkpoint-map-control-attempt-1", 1),
    ("manual-checkpoint-prefix-control", "manual-checkpoint-map-control", 1),
    ("__MANUAL_CHECKPOINT_PREFIX_RUNTIME_BEGIN__",
     "__MANUAL_CHECKPOINT_MAP_RUNTIME_BEGIN__", 1),
    ("__MANUAL_CHECKPOINT_PREFIX_RUNTIME_END__",
     "__MANUAL_CHECKPOINT_MAP_RUNTIME_END__", 1),
    ("manual-checkpoint-prefix-pass", "manual-checkpoint-map-pass", 1),
    (".derived-manual-checkpoint-prefix-collector.XXXXXXXX",
     ".derived-manual-checkpoint-map-collector-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe map collector derivation: expected {count}, found {actual}: {old}"
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
