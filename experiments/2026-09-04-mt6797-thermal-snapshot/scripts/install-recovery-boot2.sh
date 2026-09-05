#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Bind the source-pinned installer to the observed Gemian recovery-cycle boot.
set -euo pipefail
export LC_ALL=C PYTHONDONTWRITEBYTECODE=1
umask 077
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer=$repo/experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/install-boot2.sh
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == deaa0e886a881132dd49ee1e3d5b0e6f776400f51fa86a8d0b7c791e979d12a8 ]]
derived=$(mktemp "$script_dir/.derived-recovery-install.XXXXXXXX")
trap 'rm -f -- "$derived"' EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text()
for old,new,count in (
 ('ea603c1b1a64d4f1aa9cac3e53957a3e858a7ce04127f1aef36d4b0e8173cb02','666961b636b21b8598a64999e9dbf72af280ad99f07a6b745045320f24ca361b',1),
 ('ad92d496dfb4fd183c35e6e0f32ce626b2045528657fb2567d8561dd02540f1a','64106b9d1e3112de94b2c8225915897293fa4657817cc1e78dbe0d4914ca050b',1),
 ('gemian-runtime-provenance-observer-rndis-1d303dda10b4','candidate-c2ddeea9',1),
 ('2026-08-14-mt6797-runtime-provenance-observer','2026-09-04-mt6797-thermal-snapshot',1),
 ('provenance-observer','thermal-snapshot',7),
 ('[[ "$initial_boot_id" =~ ^[0-9a-f-]{36}$ ]] || die \'malformed initial boot ID\'',
  '[[ "$initial_boot_id" == 5d45171e-6c70-4fe4-99b6-715ac22ca826 ]] || die \'recovery source boot changed\'',1),
):
 if s.count(old)!=count:raise ValueError('installer source anchor changed: '+old)
 s=s.replace(old,new)
Path(sys.argv[2]).write_text(s)
PY
bash -n "$derived"
shellcheck "$derived"
if [[ ${1:-} == --validate-only && $# == 1 ]]; then
    printf 'installer_derivation=pass\n'
    exit 0
fi
[[ ${1:-} == --execute ]] || { printf 'Explicit --execute or --validate-only required\n' >&2; exit 2; }
shift
python3 "$script_dir/validate-candidate.py" --candidate "$repo/artifacts/thermal-snapshot-composition/candidate-c2ddeea9" >/dev/null
/bin/bash "$derived" "$@"
