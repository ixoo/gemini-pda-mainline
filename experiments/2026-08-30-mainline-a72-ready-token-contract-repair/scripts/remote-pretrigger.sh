#!/usr/bin/env bash

# Source-pin the proven read-only identity probe and retarget only the exact
# installed READY-token repair candidate.
set -euo pipefail

readonly SOURCE_SHA256=5826658d983313d2ddb7b032dc80f8a7a3844076aaf346e36f852702e7cec010
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-30-mainline-a72-provenance-serviceability-composition/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
python3 - "$source_probe" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a"
new = "a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179"
if text.count(old) != 1:
    raise SystemExit("unsafe READY-contract pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
