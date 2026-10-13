#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind ND4's real receipt and ND3 predecessor to the unchanged boot2 guards."""
import json
import os
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'install-native-3.py'))
ADAPTER = BASE['ADAPTER']
INSTALLER = ADAPTER.INSTALLER
RELEASE = BASE['RELEASE']
PREDECESSOR_SHA = '7b61241a89c9d8472885c93d654ecda6f63a188f154b2a7bfc69dd5caaf9dc06'
MANIFEST_SHA = 'b7ca24a196fb416b25ce6e078770087b96d3ea240dd9928230d1e3156d7dd079'
ADAPTER.PREDECESSOR_SHA = PREDECESSOR_SHA
ADAPTER.MANIFEST_SHA = INSTALLER.MANIFEST_SHA = MANIFEST_SHA
INSTALLER.TOOL_NAME = 'install-native-4.py'
INSTALLER.CANDIDATE_RECEIPT = 'results/native-delivery-candidate-4.json'
INSTALLER.RECEIPT_NAME = 'mt6797-wifi-native-delivery-deployment-4'


def validate(candidate, previous):
    INSTALLER.boot_uuid(previous)
    candidate = Path(os.path.abspath(candidate))
    published = HERE / 'results/native-delivery-candidate-4.json'
    INSTALLER.require(candidate.is_dir() and not candidate.is_symlink() and
                      INSTALLER.digest(published.read_bytes()) == MANIFEST_SHA,
                      'candidate receipt changed')
    expected = json.loads(published.read_bytes())
    INSTALLER.require(expected['kernel_release'] == RELEASE and
                      expected['physical_admission'] is False and
                      expected.get('native_delivery_diag') is True and
                      candidate.name == 'candidate-' + expected['files']['boot.img']['sha256'],
                      'candidate scope or path changed')
    INSTALLER.require({p.name for p in candidate.iterdir()} ==
                      set(expected['files']) | {'candidate.json'} and
                      (candidate / 'candidate.json').is_file() and
                      not (candidate / 'candidate.json').is_symlink() and
                      INSTALLER.digest((candidate / 'candidate.json').read_bytes()) == MANIFEST_SHA,
                      'candidate inventory changed')
    for name, identity in expected['files'].items():
        path = candidate / name
        INSTALLER.require(path.is_file() and not path.is_symlink() and
                          path.stat().st_size == identity['bytes'] and
                          INSTALLER.digest(path.read_bytes()) == identity['sha256'],
                          'candidate file changed: ' + name)
    raw = (candidate / 'boot.img').read_bytes()
    padded = (candidate / 'boot2-padded.img').read_bytes()
    INSTALLER.require(len(padded) == 16777216 and
                      padded == raw + bytes(16777216 - len(raw)),
                      'full boot2 padding changed')
    return expected, candidate


ADAPTER.validate = INSTALLER.validate = validate
receipt = INSTALLER.receipt

if __name__ == '__main__':
    INSTALLER.main()
