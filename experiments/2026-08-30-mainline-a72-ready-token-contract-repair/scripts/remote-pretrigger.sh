#!/usr/bin/env bash

# Source-pin the complete read-only READY frame probe and retarget only the
# exact installed READY-token repair candidate.
set -euo pipefail

readonly SOURCE_SHA256=d1dac5b8b0e75460dec80480886008763f63fed96b1124793e2d3539820212f3
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-30-mainline-a72-cpu8-ready-one-shot/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
python3 - "$source_probe" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "2245c1c4056cfd849ff89ba8afa220bf0cf038f1ea23a324c1e717c6ea23d89b"
new = "a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179"
if text.count(old) != 1:
    raise SystemExit("unsafe READY-contract pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
