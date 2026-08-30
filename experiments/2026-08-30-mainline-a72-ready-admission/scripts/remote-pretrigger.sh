#!/usr/bin/env bash

# Source-pin the last qualified admission probe and retarget only the installed
# full-partition identity to the READY-bound candidate.
set -euo pipefail

readonly SOURCE_SHA256=d7a32a17362a92712a164d87f36c240c4af8e0261a90c43b41d3763131f93cc2
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-28-mainline-a72-admission-atag-one-shot/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
python3 - "$source_probe" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0"
new = "8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7"
if text.count(old) != 1:
    raise SystemExit("unsafe READY pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
