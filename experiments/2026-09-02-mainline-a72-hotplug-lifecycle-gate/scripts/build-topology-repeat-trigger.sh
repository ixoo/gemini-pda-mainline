#!/usr/bin/env bash

# Materialize the one-shot topology-repeat trigger for one fresh boot ID.
set -euo pipefail
export LC_ALL=C

readonly SOURCE_SHA256=3f728363bd18ebf0f5dac4950e62c1b218bdd15303ed9d37ed3f4b4a2325ddda
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 2 && $1 == --boot-id ]] || die "usage: $0 --boot-id UUID"
boot_id=$2
[[ "$boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || die 'boot ID is malformed'
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_trigger="$script_dir/remote-topology-repeat-trigger.sh"
[[ -f "$source_trigger" && ! -L "$source_trigger" ]] || die 'remote trigger template is missing or unsafe'
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'remote trigger template changed'

python3 - "$source_trigger" "$boot_id" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
placeholder = "EXPECTED_BOOT_ID=__EXPECTED_BOOT_ID__"
if text.count(placeholder) != 1:
    raise SystemExit("remote trigger boot-ID placeholder changed")
sys.stdout.write(text.replace(placeholder, f"EXPECTED_BOOT_ID={sys.argv[2]}"))
PY
