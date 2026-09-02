#!/usr/bin/env bash

# Bind the reviewed device-side probe to exactly one mainline boot ID.
set -euo pipefail
export LC_ALL=C

readonly TEMPLATE_SHA256=d1b5f4d9046639e61785d6bebcd598f67ab07feb6dcb82d2a49f8ab41eee5738
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 2 && $1 == --boot-id ]] || die "usage: $0 --boot-id UUID"
boot_id=$2
[[ "$boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || die 'boot ID is malformed'
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
template="$script_dir/device-bounded-ram-coherency.sh"
[[ -f "$template" && ! -L "$template" ]] || die 'device probe template is absent or unsafe'
[[ "$(sha256sum "$template" | awk '{print $1}')" == "$TEMPLATE_SHA256" ]] || die 'device probe template changed'

python3 - "$template" "$boot_id" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
marker = "__EXPECTED_BOOT_ID__"
if text.count(marker) != 1:
    raise SystemExit("unsafe device-probe materialization")
sys.stdout.write(text.replace(marker, sys.argv[2]))
PY
