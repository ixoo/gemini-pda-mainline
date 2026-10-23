#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Narrow measurement binding of retained custody; source cohort stays immutable."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

CANDIDATE_SHA = '8eb12232ddbb2a00027f926a2c72c5e8213a3dbffadf6269c10beeed6bdceab3'
BOOT2_SHA = '5f63e2d32fc0b921b4fc60d5a50baeb045d1155598ad4108fb0afe6629bfefdd'
ADAPTER_SHA = 'ff658dc6e4df8553d71239f3b56b79699cb4763647fe3890dd066821e3431eeb'


def candidate():
    path = Path(os.environ['TP_CANDIDATE']).resolve(strict=True)/'candidate.json'
    if hashlib.sha256(path.read_bytes()).hexdigest() != CANDIDATE_SHA:
        raise ValueError('measurement candidate receipt changed')
    value = json.loads(path.read_bytes())
    if value['files']['boot2-padded.img']['sha256'] != BOOT2_SHA or value['kernel_build_commit'] != '3da69187ec93fd15b28fda3fbdbf118c37ad55a5':
        raise ValueError('measurement is bound to the unchanged installed image')
    return path, value


def bind_host(host, root):
    """Replace only the owned helper and final measurement classifier."""
    plan = json.loads(Path(os.environ['TP_PLAN']).read_text())
    helper = Path(os.environ['TP_HELPER']).resolve(strict=True)
    if hashlib.sha256(helper.read_bytes()).hexdigest() != plan['helper_sha256']:
        raise ValueError('measurement helper changed after preparation')
    host.CCMP_CLASSIFIER = Path(os.environ['TP_CLASSIFIER'])
    host.THROUGHPUT_BINDING = (str(root), plan['helper_sha256'])
    ph = host.PH
    if ph.HELPER is not None:
        if ph.HELPER.record['started']:
            raise ValueError('measurement helper already started')
        def spawn(argv, **kwargs):
            if Path(argv[1]).name != 'laptop-wifi-ssh-retain.py':
                raise ValueError('unexpected owned-helper entry')
            return subprocess.Popen([argv[0],str(helper),*argv[2:]],**kwargs)
        ph.HELPER.spawn = spawn


def run_phase(phase, execute):
    cohort = Path(os.environ['TP_SOURCE_ROOT']).resolve(strict=True)
    original = runpy.run_path
    leaf = Path(os.environ['TP_REVIEWED_LEAF'])
    plan = json.loads(Path(os.environ['TP_PLAN']).read_text())
    if hashlib.sha256(leaf.read_bytes()).hexdigest() != plan['leaf_sha256']:
        raise ValueError('measurement leaf changed')
    receipt, value = candidate()

    def hooked(path, *args, **kwargs):
        path = Path(path)
        if path.name == 'deployment-authority.py':
            # A measurement-specific exact installed-image binding. This is
            # not an install receipt, archive search or permission to flash.
            return {'path':lambda:receipt, 'read':lambda:value}
        result = original(str(path), *args, **kwargs)
        if path.name == 'p2-evidence-successor.py':
            if hashlib.sha256(path.read_bytes()).hexdigest() != ADAPTER_SHA:
                raise ValueError('retained custody derivation changed')
            globals_ = result['client'].__globals__
            old_roots = globals_['fresh_roots']
            def roots(source):
                return old_roots(source).replace('session-ccmp-p2e','session-throughput-2').replace('capture-ccmp-p2e','capture-throughput-2')
            globals_['fresh_roots'] = roots
            old_host = result['host']
            def host(source, client_sha):
                source = old_host(source,client_sha)
                old = "reviewed = (HERE / 'join-ccmp-p2.sh').read_bytes()"
                if source.count(old) != 1:
                    raise ValueError('retained leaf binding anchor changed')
                source = source.replace(old,"reviewed = Path(os.environ['TP_REVIEWED_LEAF']).read_bytes()")
                source = source.replace('af39853a381879c6040044ac7d913942ae1304f979e6d25b5d859249ddd381a8',plan['leaf_sha256'])
                source = source.replace('import runpy\n','import runpy\nimport os\n_TP = runpy.run_path(os.environ["TP_ADAPTER"])\n',1)
                anchor = '    ph.run_without_scan = lambda candidate: no_scan(ph, candidate)'
                if source.count(anchor) != 1:
                    raise ValueError('retained host binding anchor changed')
                return source.replace(anchor,anchor+'\n    _TP["bind_host"](host, root)')
            result['host'] = host
        return result
    runpy.run_path = hooked
    try:
        script = cohort/'experiments/2026-10-13-mt6797-wifi-native-delivery-probe'/('laptop-'+phase+'-ccmp-p2e.py')
        sys.argv = [str(script),'--candidate',str(receipt.parent)] + (['--execute'] if execute else [])
        result = hooked(script)
        # Wrappers compile definitions without invoking main under run_path.
        if phase == 'session':
            host = result['GLOBALS']['NH']
            expected = (str(Path(os.environ['GEMINI_RUNTIME_ROOT'])/'ccmp-stable-monitor/session-throughput-2'),plan['helper_sha256'])
            if getattr(host,'THROUGHPUT_BINDING',None)!=expected or host.PH.ROOT!=host.ROOT:
                raise ValueError('measurement host/helper binding not applied to actual constructor')
        main = result['CAP'].main if phase == 'capture' else result['GLOBALS']['NH'].main
        if main is None:
            raise ValueError('retained phase lacks main')
        return main()
    finally:
        runpy.run_path = original


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=('capture','session'))
    p.add_argument('--execute',action='store_true')
    args = p.parse_args()
    raise SystemExit(run_phase(args.phase,args.execute))
