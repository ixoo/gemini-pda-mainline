#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create the fresh runtime 4 evidence root and check the laptop inputs offline.

Driven only by GEMINI_PRIVATE_REPO, GEMINI_RUNTIME_ROOT and GEMINI_JOIN_SCRIPT.
It creates the evidence root and the session directory only. The capture
directory is left absent, because the inherited capture claims it itself and
refuses when it already exists (one attempt per root). No device action.
"""

import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECEIPT = HERE / 'results/candidate-14.json'
COMMIT = '67a37ca130885e76c18a3b8c89969beacfaa99f9'
PACKAGE = 'ee32128de75a20ab64da1ebd82d25e7b88ea41e826fb6a875bce471025a7df9e'
RELEASE = '7.1.3-gemini-a53-wifi-phase-b-compile'
PREDECESSOR = 'ec412ce9a34441c0fe4258e36cc1d16ccb648ea2d0b6b5ffe76f803fdca2d786'
EVIDENCE, CAPTURE, SESSION = 'wifi-phase-b', 'capture-15', 'session-15'


def refuse(reason):
    sys.exit('prepare-runtime 4 refused: ' + reason)


def slot(name):
    match = re.search(r"^MANIFEST_SHA = (None|'([0-9a-f]{64})')$",
                      (HERE / name).read_text(), re.M)
    return match.group(2) if match else None


def main():
    os.umask(0o077)
    try:
        private = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
        runtime = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True)
        script = Path(os.environ['GEMINI_JOIN_SCRIPT'])
        info = script.lstat()
    except (KeyError, OSError) as error:
        refuse('environment: ' + str(error))
    if not private.is_dir() or not (private / 'artifacts/credentials').is_dir():
        refuse('GEMINI_PRIVATE_REPO is not the private repository')
    if not runtime.is_dir():
        refuse('GEMINI_RUNTIME_ROOT is not a directory')
    if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or
            info.st_nlink != 1 or info.st_size > 20480):
        refuse('GEMINI_JOIN_SCRIPT must be one small mode-0600 regular file')
    body = script.read_bytes()
    if not body.startswith(b'TARGET_SSID=') or \
            not body.endswith((HERE / 'join-once.sh').read_bytes()):
        refuse('GEMINI_JOIN_SCRIPT does not wrap the reviewed join-once.sh')
    # Runtime 15 is the supplicant-owned C2 session: the private binder must
    # have added the PSK and the hex SSID (never printed here).
    if b'\nWPA_PSK_HEX=' not in body or b'\nTARGET_SSID_HEX=' not in body:
        refuse('GEMINI_JOIN_SCRIPT is not the PSK-bound C2 script')
    if not RECEIPT.is_file() or RECEIPT.is_symlink():
        refuse('results/candidate-14.json is not committed yet')
    digest = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()
    receipt = json.loads(RECEIPT.read_bytes())
    if (receipt.get('kernel_build_commit') != COMMIT or
            receipt.get('kernel_package_sha256') != PACKAGE or
            receipt.get('kernel_release') != RELEASE or
            receipt.get('physical_admission') is not False):
        refuse('results/candidate-14.json is not the package-14 candidate')
    for name in ('install-passive.py', 'capture-private.py'):
        if slot(name) != digest:
            refuse(name + ' MANIFEST_SHA slot is not the committed candidate-14 receipt')
    root = runtime / EVIDENCE
    for name in (CAPTURE, SESSION):
        if (root / name).exists() or (root / name).is_symlink():
            refuse(name + ' already exists; runtime 2 needs a fresh evidence root')
    root.mkdir(mode=0o700, exist_ok=True)
    (root / SESSION).mkdir(mode=0o700)
    if (root / CAPTURE).exists():
        refuse('capture directory appeared; the capture must claim it')
    print(json.dumps({'evidence_root': str(root), 'created': [SESSION],
                      'left_absent_for_capture_claim': CAPTURE,
                      'candidate_manifest_sha256': digest,
                      'candidate_boot2_sha256': receipt['files']['boot2-padded.img']['sha256'],
                      'predecessor_sha256': PREDECESSOR, 'deployment_receipt': 'deployment-14',
                      'device_action': 'none'}, indent=2))


if __name__ == '__main__':
    main()
