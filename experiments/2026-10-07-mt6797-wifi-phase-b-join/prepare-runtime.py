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
RECEIPT = HERE / 'results/candidate-27.json'
COMMIT = '5ee1f55f4c9bd5e5b94df3218f4d900c1305c6e6'
PACKAGE = 'e9610ba518b49a6f4289cff22a0c0c143309492359c66eeb7e194aee97129240'
RELEASE = '7.1.3-gemini-a53-wifi-phase-b-compile'
# Current boot2 content: the installed candidate 26 (deployment 26, full 16 MiB
# readback verified); the custodian rederives the live GPT and verifies it with
# the reviewed guard at deployment.
PREDECESSOR = 'e322e068ebff5888b4dd8f20063aa5c634cc385269c87a70780ff5240b1addf1'
EVIDENCE, CAPTURE, SESSION = 'wifi-phase-b', 'capture-28', 'session-28'


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
            info.st_nlink != 1 or info.st_size > 32768):
        refuse('GEMINI_JOIN_SCRIPT must be one small mode-0600 regular file')
    body = script.read_bytes()
    if not body.startswith(b'TARGET_SSID=') or \
            not body.endswith((HERE / 'join-once.sh').read_bytes()):
        refuse('GEMINI_JOIN_SCRIPT does not wrap the reviewed join-once.sh')
    # Runtime 28 is the supplicant-owned C2+C3 session: the private binder must
    # have added the PSK and the hex SSID (never printed here).
    if b'\nWPA_PSK_HEX=' not in body or b'\nTARGET_SSID_HEX=' not in body:
        refuse('GEMINI_JOIN_SCRIPT is not the PSK-bound C2 script')
    if not RECEIPT.is_file() or RECEIPT.is_symlink():
        refuse('results/candidate-27.json is not committed yet')
    digest = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()
    receipt = json.loads(RECEIPT.read_bytes())
    if (receipt.get('kernel_build_commit') != COMMIT or
            receipt.get('kernel_package_sha256') != PACKAGE or
            receipt.get('kernel_release') != RELEASE or
            receipt.get('physical_admission') is not False):
        refuse('results/candidate-27.json is not the package-27 candidate')
    for name in ('install-passive.py', 'capture-private.py'):
        if slot(name) != digest:
            refuse(name + ' MANIFEST_SHA slot is not the committed candidate-27 receipt')
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
                      'predecessor_sha256': PREDECESSOR, 'deployment_receipt': 'deployment-27',
                      'device_action': 'none'}, indent=2))


if __name__ == '__main__':
    main()
