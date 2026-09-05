#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the corrected V4 offline suite with the exact candidate BusyBox."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
EXTRACTOR_SHA = 'ff0a3642d4a8a6875228f80da34427d52b807778d0b829744c2aee0bc4d98ada'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initramfs', type=Path, required=True)
    parser.add_argument('--work-root', type=Path, required=True)
    parser.add_argument('--expected-revision', required=True)
    args = parser.parse_args()
    revision = subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
    if revision != args.expected_revision:
        raise ValueError('exact test revision required')
    if subprocess.check_output(['git','-C',str(REPO),'status','--porcelain'],text=True).strip():
        raise ValueError('test checkout is dirty')
    if not args.work_root.is_dir() or args.work_root.is_symlink():
        raise ValueError('unsafe managed temporary root')
    if args.initramfs.is_symlink() or not args.initramfs.is_file():
        raise ValueError('unsafe initramfs input')
    extractor = HERE/'run-candidate-shell-tests.py'
    if extractor.is_symlink() or hashlib.sha256(extractor.read_bytes()).hexdigest() != EXTRACTOR_SHA:
        raise ValueError('BusyBox extractor identity changed')
    helper = runpy.run_path(str(extractor))
    qemu = shutil.which('qemu-aarch64-static')
    if not qemu:
        raise ValueError('AArch64 user-mode emulator missing; no native fallback')
    binary = helper['extract_busybox'](args.initramfs.read_bytes())
    tests = ('test-v4-remote-shell.py','test-v4-observation-protocol.py',
             'test-v4-observation-runner.py','test-v4-installer-guard.py',
             'test-v4-deployment-shell.py')
    with tempfile.TemporaryDirectory(prefix='gemini-v4-shell-suite-',dir=args.work_root) as temporary:
        root = Path(temporary)
        busybox = root/'busybox';busybox.write_bytes(binary);busybox.chmod(0o700)
        wrapper = root/'candidate-busybox'
        wrapper.write_text('#!/bin/sh\nexec '+shlex.quote(qemu)+' '+shlex.quote(str(busybox))+' "$@"\n')
        wrapper.chmod(0o700)
        env = dict(os.environ, GEMINI_TEST_SHELL=json.dumps([str(wrapper),'sh']),
                   GEMINI_TEST_BUSYBOX=str(wrapper), PYTHONDONTWRITEBYTECODE='1')
        for script in ('remote-observation-state.sh','remote-v4-observation-read.sh'):
            subprocess.run([str(wrapper),'sh','-n',str(HERE/script)],check=True,env=env)
        for name in tests:
            result = subprocess.run([sys.executable,str(HERE/name)],env=env,text=True,capture_output=True,timeout=120)
            if result.returncode:
                print(result.stdout);print(result.stderr,file=sys.stderr)
                raise ValueError('V4 suite failed: '+name)
            print(result.stdout,end='')
        subprocess.run(['bash',str(HERE/'install-v4-boot2.sh'),'--validate-only'],env=env,check=True)
    print(json.dumps({'classification':'v4-offline-shell-suite-pass','revision':revision,
                      'initramfs_sha256':helper['INITRAMFS_SHA'],'busybox_sha256':helper['BUSYBOX_SHA'],
                      'observation_shell':'exact-candidate-busybox-under-qemu',
                      'deployment_shell':'builder-bash-synthetic-metadata',
                      'device_action':'none','kernel_build':'none',
                      'temporary_binary':'removed','test_scripts':list(tests)},sort_keys=True))


if __name__ == '__main__':
    main()
