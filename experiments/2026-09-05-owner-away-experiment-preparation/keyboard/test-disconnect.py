#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exact retained ARM64 Dropbear channel loss with a harmless monitor child.

Run inside a disposable PID namespace; no device endpoints or credentials.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import resource
import runpy
import shlex
import signal
import socket
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
PACKAGE_SHA = 'dfeb746505b7ad01423e91e952e76620f845b048ae2e8c5cf8a311e0d4443e60'
PACKAGE_REV = 'e9c028005b88ef8536ecb58c095e8d172253fa12'

def require(value, reason):
    if not value: raise ValueError(reason)

def main():
    parser=argparse.ArgumentParser()
    for name in ('package','compiler','qemu','work-root','output'):parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    # unshare --pid --fork makes this test PID 1, whose exit kills the namespace.
    require(os.getpid()==1, 'disposable PID namespace required')
    package=args.package.resolve(strict=True)
    runpy.run_path(str(HERE/'../baseline/scripts/buildbox_userspace.py'))['check_package'](package,PACKAGE_SHA,PACKAGE_REV)
    args.output.mkdir(mode=0o700,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='disconnect-',dir=args.work_root) as temporary:
        root=Path(temporary); case=root/'case';case.mkdir(mode=0o700)
        fixture=root/'fixture'
        subprocess.run([str(args.compiler),'-std=c11','-Os','-static','-Wall','-Wextra','-Werror',
            '-DMONITOR_FULL_DURATION','-DFIXTURE_ROOT='+json.dumps(str(root)),str(HERE/'monitor-fixture.c'),'-o',str(fixture)],check=True,capture_output=True,timeout=30)
        provision=runpy.run_path(str(HERE/'../baseline/scripts/provision.py'))
        keys=root/'keys';provision['generate'](keys)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        known=root/'known_hosts';public=(keys/'host.pub').read_text().split()
        known.write_text(f'[127.0.0.1]:{port} '+' '.join(public[:2])+'\n');known.chmod(0o600)
        def limits():resource.setrlimit(resource.RLIMIT_FSIZE,(131072,131072))
        server_command=[str(args.qemu),str(package/'dropbear'),'-F','-D',str(keys),'-r',str(keys/'dropbear_host_key'),
            '-p',f'127.0.0.1:{port}','-P',str(root/'server.pid'),'-I','60','-M','360','-T','2']
        server=subprocess.Popen(server_command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,preexec_fn=limits)
        client=None
        try:
            for _ in range(40):
                require(server.poll() is None,'server exited')
                try:
                    with socket.create_connection(('127.0.0.1',port),timeout=.1):break
                except OSError:time.sleep(.1)
            else:raise ValueError('loopback server unavailable')
            command=['ssh','-F','/dev/null','-T','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','IdentityAgent=none',
                '-o','StrictHostKeyChecking=yes','-o',f'UserKnownHostsFile={known}','-o','GlobalKnownHostsFile=/dev/null',
                '-o','ConnectTimeout=3','-o','ConnectionAttempts=1','-i',str(keys/'admin'),'-p',str(port),
                pwd.getpwuid(os.getuid()).pw_name+'@127.0.0.1',
                'exec '+shlex.join([str(args.qemu),str(fixture),str(case),'disconnect'])]
            with (root/'client.stdout').open('xb') as out,(root/'client.stderr').open('xb') as err:
                client=subprocess.Popen(command,stdout=out,stderr=err)
                deadline=time.monotonic()+5
                while b'fixture-progress\n' not in (root/'client.stdout').read_bytes():
                    require(time.monotonic()<deadline and client.poll() is None,'fixture startup failed')
                    time.sleep(.01)
                # Hold the client child identity through signal/reap; no reconnect.
                client.terminate();client.wait(timeout=3)
            deadline=time.monotonic()+8
            while not (case/'monitor.exit').exists() or (case/'monitor.exit').read_text() not in ('0\n','2\n'):
                require(time.monotonic()<deadline,'monitor did not independently return after channel loss')
                time.sleep(.01)
            status=dict(line.split('=',1) for line in (case/'keyboard-attempt/monitor.status').read_text().splitlines())
            outer=(case/'monitor.exit').read_text()
            require(outer=='2\n' and status['reaped']=='1' and status['identity_lost']=='0' and
                status['reason'] in ('cancelled','forward-close-or-stall') and status['late']=='0', 'disconnect did not preserve bounded failed lifecycle')
            retained=(case/'keyboard-attempt/observer.stdout').read_bytes()
            require(retained and not (case/'keyboard-attempt/observer.stderr').read_bytes(),'private fixture capture missing/diagnostic')
            for name in ('observer.stdout','observer.stderr','monitor.status'):
                (args.output/name).write_bytes((case/'keyboard-attempt'/name).read_bytes())
            (args.output/'monitor.exit').write_text(outer)
            result={'classification':'exact-dropbear-disconnect-private-capture-and-reap-pass',
                'server_package':PACKAGE_SHA,'server_revision':PACKAGE_REV,'server_sha256':hashlib.sha256((package/'dropbear').read_bytes()).hexdigest(),
                'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'fixture_source_sha256':hashlib.sha256((HERE/'monitor-fixture.c').read_bytes()).hexdigest(),
                'monitor_source_sha256':hashlib.sha256((HERE/'monitor.c').read_bytes()).hexdigest(),
                'client_exit':client.returncode,'monitor_exit':2,'monitor_status':status,'capture_bytes':len(retained),
                'server_idle_seconds':60,'server_maximum_seconds':360,'transport':'loopback no-PTY SSH; explicit client termination',
                'command_shell':'builder account shell','candidate_init':'not-tested','device_action':'none'}
            (args.output/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
            print(json.dumps(result,sort_keys=True))
        finally:
            if client is not None and client.poll() is None:
                client.kill();client.wait(timeout=3)
            if server.poll() is None:
                server.terminate()
                try:server.wait(timeout=3)
                except subprocess.TimeoutExpired:server.kill();server.wait(timeout=3)
            # Namespace PID 1 exit is the independent descendant containment.

if __name__=='__main__':main()
