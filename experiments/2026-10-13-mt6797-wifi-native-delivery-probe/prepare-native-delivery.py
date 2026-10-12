#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline preparation for the native-crypto-delivery runtime (proposal 0181).

The native-delivery diagnostic is its OWN runtime identity, independent of
candidate 32 / runtime 33, which stay pinned and untouched. This adapter only
validates the private laptop inputs and the committed candidate receipt, then
creates a fresh evidence root. It performs NO device, radio, build or key
action, and it fabricates no hashes: the kernel build commit and package digest
are read from the committed receipt the Buildbox build produces, never written
here.

Driven by GEMINI_PRIVATE_REPO, GEMINI_RUNTIME_ROOT and GEMINI_JOIN_SCRIPT. The
native diagnostic is a SINGLE association lifetime: the join script wraps the
reviewed one-cycle join-once.sh (auto-reconnect disabled via wpa_cli, one cycle
selected); the diagnostic engages during that association and stays CLOSED after
its first window. The candidate receipt it checks is the one the LAPTOP
compositor produces from the Buildbox kernel package plus the verified private
parent/RAM root -- Buildbox itself emits only a kernel package. This adapter is
the offline preparation step; the executable compositor/capture/classifier are
authored separately. No device, radio, build or key action; no fabricated hash.
"""

import hashlib
import json
import os
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECEIPT = HERE / 'results/native-delivery-candidate.json'
RELEASE = '7.1.3-gemini-a53-wifi-native-delivery-diag'
EVIDENCE, CAPTURE, SESSION = 'native-delivery', 'capture-nd1', 'session-nd1'


def refuse(reason):
    sys.exit('prepare-native-delivery refused: ' + reason)


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
    # The diagnostic engages during the reviewed C2 join; reuse that exact
    # script (the private binder adds the PSK and hex SSID; never printed here).
    reviewed = (HERE.parent / '2026-10-07-mt6797-wifi-phase-b-join' /
                'join-once.sh').resolve()
    if not body.startswith(b'TARGET_SSID=') or \
            not body.endswith(reviewed.read_bytes()):
        refuse('GEMINI_JOIN_SCRIPT does not wrap the reviewed one-cycle join-once.sh')
    if b'\nWPA_PSK_HEX=' not in body or b'\nTARGET_SSID_HEX=' not in body:
        refuse('GEMINI_JOIN_SCRIPT is not the PSK-bound single-lifetime script')
    # The receipt is produced by the LAPTOP compositor (from the Buildbox
    # kernel package + verified private parent); its hashes are read, never
    # fabricated here. Buildbox emits only the kernel package.
    if not RECEIPT.is_file() or RECEIPT.is_symlink():
        refuse('results/native-delivery-candidate.json is not committed yet')
    digest = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()
    receipt = json.loads(RECEIPT.read_bytes())
    if receipt.get('kernel_release') != RELEASE:
        refuse('receipt kernel_release is not the native-delivery profile')
    if receipt.get('physical_admission') is not False:
        refuse('receipt must record physical_admission false')
    if receipt.get('native_delivery_diag') is not True:
        refuse('receipt does not mark the native-delivery diagnostic armed')
    for field in ('kernel_build_commit', 'kernel_package_sha256'):
        value = receipt.get(field)
        if not isinstance(value, str) or len(value) < 40:
            refuse('receipt %s missing or malformed' % field)
    try:
        boot2 = receipt['files']['boot2-padded.img']['sha256']
    except (KeyError, TypeError):
        refuse('receipt has no boot2-padded.img sha256')
    root = runtime / EVIDENCE
    for name in (CAPTURE, SESSION):
        if (root / name).exists() or (root / name).is_symlink():
            refuse(name + ' already exists; the native-delivery runtime needs a fresh root')
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
