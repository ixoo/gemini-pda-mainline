#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the reviewed boot2 guard to the Phase B candidate."""

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
RELEASE = '7.1.3-gemini-a53-wifi-phase-b-compile'
# Current boot2 content: the consumed Phase B candidate 17 (deployment 17).
PREDECESSOR_SHA = '5135b2f8d5d8a8d64b507cd635f29511207392a4525327b27c6a7ecc9d80985a'
# Slot filled from the committed results/candidate-18.json after composition.
MANIFEST_SHA = 'b0d577bab4db726d5929acbf2d3481101492b1e2448f2a85bdbae88ec913cab5'
ADAPTER.HERE = HERE
ADAPTER.PREDECESSOR_SHA = PREDECESSOR_SHA
ADAPTER.INSTALLER.HERE = HERE
ADAPTER.INSTALLER.EXPERIMENT = 'mt6797-wifi-phase-b'
ADAPTER.INSTALLER.RECEIPT_NAME = 'mt6797-wifi-phase-b-deployment-18'
ADAPTER.INSTALLER.MANIFEST_SHA = MANIFEST_SHA
ADAPTER.MANIFEST_SHA = MANIFEST_SHA
ORIGINAL_SOURCES = ADAPTER.INSTALLER.sources


def sources():
    """Read the pinned installer inputs from the retained private checkout.

    The baseline installer's pinned_sources() captures this checkout as its
    default root, and this checkout's install-boot2.sh no longer matches the
    reviewed pin (changed by a0887d2c after the pin at cac47380), while the
    private checkout retains the pinned bytes. Bind that one input root to
    GEMINI_PRIVATE_REPO. Every pin, digest and derive check stays as reviewed;
    a mismatching private copy still refuses.
    """
    installer, parser = ORIGINAL_SOURCES()
    private = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
    pinned = installer['pinned_sources']
    installer = dict(installer)
    installer['pinned_sources'] = lambda repo=private: pinned(repo)
    return installer, parser


ADAPTER.INSTALLER.sources = sources


def validate(candidate, previous):
    ADAPTER.INSTALLER.require(MANIFEST_SHA is not None, 'Phase B receipt slot not filled')
    ADAPTER.INSTALLER.boot_uuid(previous)
    candidate = Path(os.path.abspath(candidate))
    published = HERE / 'results/candidate-18.json'
    ADAPTER.INSTALLER.require(candidate.is_dir() and not candidate.is_symlink() and
                              ADAPTER.INSTALLER.digest(published.read_bytes()) ==
                              MANIFEST_SHA, 'candidate receipt changed')
    expected = json.loads(published.read_text())
    ADAPTER.INSTALLER.require(expected['kernel_release'] == RELEASE and
                              expected['physical_admission'] is False and
                              candidate.name == 'candidate-' +
                              expected['files']['boot.img']['sha256'],
                              'candidate scope or path changed')
    ADAPTER.INSTALLER.require({p.name for p in candidate.iterdir()} ==
                              set(expected['files']) | {'candidate.json'} and
                              (candidate / 'candidate.json').is_file() and
                              not (candidate / 'candidate.json').is_symlink() and
                              ADAPTER.INSTALLER.digest((candidate / 'candidate.json').read_bytes()) ==
                              MANIFEST_SHA, 'candidate inventory changed')
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
receipt = ADAPTER.INSTALLER.receipt


if __name__ == '__main__':
    ADAPTER.INSTALLER.main()
