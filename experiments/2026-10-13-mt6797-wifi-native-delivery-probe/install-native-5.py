#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind ND5's real receipt and ND4 predecessor to unchanged boot2 guards."""
import json
import os
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'install-native-4.py'))
ADAPTER = BASE['ADAPTER']
INSTALLER = ADAPTER.INSTALLER
RELEASE = BASE['RELEASE']
PREDECESSOR_SHA = '7ce16dc852c1d89881c3ed4e676713fde1f8af755f297cc3e9671cddf6819a0c'
MANIFEST_SHA = '25893fa2bf4b67364e0821e635c0105c212f110d37156748d8e5a9338a612ef8'
ADAPTER.PREDECESSOR_SHA = PREDECESSOR_SHA
ADAPTER.MANIFEST_SHA = INSTALLER.MANIFEST_SHA = MANIFEST_SHA
INSTALLER.TOOL_NAME = 'install-native-5.py'
INSTALLER.CANDIDATE_RECEIPT = 'results/native-delivery-candidate-5.json'
INSTALLER.RECEIPT_NAME = 'mt6797-wifi-native-delivery-deployment-5'


def validate(candidate, previous):
    INSTALLER.boot_uuid(previous)
    candidate = Path(os.path.abspath(candidate))
    published = HERE / 'results/native-delivery-candidate-5.json'
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
