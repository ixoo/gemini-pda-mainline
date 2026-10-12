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
# Runtime identity (33 = candidate 32 over the then-installed candidate 30, the
# default and unchanged; 34 = the successor candidate 33 over the now-installed
# candidate 32). A narrow R34 wrapper sets GEMINI_PHASE_B_SESSION=34; the pinned
# predecessor and receipt sha are reviewed constants selected by it, and the
# reviewed guard still rederives and verifies the live GPT at deployment.
_SID = os.environ.get('GEMINI_PHASE_B_SESSION', '33')
if _SID not in ('33', '34'):
    raise SystemExit('GEMINI_PHASE_B_SESSION must be 33 or 34')
_CANDIDATE, PREDECESSOR_SHA, MANIFEST_SHA, _DEPLOYMENT = {
    '33': ('candidate-32',
           '54791b439791339fb1f6a2fec970b008569f9b1fa8883e3d7c3cb8a7a5da64f2',
           'e487260cda36a706433d5eb5790032413df2db997ef3d4abb4f0f09b54424320',
           'deployment-32'),
    '34': ('candidate-33',
           '5260715b453d4ad9e635845132f7d08530e0386ce6bce98f53a818b3ab87b815',
           '064d0f81b644eb2409406fa46054fa5ac135117bcf08678215466aaebebb4a37',
           'deployment-33'),
}[_SID]
ADAPTER.HERE = HERE
ADAPTER.PREDECESSOR_SHA = PREDECESSOR_SHA
ADAPTER.INSTALLER.HERE = HERE
ADAPTER.INSTALLER.EXPERIMENT = 'mt6797-wifi-phase-b'
ADAPTER.INSTALLER.RECEIPT_NAME = 'mt6797-wifi-phase-b-' + _DEPLOYMENT
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
    published = HERE / 'results' / (_CANDIDATE + '.json')
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
