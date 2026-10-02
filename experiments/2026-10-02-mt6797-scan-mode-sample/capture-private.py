#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve WMT evidence and issue one passive-scan session."""

import importlib.util
import json
import os
from pathlib import Path
import sys


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/scan-mode-sample'
SOURCE = HERE.parent / '2026-09-29-mt6797-wmt-before-start/capture-private.py'
SPEC = importlib.util.spec_from_file_location('wmt_start_capture', SOURCE)
WMT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WMT)
WMT.HERE = HERE
WMT.ROOT = ROOT
WMT.CAPTURE_DIR = ROOT / 'capture-1'
WMT.RELEASE = '7.1.3-gemini-a53-wifi-scan-mode-sample'
WMT.CAPTURE.HERE = HERE
WMT.CAPTURE.ROOT = ROOT
WMT.CAPTURE.CAPTURE = WMT.CAPTURE_DIR
WMT.CAPTURE.DEPLOYMENT = ROOT / 'session-1/deployment-summary.txt'
WMT.CAPTURE.RECEIPT = HERE / 'results/candidate.json'
WMT.CAPTURE.MANIFEST_SHA = '5ab002a5cd356f6f6a8784f001b24f47dd4f56019e2cd0218e01bc24f2340514'
WMT.CAPTURE.RELEASE = WMT.RELEASE


def prepare(candidate):
    published = WMT.CAPTURE.RECEIPT.read_bytes()
    WMT.require(WMT.sha(published) == WMT.CAPTURE.MANIFEST_SHA,
                'published candidate changed')
    expected = json.loads(published)
    WMT.require(not candidate.is_symlink(), 'candidate path is a symlink')
    candidate = candidate.resolve(strict=True)
    WMT.require(candidate.is_dir() and
                candidate.name == 'candidate-' + expected['files']['boot.img']['sha256'] and
                json.loads((candidate / 'candidate.json').read_bytes()) == expected and
                {p.name for p in candidate.iterdir()} == set(expected['files']) | {'candidate.json'},
                'private candidate identity changed')
    for name, identity in expected['files'].items():
        path = candidate / name
        WMT.require(path.is_file() and not path.is_symlink() and
                    path.stat().st_size == identity['bytes'] and
                    WMT.sha(path.read_bytes()) == identity['sha256'],
                    'candidate member changed: ' + name)
    rows = [line.split('=', 1) for line in WMT.CAPTURE.DEPLOYMENT.read_text().splitlines()]
    WMT.require(all(len(row) == 2 for row in rows) and
                len({row[0] for row in rows}) == len(rows), 'deployment malformed')
    fields = dict(rows)
    WMT.require(fields.get('experiment') == 'mt6797-scan-mode-sample' and
                fields.get('candidate_manifest_sha256') == WMT.CAPTURE.MANIFEST_SHA and
                fields.get('target_logical_name') == 'boot2' and
                fields.get('result') in ('write-synced-flushed-full-readback-verified',
                                         'skipped-already-matching') and
                (fields['result'] != 'skipped-already-matching' or
                 fields.get('predecessor_sha256') == expected['files']['boot2-padded.img']['sha256']) and
                fields.get('candidate_sha256') == expected['files']['boot2-padded.img']['sha256'] and
                fields.get('readback_sha256') == fields['candidate_sha256'] and
                fields.get('reboot') == 'no', 'deployment not admitted')
    return expected


WMT.prepare = prepare


if __name__ == '__main__':
    raise SystemExit(WMT.main())
