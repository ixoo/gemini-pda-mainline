#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Retarget the pinned installer and add verified block identity at every gate.
set -euo pipefail
export LC_ALL=C PYTHONDONTWRITEBYTECODE=1
umask 077
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer=$repo/experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/install-boot2.sh
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == deaa0e886a881132dd49ee1e3d5b0e6f776400f51fa86a8d0b7c791e979d12a8 ]]
derived=$(mktemp "$script_dir/.derived-v4-install.XXXXXXXX")
trap 'rm -f -- "$derived"' EXIT HUP INT TERM
python3 - "$source_installer" "$derived" "$script_dir" "$repo/scripts/boot2-device-guard.sh" <<'PY'
from pathlib import Path
import sys
sys.path.insert(0,sys.argv[3])
from v4_installer_guard import derive
s=Path(sys.argv[1]).read_text()
for old,new,count in (
 ('ea603c1b1a64d4f1aa9cac3e53957a3e858a7ce04127f1aef36d4b0e8173cb02','b007af3d7025b804b34c6f1e717b2eca5e9fecf09b0ff731cede2a12116d993c',1),
 ('ad92d496dfb4fd183c35e6e0f32ce626b2045528657fb2567d8561dd02540f1a','dca4bb9e13601552a9e0b2da24a0b14f74959586a13b15d0281ac4225196fde9',1),
 ('gemian-runtime-provenance-observer-rndis-1d303dda10b4','candidate-v4-ba906730',1),
 ('2026-08-14-mt6797-runtime-provenance-observer','2026-09-04-mt6797-thermal-snapshot',1),
 ('provenance-observer','thermal-snapshot',7),
):
 if s.count(old)!=count:raise ValueError('installer source anchor changed: '+old)
 s=s.replace(old,new)
guard=Path(sys.argv[4])
if guard.is_symlink() or not guard.is_file():raise ValueError('unsafe guard source')
Path(sys.argv[2]).write_text(derive(s,guard.read_bytes()))
PY
bash -n "$derived"
shellcheck "$derived"
if [[ ${1:-} == --validate-only && $# == 1 ]]; then
    printf 'installer_derivation=pass\n'
    exit 0
fi
[[ ${1:-} == --execute ]] || { printf 'Explicit --execute or --validate-only required\n' >&2; exit 2; }
shift
python3 "$script_dir/validate-v4-candidate.py" --candidate "$repo/artifacts/thermal-snapshot-composition/candidate-v4-ba906730" >/dev/null
/bin/bash "$derived" "$@"
