#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the reviewed boot2 guard to the exact successor candidate."""

import importlib.util
import json
import os
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-10-01-mt6797-port0-header/install-passive.py'
SPEC = importlib.util.spec_from_file_location('port0_header_installer', SOURCE)
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)
ADAPTER = ADAPTER.ADAPTER
ADAPTER.HERE = HERE
ADAPTER.PREDECESSOR_SHA = 'fa7dc1a6a96f7b2e8c7e875271882b27f7e73148508a0ae4ae2880e32802165d'
ADAPTER.INSTALLER.HERE = HERE
ADAPTER.INSTALLER.EXPERIMENT = 'mt6797-port0-successor'
ADAPTER.INSTALLER.RECEIPT_NAME = 'mt6797-port0-successor-deployment-1'
ADAPTER.INSTALLER.MANIFEST_SHA = '533c178315ea1faf45bbbbaa41aaf1bde43adf169325d8f0259da1786fc13173'
ADAPTER.MANIFEST_SHA = ADAPTER.INSTALLER.MANIFEST_SHA


def validate(candidate, previous):
    ADAPTER.INSTALLER.boot_uuid(previous)
    candidate = Path(os.path.abspath(candidate))
    published = HERE / 'results/candidate.json'
    ADAPTER.INSTALLER.require(candidate.is_dir() and not candidate.is_symlink() and
                              ADAPTER.INSTALLER.digest(published.read_bytes()) ==
                              ADAPTER.MANIFEST_SHA, 'candidate receipt changed')
    expected = json.loads(published.read_text())
    ADAPTER.INSTALLER.require(expected['kernel_release'] ==
                              '7.1.3-gemini-a53-wifi-port0-successor' and
                              expected['parent_boot2_sha256'] == ADAPTER.PREDECESSOR_SHA and
                              expected['physical_admission'] is False and
                              candidate.name == 'candidate-' +
                              expected['files']['boot.img']['sha256'],
                              'candidate scope or path changed')
    ADAPTER.INSTALLER.require({p.name for p in candidate.iterdir()} ==
                              set(expected['files']) | {'candidate.json'} and
                              ADAPTER.INSTALLER.digest((candidate / 'candidate.json').read_bytes()) ==
                              ADAPTER.MANIFEST_SHA,
                              'candidate inventory changed')
    for name, identity in expected['files'].items():
        path = candidate / name
        ADAPTER.INSTALLER.require(path.is_file() and not path.is_symlink() and
                                  path.stat().st_size == identity['bytes'] and
                                  ADAPTER.INSTALLER.digest(path.read_bytes()) ==
                                  identity['sha256'], 'candidate file changed: ' + name)
    raw = (candidate / 'boot.img').read_bytes()
    padded = (candidate / 'boot2-padded.img').read_bytes()
    ADAPTER.INSTALLER.require(len(padded) == 16777216 and
                              padded == raw + bytes(16777216 - len(raw)),
                              'full boot2 padding changed')
    return expected, candidate


ADAPTER.INSTALLER.validate = validate
ADAPTER.validate = validate
MANIFEST_SHA = ADAPTER.MANIFEST_SHA
receipt = ADAPTER.INSTALLER.receipt


if __name__ == '__main__':
    ADAPTER.INSTALLER.main()
