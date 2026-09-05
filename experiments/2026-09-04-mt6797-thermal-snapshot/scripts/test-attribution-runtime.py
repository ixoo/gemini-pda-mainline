#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generated-shell and complete transcript rejection fixtures; no device access."""
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
builder=load('builder',HERE/'build-attribution-runtime.py')
classifier=load('classifier',HERE/'classify-attribution-runtime.py')
parent=load('parent_fixture',ROOT/'experiments/2026-09-04-mt6797-a72-frequency-observation/scripts/test-production-runtime.py')
BOOT=parent.BOOT_ID

def record(n,maximum):
    values=[maximum-600+i*100 for i in range(7)]
    return (f'abi=1 attempt={n} error=0 complete=1 count=7 valid_mask=127 winner=6 maximum={maximum} start_ns={n*100} end_ns={n*100+9}\n'+
            ''.join(f'slot={i} bank={b} sensor={s} temperature={v} valid=1\n' for i,(b,s,v) in enumerate(zip((0,1,2,2,3,4,5),(0,3,1,2,1,1,1),values))))

def capture(last=36500):
    raw=parent.passing_capture().replace(parent.CURRENT_RELEASE,builder.RELEASE)
    for n,(stage,value) in enumerate(zip(('before','during','after'),(36000,37000,last)),1):
        raw=re.sub(r'thermal_'+stage+r'_millicelsius=[0-9]+\n',
                   f'__THERMAL_ATTRIBUTION_{stage}_BEGIN__\n'+record(n,value)+f'__THERMAL_ATTRIBUTION_{stage}_END__\nthermal_{stage}_millicelsius={value}\nsnapshot_{stage}_attempt={n}\n',raw)
    return raw.replace('__GEMINI_A72_CONCURRENT_MULTILINE_END__','owned_workers_reaped=yes\ncancellation_file=absent\nsnapshot_final_attempts=3\n__GEMINI_A72_CONCURRENT_MULTILINE_END__')

program=builder.build(BOOT)
assert program.count('cat "$SNAPSHOT"')==1
assert 'cat "$THERMAL_ZONE/temp"' not in program
assert 'ROUNDS=4\nSPIN_LIMIT=1000000\n' in program
assert program.index('snapshot-not-pristine')<program.index('mount -o remount,rw /sys')
assert program.index('attribution_observe before')<program.index('spawn_in_progress=1')<program.index('attribution_observe during')<program.index('touch "$START_WRITE"')<program.index('attribution_observe after')
assert program.count('spawn_in_progress=1\n')==4 and program.count('pending_exit" = 0')==4
assert '/dev/mmcblk' not in program and 'poweroff' not in program
for boot in builder.FORBIDDEN_BOOTS:
    try:builder.build(boot)
    except ValueError:pass
    else:raise AssertionError('consumed boot')
valid=capture()
assert classifier.classify(valid,BOOT,35000)['classification']=='bounded-attribution-pass'
rejected=classifier.classify(capture(41300),BOOT,35000)
assert rejected['classification']=='bounded-attribution-thermal-rejected' and len(rejected['thermal']['slots'])==7
mutations=[valid.replace('owned_workers_reaped=yes','owned_workers_reaped=no'),
           valid.replace('cancellation_file=absent','cancellation_file=present'),
           valid.replace('snapshot_final_attempts=3','snapshot_final_attempts=4'),
           valid.replace('snapshot_during_attempt=2','snapshot_during_attempt=1'),
           valid.replace('thermal_after_millicelsius=36500','thermal_after_millicelsius=36400'),
           valid.replace('valid_mask=127','valid_mask=126',1),
           valid.replace('winner=6','winner=0',1),
           valid.replace('writer8_alive_after_observation=1','writer8_alive_after_observation=0'),
           valid.replace('reader9_status=0','reader9_status=1'),
           valid.replace('concurrent_result=pass','concurrent_result=fail'),
           valid.replace('cleanup_file8=absent','cleanup_file8=present'),
           valid.replace('kernel_release='+builder.RELEASE,'kernel_release=wrong',1),
           valid+'snapshot_final_attempts=3\n',
           valid.replace('__THERMAL_ATTRIBUTION_before_END__','__THERMAL_ATTRIBUTION_during_END__',1)]
for mutation in mutations:
    try:classifier.classify(mutation,BOOT,35000)
    except ValueError:pass
    else:raise AssertionError('bad combined transcript admitted')
with tempfile.TemporaryDirectory(prefix='gemini-attribution-fixtures-',dir='/tmp') as tmp:
    root=Path(tmp);path=root/'program.sh';path.write_text(program)
    subprocess.run(['bash','-n',str(path)],check=True)
    subprocess.run(['shellcheck',str(path)],check=True)
    for transcript,expected in ((valid,0),(capture(41300),3),(mutations[0],1)):
        capture_path=root/'capture.txt';capture_path.write_text(transcript)
        outcome=subprocess.run([sys.executable,str(HERE/'classify-attribution-runtime.py'),str(capture_path),'--boot-id',BOOT,'--initial','35000'],capture_output=True,text=True)
        assert outcome.returncode==expected
    # The actual observer fragment uses a file adapter instead of consuming sysfs.
    adapter=root/'bb'
    adapter.write_text('''#!/bin/sh
if [ "$1" = cat ] && [ "$2" = "$SNAPSHOT" ]; then
 printf 'read\\n' >> "$COUNT"
 printf 'abi=1 attempts=%s limit=3\\n' "$NEXT" > "${SNAPSHOT}_status"
fi
exec "$@"
''');adapter.chmod(0o700)
    fragment=(HERE/'attribution-observer.sh').read_text()
    cases=[('before',1,'valid'),('during',2,'valid'),('after',3,'valid'),
           ('before',1,'hot'),('before',1,'mask'),('before',1,'winner'),
           ('before',1,'truncated'),('before',1,'stale'),('during',2,'bad-after')]
    for label,n,kind in cases:
        snapshot=root/'snapshot';count=root/'count';count.write_text('')
        data=record(n,59000 if kind=='hot' else 35000)
        if kind=='mask':data=data.replace('valid_mask=127','valid_mask=126')
        if kind=='winner':data=data.replace('winner=6','winner=0')
        if kind=='truncated':data=data[:100]
        snapshot.write_text(data)
        Path(str(snapshot)+'_status').write_text(f'abi=1 attempts={3 if kind=="stale" else n-1} limit=3\n')
        freq=root/'frequency';freq.write_text('fixture-frequency\n')
        harness=f'''#!/bin/sh
BB={adapter}
SNAPSHOT={snapshot}
FREQUENCY_OBSERVER={freq}
COUNT={count}
NEXT={n+1 if kind=='bad-after' else n}
export SNAPSHOT COUNT NEXT
frequency_reject() {{ printf 'refused=%s\\n' "$1"; exit 3; }}
{fragment}
attribution_observe {label}
'''
        outcome=subprocess.run(['sh'],input=harness,text=True,capture_output=True)
        assert outcome.returncode==(0 if kind=='valid' else 3),(kind,outcome.stderr)
        assert len(count.read_text().splitlines())==(0 if kind=='stale' else 1)
print('materialized_shell=pass combined_positive=1 thermal_rejection_retained=1 combined_mutations_rejected=14 classifier_cli_exit_cases=3 observer_fragment_cases=9 consumed_boot_refusals=3 device_action=none')
