#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ROOT-only REAL CCMP5 receipt/predecessor binding; unchanged reviewed boot2 guard."""

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
INSTALLER = ADAPTER.INSTALLER
RELEASE = '7.1.3-gemini-a53-wifi-ccmp-stable-monitor'
# Expected last-installed CCMP4, freshly verified by ROOT/GPT guard before write.
# Historical Gemian identity is not current identity or a deployment receipt.
PREDECESSOR_SHA = 'ee5dd8ad261496a387cf755b755982e0280f13a259e49619eb2de26e4a8dfc16'
MANIFEST_SHA = '1b1d668c15754b75e36fac6d24d4a31a3bc21eda042ead307a198c560e58597d'
ADAPTER.HERE = HERE
ADAPTER.PREDECESSOR_SHA = PREDECESSOR_SHA
ADAPTER.INSTALLER.HERE = HERE
ADAPTER.INSTALLER.TOOL_NAME = 'install-ccmp5.py'
ADAPTER.INSTALLER.CANDIDATE_RECEIPT = 'results/ccmp-stable-monitor-candidate-5.json'
ADAPTER.INSTALLER.EXPERIMENT = 'mt6797-wifi-ccmp-stable-monitor'
ADAPTER.INSTALLER.RECEIPT_NAME = 'mt6797-wifi-ccmp-stable-monitor-deployment-5'
ADAPTER.INSTALLER.MANIFEST_SHA = MANIFEST_SHA
ADAPTER.MANIFEST_SHA = MANIFEST_SHA
ORIGINAL_SOURCES = ADAPTER.INSTALLER.sources


def sources():
    """Read the pinned installer inputs from the retained private checkout, as the
    phase-b binding does: the reviewed install-boot2.sh bytes live there. Every
    pin, digest and derive check stays as reviewed; a mismatching private copy
    still refuses."""
    installer, parser = ORIGINAL_SOURCES()
    private = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
    pinned = installer['pinned_sources']
    installer = dict(installer)
    installer['pinned_sources'] = lambda repo=private: pinned(repo)
    return installer, parser


ADAPTER.INSTALLER.sources = sources


def validate(candidate, previous):
    ADAPTER.INSTALLER.boot_uuid(previous)
    candidate = Path(os.path.abspath(candidate))
    published = HERE / 'results/ccmp-stable-monitor-candidate-5.json'
    ADAPTER.INSTALLER.require(candidate.is_dir() and not candidate.is_symlink() and
                              ADAPTER.INSTALLER.digest(published.read_bytes()) ==
                              MANIFEST_SHA, 'candidate receipt changed')
    expected = json.loads(published.read_text())
    ADAPTER.INSTALLER.require(expected['kernel_release'] == RELEASE and
                              expected['physical_admission'] is False and
                               expected.get('native_delivery_diag') is False and
                               expected.get('ccmp_stable_epoch') is True and
                               expected.get('bootstrap') == 'normal-dhcp-only' and
                               expected.get('integration_source_commit') ==
                               '85d1d6212d24f8c1d53050dcc4be7060820c06af' and
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
