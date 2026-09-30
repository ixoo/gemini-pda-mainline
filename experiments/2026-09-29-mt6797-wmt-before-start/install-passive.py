#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the reviewed boot2 guard to the deferred WMT-start image."""

import importlib.util
import json
import os
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-29-mt6797-region19-mainline-observe/install-passive.py'
SPEC = importlib.util.spec_from_file_location('region19_passive_installer', SOURCE)
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)
ADAPTER.HERE = HERE
ADAPTER.PREDECESSOR_SHA = 'd693e23ced511d6473a81d25e7c30eb792a7328b570755325b4492bb9bac1749'
ADAPTER.INSTALLER.HERE = HERE
ADAPTER.INSTALLER.EXPERIMENT = 'mt6797-wmt-before-start'
ADAPTER.INSTALLER.RECEIPT_NAME = 'mt6797-wmt-before-start-deployment-3'
ADAPTER.INSTALLER.MANIFEST_SHA = '5c2a1d6e65db746dfd62a8da13535ab55e95c72043cf4c42623e095b6c514131'
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
                              '7.1.3-gemini-a53-wifi-wmt-start' and
                              expected['physical_admission'] is False and
                              candidate.name == 'candidate-' +
                              expected['files']['boot.img']['sha256'],
                              'candidate scope or path changed')
    ADAPTER.INSTALLER.require({p.name for p in candidate.iterdir()} ==
                              set(expected['files']) | {'candidate.json'} and
                              ADAPTER.INSTALLER.digest((candidate / 'candidate.json').read_bytes()) ==
                              ADAPTER.MANIFEST_SHA, 'candidate inventory changed')
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
