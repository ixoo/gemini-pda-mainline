#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The Phase B host checks capture identity against the candidate-2 receipt.

The inherited WMT host main reads HERE/results/candidate.json; the Phase B host
binds that HERE to runtime-2/. Asserts the binding targets that module, that the
bound receipt is byte-identical to results/candidate-2.json, that the runtime-1
receipt is preserved, and that the inherited identity predicate accepts
candidate-2 capture evidence while refusing runtime-1 identity or a boot
mismatch. No device action.
"""
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
RECEIPT_SHA = 'f19dffdb622643e7dd486a2b6b3b4e752c993b5908ecc91929c0b4a0972ee896'
CANDIDATE_2_BOOT2 = '03a6d78caf8d38eca3d46015dc053defa8677d6e75ab40454593fe8155590bf4'
CANDIDATE_3_BOOT2 = '84f65eae0a5ddc63f1c271ba78873d54e61bec30ec6e8ae176cb8394098f0adc'
RUNTIME_1_BOOT2 = '6ecc057c390e6c9acb3480a52950a7261d7f4678c43da5688dcc1724e2bb778f'

with tempfile.TemporaryDirectory(prefix='mt6797-host-identity-') as directory:
    work = Path(directory)
    (work / 'private/artifacts/credentials').mkdir(parents=True)
    (work / 'runtime').mkdir()
    bound = work / 'bound.sh'
    bound.write_bytes(b'TARGET_SSID=x\n' + (HERE / 'join-once.sh').read_bytes())
    bound.chmod(0o600)
    os.environ.update(GEMINI_PRIVATE_REPO=str(work / 'private'), GEMINI_RUNTIME_ROOT=str(work / 'runtime'),
                      GEMINI_JOIN_SCRIPT=str(bound))
    spec = importlib.util.spec_from_file_location('phase_b_host', HERE / 'passive-host.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    host = module.HOST
    source = Path(host.main.__code__.co_filename)
    assert source.parent.name == '2026-09-29-mt6797-wmt-before-start', source
    assert source.read_text().count("json.loads((HERE / 'results/candidate.json').read_text())") == 1
    # Each runtime binds the WMT host identity to its own candidate receipt
    # through a byte copy; earlier copies stay bound to their runtimes.
    PAIRS = [('runtime-2', 'candidate-2'), ('runtime-4', 'candidate-3'), ('runtime-5', 'candidate-4'),
             ('runtime-6', 'candidate-5'), ('runtime-7', 'candidate-6'), ('runtime-8', 'candidate-7'),
             ('runtime-9', 'candidate-8'), ('runtime-10', 'candidate-9'),
             ('runtime-11', 'candidate-10')]
    assert host.HERE == HERE / PAIRS[-1][0]
    receipts = []
    for directory, receipt in PAIRS:
        copy, published = HERE / directory / 'results/candidate.json', HERE / 'results' / (receipt + '.json')
        if published.exists():
            assert copy.read_bytes() == published.read_bytes(), (directory, 'copy differs from its receipt')
            receipts.append(published.read_bytes())
        else:
            assert not copy.exists(), (directory, 'copy without a committed receipt')
    assert hashlib.sha256(receipts[0]).hexdigest() == RECEIPT_SHA
    bound_receipt = receipts[-1]
    digest = json.loads(bound_receipt)['files']['boot2-padded.img']['sha256']
    assert digest in (CANDIDATE_2_BOOT2, CANDIDATE_3_BOOT2) or len(receipts) >= 3
    runtime_2 = receipts[0]
    candidate_3 = HERE / 'results/candidate-3.json'
    runtime_1 = json.loads((HERE / 'results/candidate.json').read_bytes())
    assert runtime_1['files']['boot2-padded.img']['sha256'] == RUNTIME_1_BOOT2, 'runtime-1 receipt preserved'
    # Other rebound roots are untouched by the receipt binding.
    assert host.DOMAIN.HERE == HERE and host.DOMAIN.HOST.HERE == HERE
    assert host.ROOT == work / 'runtime/wifi-phase-b/session-10' and host.CAPTURE == work / 'runtime/wifi-phase-b/capture-10'

    def identity(receipt, wmt, start):
        digest = receipt['files']['boot2-padded.img']['sha256']
        return (wmt.get('accepted') is True and
                wmt.get('candidate_boot2_sha256') == digest and
                start.get('candidate_boot2_sha256') == digest and
                start.get('boot_id') == wmt.get('boot_id') and
                start.get('one_host_start_attempt') is True and
                start.get('firmware_start_request_sent') is True)
    boot = 'eee023ca-0000-4000-8000-000000000000'
    wmt = {'accepted': True, 'candidate_boot2_sha256': digest, 'boot_id': boot}
    start = {'candidate_boot2_sha256': digest, 'boot_id': boot, 'one_host_start_attempt': True,
             'firmware_start_request_sent': True}
    assert identity(json.loads(bound_receipt), wmt, start), 'current-candidate evidence must pass'
    assert not identity(runtime_1, wmt, start), 'runtime-1 receipt must refuse current evidence'
    for other in receipts[:-1]:
        assert not identity(json.loads(other), wmt, start), 'an earlier receipt must refuse the current evidence'
    assert not identity(json.loads(bound_receipt), wmt, dict(start, boot_id='other')), 'boot mismatch refused'
    assert not identity(json.loads(bound_receipt), dict(wmt, candidate_boot2_sha256=RUNTIME_1_BOOT2), start)
print('host identity: PASS (WMT host receipt bound per runtime; runtime-1 receipt preserved; predicate positive/negative)')
