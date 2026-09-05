#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Frozen one-shot cycle preparation and bounded attribution over direct USB."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CAPTURE_ROOT=ROOT/'artifacts/runtime-captures'
CYCLE=CAPTURE_ROOT/'thermal-snapshot-attribution-cycle-1'
RUN=CAPTURE_ROOT/'thermal-snapshot-workload-attribution-1'
DEPLOYMENT=ROOT/'artifacts/device-install-evidence/thermal-snapshot-deployment-1/deployment-summary.txt'
DEPLOYMENT_SHA='6f47eef465c9461536d6a72b5acd3c80d776ca4446ebf3f82bfecadea40eb945'
SOURCE_BOOT='ac3d28c7-69fe-4ccb-8145-cad85cbd0653'
PINS={'run-observation.py': '6f87d631cab6626d8ffe54c008ac327b515cf79a46b98117a6d4c72d2b8e11e1', 'observation_protocol.py': 'ac8067307a46bc80478697bd30dddab78459f298a408b4de48dd8fd649a7bf6c', 'observation_state.py': '217b176e5825cfb1423a51b0b4b99a443b5d00d3a7149ad7c9f7e06c77c628dc', 'thermal_snapshot_records.py': '3d16447c3a213c658814a27795d6964d2c21c99424806aa51bd582f78e90da74', 'remote-observation-state.sh': 'bada6f961efaf2ee3be8d43647942143381ecfadb0b00f4be329d8fd5ad5c9ae', 'remote-attribution-shutdown.sh': '1b436728ecc0fb8d02033a5058b3072cea92f0260d0346f24723916d2f6e4471', 'build-attribution-runtime.py': 'ab9d08ec8307e249d4ca45840ff7c31377136a07d51d62aa3a3d4d227fd6fe84', 'workload_cleanup.py': '9fc538e384d1d37e498b9599232d7900a50dd87cc6cf61e38033c83930b2824e', 'attribution-observer.sh': '22e4414c325070d037a5d933e070042492b91344be39b941c5b71458114a02d9', 'classify-attribution-runtime.py': '9de00f9fa3c80c9d52200313d6bbc8df86d875ce1b8adf7888418014275f765b', 'assess-workload-thermal.py': '2618bfc9d419b2e61b4f017e7fe3aff6b6bf2d9d81d2e644dd6e0abb9620a031'}


def module(name):
    spec=importlib.util.spec_from_file_location(name.replace('-','_'),HERE/(name+'.py'))
    out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out


def sources():
    if not PINS:raise ValueError('protocol is not frozen')
    for name,sha in PINS.items():
        path=HERE/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
            raise ValueError('protocol source changed: '+name)


def unique_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('duplicate JSON field')
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs)


def shutdown_fields():
    return {'source_boot_id':SOURCE_BOOT,'kernel_release':'7.1.3-gemini-thermal-snapshot',
            'record_identity':'7d67a19b3ae40ae1521293d7ffc834e6d06ae14a2d55de693ee9c815bdaee552',
            'cpu_online':'0-7','cpu_offline':'8-9','snapshot_attempts':'3','frequency_attempts':'0',
            'lifecycle':'unchanged-pristine','block_mounts':'0','shutdown_requested':'yes'}


def cycle_expected():
    return shutdown_fields() | {'protocol':'thermal-snapshot-workload-attribution-1',
        'candidate_sha256':'666961b636b21b8598a64999e9dbf72af280ad99f07a6b745045320f24ca361b',
        'deployment_receipt_sha256':DEPLOYMENT_SHA,'post_shutdown_reachability':'unreachable','reboot_requested':'no'}


def validate_cycle(raw):
    data=unique_json(raw)
    if data!=cycle_expected():raise ValueError('cycle receipt incomplete or changed')
    return data


def read_cycle():
    required={'deployment-summary.txt','shutdown.requested','transport-1.txt','transport-1-meta.json','cycle-receipt.json','classification.json'}
    if CYCLE.is_symlink() or not CYCLE.is_dir() or CYCLE.stat().st_mode & 0o777!=0o700:
        raise ValueError('unsafe cycle capture')
    manifest=CYCLE/'SHA256SUMS'
    if manifest.is_symlink():raise ValueError('unsafe cycle manifest')
    entries={}
    for line in manifest.read_text().splitlines():
        sha,sep,name=line.partition('  ')
        if not sep or name not in required or name in entries:raise ValueError('cycle manifest inventory')
        entries[name]=sha
    if entries.keys()!=required:raise ValueError('incomplete cycle manifest')
    for name,sha in entries.items():
        path=CYCLE/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('cycle evidence changed')
    if entries['deployment-summary.txt']!=DEPLOYMENT_SHA or (CYCLE/'shutdown.requested').read_text()!='requested=yes\n':
        raise ValueError('cycle deployment or request seal changed')
    raw=(CYCLE/'cycle-receipt.json').read_text();data=validate_cycle(raw)
    if unique_json((CYCLE/'classification.json').read_text())!=data:raise ValueError('cycle classification disagrees')
    validate_shutdown_frame((CYCLE/'transport-1.txt').read_text())
    return raw


def validate_shutdown_frame(raw):
    state=module('observation_state')
    text=state.bounded(raw.replace('\r\n','\n'),'__THERMAL_ATTRIBUTION_SHUTDOWN_BEGIN__','__THERMAL_ATTRIBUTION_SHUTDOWN_END__')
    fields={}
    for line in text.splitlines():
        key,sep,value=line.partition('=')
        if not sep or key in fields:raise ValueError('shutdown frame shape')
        fields[key]=value
    if fields!=shutdown_fields():raise ValueError('shutdown frame identity')


def frame(raw):
    state=module('observation_state')
    data=state.bounded(raw.replace('\r\n','\n'),state.BEGIN,state.END)
    late=state.bounded(data,state.LATE_BEGIN,state.LATE_END)
    data=data.replace(state.LATE_BEGIN+'\n'+late+state.LATE_END+'\n','')
    values={}
    for line in data.splitlines():
        key,sep,value=line.partition('=')
        if not sep or key in values:raise ValueError('state duplicate or malformed field')
        values[key]=value
    return values,late


def postflight(raw,pre,late,terminal):
    values,post_late=frame(raw)
    temperature=values.get('thermal_temperature_millicelsius','')
    if not temperature.isascii() or not temperature.isdecimal() or not 0<=int(temperature)<=58500 or str(int(temperature))!=temperature:
        raise ValueError('postflight thermal refusal')
    expected=pre | {'cpu_online':'0-9','cpu_offline':'','frequency_log_count':'3','live_status':terminal,
                    'thermal_snapshot_status':'abi=1 attempts=3 limit=3','thermal_temperature_millicelsius':temperature}
    if values!=expected or post_late!=late:raise ValueError('postflight identity/accounting drift')


class Capture:
    def __init__(self,path,link):
        self.path=path;self.link=link;self.sessions=0
        if path.parent.is_symlink() or not path.parent.is_dir() or path.parent.stat().st_mode & 0o777!=0o700:
            raise ValueError('unsafe capture root')
        subprocess.run(['git','-C',str(ROOT),'check-ignore','-q',str(path)],check=True)
        path.mkdir(mode=0o700)
        self.sync(path.parent)
    @staticmethod
    def sync(path):
        fd=os.open(path,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    def save(self,name,data):
        module('run-observation').durable(self.path/name,data)
    def seal(self,name):
        self.save(name,'requested=yes\n');self.sync(self.path)
    def transport(self,script,workload=False,shutdown=False):
        self.sessions+=1
        marker='__THERMAL_ATTRIBUTION_HOST_SCRIPT__'
        if marker in script:raise ValueError('heredoc collision')
        command=f"/bin/busybox sh <<'{marker}'\n{script}\n{marker}\nexit\n"
        idle,outer=(120,125) if workload else (15,20)
        args=['nc','-4','-b',self.link,'-s','10.15.19.1','-G','5','-w',str(idle),'10.15.19.82','2323']
        try:result=subprocess.run(args,input=command.encode(),capture_output=True,timeout=outer)
        except subprocess.TimeoutExpired as error:
            raw=(error.stdout or b'').decode('utf-8','replace')
            self.save(f'transport-{self.sessions}.txt',raw)
            self.save(f'transport-{self.sessions}-meta.json',json.dumps({'timeout':True,'returncode':None})+'\n')
            if shutdown:return raw
            raise ValueError('transport timeout; no retry') from error
        raw=result.stdout.decode('utf-8','replace')
        self.save(f'transport-{self.sessions}.txt',raw)
        self.save(f'transport-{self.sessions}-meta.json',json.dumps({'timeout':False,'returncode':result.returncode})+'\n')
        if result.returncode and not shutdown:raise ValueError('transport failure; no retry')
        return raw
    def finish(self):
        entries=sorted(p for p in self.path.iterdir() if p.is_file())
        self.save('SHA256SUMS',''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in entries))


def workload(capture,deployment,cycle):
    protocol=module('observation_protocol');state=module('observation_state')
    classifier=module('classify-attribution-runtime');builder=module('build-attribution-runtime')
    validate_cycle(cycle)
    deployment_boot=protocol.receipt(deployment)
    raw=capture.transport((HERE/'remote-observation-state.sh').read_text())
    capture.save('preflight.txt',raw)
    pre=state.validate_state(raw,record_identity=protocol.RECORD,deployment_boot=deployment_boot)
    if pre['boot_id'] in builder.FORBIDDEN_BOOTS | {SOURCE_BOOT}:raise ValueError('consumed boot identity')
    if pre['thermal_snapshot_path']!=protocol.PATH:raise ValueError('thermal device path changed')
    _,late=frame(raw)
    program=builder.build(pre['boot_id']);capture.save('program.sh',program)
    capture.seal('workload.requested')
    raw=capture.transport(program,workload=True);capture.save('runtime.txt',raw)
    result=classifier.classify(raw,pre['boot_id'],int(pre['thermal_temperature_millicelsius']))
    capture.save('runtime-classification.json',json.dumps(result,indent=2,sort_keys=True)+'\n')
    # A structurally complete thermal refusal still gets the single declared final
    # accounting frame. An incomplete runtime gets no further device request.
    terminal=classifier.scalar(raw,'post_status')
    post=capture.transport((HERE/'remote-observation-state.sh').read_text());capture.save('postflight.txt',post)
    postflight(post,pre,late,terminal)
    result.update({'postflight':'pass','transport_sessions':capture.sessions,'ordinary_thermal_reads':2,
                   'workload_requests':1,'retries':0,'candidate_sha256':protocol.CANDIDATE})
    return result


def prepare_cycle(capture):
    raw=capture.transport((HERE/'remote-attribution-shutdown.sh').read_text(),shutdown=True)
    validate_shutdown_frame(raw)
    failures=0
    for _ in range(10):
        probe=subprocess.run(['nc','-z','-4','-b',capture.link,'-s','10.15.19.1','-G','2','-w','2','10.15.19.82','2323'],capture_output=True,timeout=4)
        failures=failures+1 if probe.returncode else 0
        if failures==2:
            result=cycle_expected();capture.save('cycle-receipt.json',json.dumps(result,indent=2,sort_keys=True)+'\n');return result
        time.sleep(2)
    raise ValueError('shutdown reachability did not disappear; no retry')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('prepare-cycle','run'))
    p.add_argument('--execute',action='store_true')
    a=p.parse_args();sources()
    deployment=DEPLOYMENT.read_text()
    if DEPLOYMENT.is_symlink() or hashlib.sha256(deployment.encode()).hexdigest()!=DEPLOYMENT_SHA:
        raise ValueError('exact deployment receipt changed')
    module('observation_protocol').receipt(deployment)
    cycle=''
    if a.mode=='run':
        cycle=read_cycle()
    if not a.execute:print('protocol=frozen receipts=pass device_action=none');return 0
    link=module('run-observation').interface()
    capture=Capture(CYCLE if a.mode=='prepare-cycle' else RUN,link)
    try:
        capture.save('deployment-summary.txt',deployment)
        if a.mode=='run':capture.save('cycle-receipt.json',cycle)
        else:capture.seal('shutdown.requested')
        result=prepare_cycle(capture) if a.mode=='prepare-cycle' else workload(capture,deployment,cycle)
        capture.save('classification.json',json.dumps(result,indent=2,sort_keys=True)+'\n')
    except BaseException as error:
        capture.save('classification.json',json.dumps({'classification':'refused-or-incomplete','reason':str(error),'retry':'forbidden','transport_sessions':capture.sessions})+'\n')
        raise
    finally:capture.finish()
    print('classification='+result.get('classification','cycle-prepared'))
    return 3 if result.get('classification')=='bounded-attribution-thermal-rejected' else 0

if __name__=='__main__':raise SystemExit(main())
