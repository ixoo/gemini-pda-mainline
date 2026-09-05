#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Materialize the prospective attribution program offline; no device transport."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
from workload_cleanup import replace_exact

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BUILDER=ROOT/'experiments/2026-09-04-mt6797-a72-frequency-observation/scripts/build-production-runtime.sh'
BUILDER_SHA='241854bde76396d2713a7cc5a75ea53f7e56fa1b143a3a2278c3b7f64fff52eb'
CLEANUP_SHA='209a24a3215603ae614a37625c559738f093d9f35915a86bda3b4dee4c07d452'
OBSERVER_SHA='22e4414c325070d037a5d933e070042492b91344be39b941c5b71458114a02d9'
RECORD='7d67a19b3ae40ae1521293d7ffc834e6d06ae14a2d55de693ee9c815bdaee552'
RELEASE='7.1.3-gemini-thermal-snapshot'
FORBIDDEN_BOOTS={'50e87880-b73a-46c2-9914-cabe34acff8c','1afc43e5-d4cd-4df6-a0e1-431eeef140df','ac3d28c7-69fe-4ccb-8145-cad85cbd0653'}
PRE=r'''SNAPSHOT=/sys/bus/platform/devices/1100b000.thermal/mt6797_temperature_snapshot
snapshot_count=0
for item in /sys/bus/platform/devices/*/mt6797_temperature_snapshot; do
	[ -r "$item" ] || continue
	snapshot_count=$((snapshot_count + 1))
done
# shellcheck disable=SC2015 # Both inventory checks must pass.
[ "$snapshot_count" = 1 ] && [ -r "$SNAPSHOT" ] || reject_preflight snapshot-inventory
[ "$($BB stat -c %a "$SNAPSHOT")" = 400 ] || reject_preflight snapshot-mode
[ "$($BB stat -c %a "${SNAPSHOT}_status")" = 400 ] || reject_preflight snapshot-status-mode
[ "$($BB cat "${SNAPSHOT}_status")" = 'abi=1 attempts=0 limit=3' ] || reject_preflight snapshot-not-pristine
[ "$($BB printf '%s\n' "$pre_status" | $BB sha256sum | $BB awk '{print $1}')" = 6a5fd459cd5b7ed4e309dd4942e116428980f6229c9ee434240c4c70396d43eb ] || reject_preflight full-lifecycle-state
[ "$($BB dmesg | $BB grep -Fc GEMINI_A72_FREQUENCY_OBSERVATION_V1)" = 0 ] || reject_preflight frequency-not-pristine
'''


def checked(path,sha):
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
        raise ValueError('source identity changed: '+path.name)
    return path.read_text()


def build(boot):
    if not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',boot) or boot in FORBIDDEN_BOOTS:
        raise ValueError('invalid or consumed boot identity')
    source=checked(BUILDER,BUILDER_SHA)
    checked(HERE/'workload_cleanup.py',CLEANUP_SHA)
    source=replace_exact(source,'script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)',
                         'script_dir='+shlex.quote(str(HERE)))
    anchor='source = Path(sys.argv[1]).read_text(encoding="utf-8")\n'
    source=replace_exact(source,anchor,anchor+'sys.path.insert(0, '+repr(str(HERE))+')\nfrom workload_cleanup import transform\nsource = transform(source)\n')
    # The inherited builder matches both the release anchor and its replacement.
    source=replace_exact(source,'wait "$pid8"; writer8_status=$?',
                         'wait "$pid8"; writer8_status=$?; pid8=',2)
    with tempfile.TemporaryDirectory(prefix='gemini-attribution-build-',dir='/tmp') as tmp:
        env=os.environ | {'TMPDIR':tmp,'PYTHONDONTWRITEBYTECODE':'1'}
        out=subprocess.run(['bash','-s','--','--boot-id',boot],input=source,text=True,capture_output=True,check=True,env=env).stdout
    out=replace_exact(out,'7.1.3-gemini-a72-frequency-thermal',RELEASE)
    out=replace_exact(out,'d1e9f8c94a4369ca32c00643a0d2f92d5c0f91a43af236bf61a2409a2512a0a2',RECORD)
    out=replace_exact(out,'if ! $BB mount -o remount,rw /sys; then',PRE+'\nif ! $BB mount -o remount,rw /sys; then')
    out=replace_exact(out,'THERMAL_ZONE=none\n','')
    out=replace_exact(out,'\tTHERMAL_ZONE=$item\n','')
    begin=out.index('frequency_observe()\n')
    end=out.index("$BB printf '%s\\n' __A72_FREQUENCY_THERMAL_BEGIN__",begin)
    fragment=checked(HERE/'attribution-observer.sh',OBSERVER_SHA)
    out=out[:begin]+fragment+'\n'+out[end:]
    for label in ('before','during','after'):
        out=replace_exact(out,'frequency_observe '+label,'attribution_observe '+label)
    # A success receipt must not infer child quiescence from file absence alone.
    out=replace_exact(out,"$BB printf '%s\\n' concurrent_result=pass",'''[ -z "$pid8$pid9$reader_pid8$reader_pid9" ] || finish_failure unreaped-worker
[ ! -e "$CANCEL" ] || finish_failure cancellation-file-remained
[ "$($BB cat "${SNAPSHOT}_status")" = 'abi=1 attempts=3 limit=3' ] || finish_failure snapshot-final-accounting
$BB printf '%s\\n' owned_workers_reaped=yes cancellation_file=absent snapshot_final_attempts=3
$BB printf '%s\\n' concurrent_result=pass''')
    for guard in (
        '\t[ -r "$item/type" ] && [ -r "$item/temp" ] || continue',
        '[ "$writer8_alive_before_observation" = 1 ] && [ "$writer9_alive_before_observation" = 1 ] ||',
        '[ "$writer8_alive_after_observation" = 1 ] && [ "$writer9_alive_after_observation" = 1 ] ||',
    ):
        out=replace_exact(out,guard,'# shellcheck disable=SC2015 # Both checks are required.\n'+guard)
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--boot-id',required=True)
    print(build(p.parse_args().boot_id),end='')

if __name__=='__main__':main()
