#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run offline fixtures with the exact candidate BusyBox under user-mode QEMU."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
INITRAMFS_SHA='e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f'
BUSYBOX_SHA='52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933'


def extract_busybox(raw):
    if hashlib.sha256(raw).hexdigest()!=INITRAMFS_SHA:raise ValueError('candidate initramfs changed')
    data=gzip.decompress(raw);offset=0;found=[]
    while offset+110<=len(data):
        header=data[offset:offset+110]
        if header[:6] not in (b'070701',b'070702'):raise ValueError('cpio format')
        size=int(header[54:62],16);namesize=int(header[94:102],16)
        if not 1<=namesize<=4096:raise ValueError('cpio name length')
        name_start=offset+110;name_end=name_start+namesize
        if name_end>len(data) or data[name_end-1]!=0:raise ValueError('cpio name framing')
        name=data[name_start:name_end-1].decode('ascii')
        start=(name_end+3)&~3;end=start+size
        if end>len(data):raise ValueError('cpio body framing')
        if name in ('bin/busybox','./bin/busybox'):found.append(data[start:end])
        if name=='TRAILER!!!':break
        offset=(end+3)&~3
    if len(found)!=1 or hashlib.sha256(found[0]).hexdigest()!=BUSYBOX_SHA:
        raise ValueError('exact candidate BusyBox identity')
    if len(found[0])!=1914704 or found[0][:5]!=b'\x7fELF\x02' or found[0][18:20]!=b'\xb7\x00':
        raise ValueError('expected AArch64 ELF')
    return found[0]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--suite',choices=('attribution','recovery','gemian-recovery'),default='attribution')
    p.add_argument('--initramfs',type=Path,required=True)
    p.add_argument('--work-root',type=Path,required=True)
    p.add_argument('--expected-revision',required=True)
    a=p.parse_args()
    revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    if revision!=a.expected_revision:raise ValueError('test revision mismatch')
    if subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip():raise ValueError('test checkout is dirty')
    if not a.work_root.is_dir() or a.work_root.is_symlink():raise ValueError('unsafe managed work root')
    if a.initramfs.is_symlink():raise ValueError('unsafe input')
    qemu=shutil.which('qemu-aarch64-static')
    if not qemu:raise ValueError('user-mode AArch64 emulator missing; no native fallback')
    binary=extract_busybox(a.initramfs.read_bytes())
    with tempfile.TemporaryDirectory(prefix='gemini-candidate-shell-',dir=a.work_root) as temporary:
        root=Path(temporary);busybox=root/'busybox';busybox.write_bytes(binary);busybox.chmod(0o700)
        wrapper=root/'candidate-busybox';wrapper.write_text('#!/bin/sh\nexec '+shlex.quote(qemu)+' '+shlex.quote(str(busybox))+' "$@"\n');wrapper.chmod(0o700)
        identity=subprocess.run([str(wrapper)],capture_output=True,text=True)
        banner=(identity.stdout+identity.stderr).splitlines()[0]
        env=os.environ | {'GEMINI_TEST_SHELL':json.dumps([str(wrapper),'sh']),
                          'GEMINI_TEST_BUSYBOX':str(wrapper),'PYTHONDONTWRITEBYTECODE':'1'}
        tests = ('test-workload-cleanup.py','test-attribution-runtime.py','test-attribution-host.py') if a.suite=='attribution' else (
            'test-workload-cleanup.py','test-recovery-thermal.py','test-recovery-runtime.py',
            'test-recovery-boundary.py','test-recovery-observer.py','test-recovery-shutdown.py','test-recovery-host.py')
        if a.suite=='gemian-recovery':
            subprocess.run(['bash',str(HERE/'install-recovery-boot2.sh'),'--validate-only'],check=True)
            tests += ('test-gemian-recovery.py',)
        for name in tests:
            result=subprocess.run([sys.executable,str(HERE/name)],env=env,text=True,capture_output=True,timeout=120)
            if result.returncode:
                print(result.stdout);print(result.stderr,file=sys.stderr)
                raise ValueError('candidate shell fixture rejected: '+name)
            print(result.stdout,end='')
        print(json.dumps({'classification':'candidate-shell-fixtures-pass','suite':a.suite,'revision':revision,
                          'initramfs_sha256':INITRAMFS_SHA,'busybox_sha256':BUSYBOX_SHA,
                          'busybox_banner':banner,'emulator':Path(qemu).name,
                          'shell_and_parser_applets':'exact-candidate','device_action':'none',
                          'kernel_build':'none','temporary_binary':'removed-on-exit'},sort_keys=True))

if __name__=='__main__':main()
