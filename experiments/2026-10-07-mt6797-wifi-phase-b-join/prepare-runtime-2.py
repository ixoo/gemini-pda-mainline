#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create the fresh runtime-2 evidence root and check the laptop inputs offline.

Driven only by GEMINI_PRIVATE_REPO, GEMINI_RUNTIME_ROOT and GEMINI_JOIN_SCRIPT.
It writes two empty mode-0700 directories and nothing else; no device action.
"""

import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECEIPT = HERE / 'results/candidate-2.json'
COMMIT = 'db1b2aeae59b5bc117893b752f73e892efd78b10'
PACKAGE = '47addc1327b7c843d530cded614b86b1baab504dd87557dbfec3212fc80421ae'
RELEASE = '7.1.3-gemini-a53-wifi-phase-b-compile'
PREDECESSOR = '6ecc057c390e6c9acb3480a52950a7261d7f4678c43da5688dcc1724e2bb778f'
EVIDENCE, CAPTURE, SESSION = 'wifi-phase-b', 'capture-2', 'session-2'


def refuse(reason):
    sys.exit('prepare-runtime-2 refused: ' + reason)


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
    if not RECEIPT.is_file() or RECEIPT.is_symlink():
        refuse('results/candidate-2.json is not committed yet')
    digest = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()
    receipt = json.loads(RECEIPT.read_bytes())
    if (receipt.get('kernel_build_commit') != COMMIT or
            receipt.get('kernel_package_sha256') != PACKAGE or
            receipt.get('kernel_release') != RELEASE or
            receipt.get('physical_admission') is not False):
        refuse('results/candidate-2.json is not the package-2 candidate')
    for name in ('install-passive.py', 'capture-private.py'):
        if slot(name) != digest:
            refuse(name + ' MANIFEST_SHA slot is not the committed candidate-2 receipt')
    root = runtime / EVIDENCE
    for name in (CAPTURE, SESSION):
        if (root / name).exists() or (root / name).is_symlink():
            refuse(name + ' already exists; runtime 2 needs a fresh evidence root')
    root.mkdir(mode=0o700, exist_ok=True)
    for name in (CAPTURE, SESSION):
        (root / name).mkdir(mode=0o700)
    print(json.dumps({'evidence_root': str(root), 'created': [CAPTURE, SESSION],
                      'candidate_manifest_sha256': digest,
                      'candidate_boot2_sha256': receipt['files']['boot2-padded.img']['sha256'],
                      'predecessor_sha256': PREDECESSOR, 'deployment_receipt': 'deployment-2',
                      'device_action': 'none'}, indent=2))


if __name__ == '__main__':
    main()
