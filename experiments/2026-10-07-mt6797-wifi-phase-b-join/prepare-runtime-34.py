#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline preparation for runtime 34 (the Phase-B two-lifetime successor).

Runtime 34 is its own identity (session-34 / capture-34), independent of
runtime 33, which stays pinned as evidence. This adapter validates the private
laptop inputs and the committed candidate-33 receipt (produced offline by
build-successor-candidate.py: the 6d6eabeb kernel on the candidate-32 parent,
config/DT/RAM byte-identical) and creates a fresh evidence root. It fabricates
no hashes -- the build commit and package digest are read from the receipt --
and takes no device, radio, build or key action.

Driven by GEMINI_PRIVATE_REPO, GEMINI_RUNTIME_ROOT and GEMINI_JOIN_SCRIPT (the
reviewed two-lifetime join-twice.sh, with the negative-scan fatal guard and the
finite owned-child quiescence the host gates on).
"""

import hashlib
import json
import os
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECEIPT = HERE / 'results/candidate-33.json'
RELEASE = '7.1.3-gemini-a53-wifi-phase-b-compile'
COMMIT = '6d6eabeb782cdbf1ef9683846934fc95677dc57d'
PACKAGE = '01851f2e1b43c2e834406d778033cbd4ff2e8655b5bea8ab1535a192e6e163c2'
EVIDENCE, CAPTURE, SESSION = 'wifi-phase-b', 'capture-34', 'session-34'


def refuse(reason):
    sys.exit('prepare-runtime 34 refused: ' + reason)


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
    reviewed = (HERE / 'join-twice.sh').resolve()
    if not body.startswith(b'TARGET_SSID=') or not body.endswith(reviewed.read_bytes()):
        refuse('GEMINI_JOIN_SCRIPT does not wrap the reviewed two-lifetime join-twice.sh')
    if b'\nWPA_PSK_HEX=' not in body or b'\nTARGET_SSID_HEX=' not in body:
        refuse('GEMINI_JOIN_SCRIPT is not the PSK-bound C2 script')
    # The receipt is produced offline by build-successor-candidate.py; its hashes
    # are read here, never fabricated. It refuses until that receipt is committed.
    if not RECEIPT.is_file() or RECEIPT.is_symlink():
        refuse('results/candidate-33.json is not committed yet')
    digest = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()
    receipt = json.loads(RECEIPT.read_bytes())
    if (receipt.get('kernel_release') != RELEASE or
            receipt.get('kernel_build_commit') != COMMIT or
            receipt.get('kernel_package_sha256') != PACKAGE or
            receipt.get('parent_candidate') != 'candidate-32' or
            receipt.get('physical_admission') is not False):
        refuse('results/candidate-33.json is not the 6d6 successor on the candidate-32 parent')
    try:
        boot2 = receipt['files']['boot2-padded.img']['sha256']
    except (KeyError, TypeError):
        refuse('receipt has no boot2-padded.img sha256')
    root = runtime / EVIDENCE
    for name in (CAPTURE, SESSION):
        if (root / name).exists() or (root / name).is_symlink():
            refuse(name + ' already exists; runtime 34 needs a fresh evidence root')
    root.mkdir(mode=0o700, exist_ok=True)
    (root / SESSION).mkdir(mode=0o700)
    if (root / CAPTURE).exists():
        refuse('capture directory appeared; the capture must claim it')
    print(json.dumps({'evidence_root': str(root), 'created': [SESSION],
                      'left_absent_for_capture_claim': CAPTURE,
                      'candidate_manifest_sha256': digest,
                      'kernel_build_commit': receipt['kernel_build_commit'],
                      'kernel_package_sha256': receipt['kernel_package_sha256'],
                      'candidate_boot2_sha256': boot2,
                      'predecessor': 'rederived by the reviewed boot2 guard at deployment',
                      'device_action': 'none'}, indent=2))


if __name__ == '__main__':
    main()
