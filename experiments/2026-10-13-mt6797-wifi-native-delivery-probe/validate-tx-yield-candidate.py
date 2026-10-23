#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only exact yield candidate check, shared with the guarded installer."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import runpy

MANIFEST='d3b1c04e811330a00ff4f7dad7e93e808899eb5734aee851b195ee7195374a42'  # Seal from the composed yield candidate.
BOOT2='8014a0dd67c5cf5641ef4134fa5412bba971a4c93c095d48c60f02a95051ccae'
BOOT='04bd176f6f8dd9a91d3cc96ddfbcfe1286bde29ee9992ccee7cef85162bb68f4'
NOTES='efdc05a727078927f49a07db0344d39493c04548a1ab8cadab9e68e650611052'
NOTES_OFFSET=12900184
COMMIT='1a4f291e221e7bc42536b4e17594614dae269405'  # Seal from the pushed yield build input.


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate(candidate):
    if None in (MANIFEST, BOOT2, BOOT, NOTES, NOTES_OFFSET, COMMIT):
        raise ValueError('yield candidate binding is not sealed')
    if candidate.is_symlink():
        raise ValueError('symlink candidate refused')
    candidate=candidate.resolve(strict=True)
    raw=(candidate/'candidate.json').read_bytes()
    if digest(raw)!=MANIFEST:
        raise ValueError('yield manifest changed')
    value=json.loads(raw)
    if (candidate.name!='candidate-'+BOOT or
        {p.name for p in candidate.iterdir()}!=set(value['files'])|{'candidate.json'}):
        raise ValueError('yield candidate inventory changed')
    for name,identity in value['files'].items():
        path=candidate/name
        if (path.is_symlink() or not path.is_file() or
            path.stat().st_size!=identity['bytes'] or digest(path.read_bytes())!=identity['sha256']):
            raise ValueError('yield member changed: '+name)
    if (value['kernel_build_commit']!=COMMIT or
        value['kernel_profile']!='mt6797-a53-wifi-tx-yield-measurement' or
        value['files']['boot2-padded.img']['sha256']!=BOOT2 or
        value['files']['boot2-padded.img']['bytes']!=16777216 or
        value['kernel_notes_sha256']!=NOTES or value['kernel_notes_bytes']!=84 or
        value.get('tx_pump_pending_yield_ms')!=1 or value.get('tx_pump_progress_resets') is not True or
        value.get('data_tx_depth')!=4 or value.get('kernel_notes_offset')!=NOTES_OFFSET or
        value['snapshot_enabled'] or value['key_reuse'] or value['reconnect']):
        raise ValueError('yield identity/admission contract changed')
    image=gzip.decompress((candidate/'Image.gz').read_bytes())
    if digest(image[NOTES_OFFSET:NOTES_OFFSET+84])!=NOTES:
        raise ValueError('Image notes do not match reviewed System.map identity')
    config=(candidate/'kernel.config').read_text()
    if ('CONFIG_MT6797_CCMP_TX_PUMP=y\n' not in config or
        'CONFIG_MT6797_CCMP_TX_DEPTH=4\n' not in config or
        'CONFIG_MT6797_CCMP_LIFETIME_PREREQUISITES=y\n' in config or
        'CONFIG_CFG80211_DEBUGFS=y\n' in config):
        raise ValueError('yield config changed')
    return value


def validate_receipt(path, previous):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>16384:
        raise ValueError('unsafe deployment receipt')
    raw=path.read_text(encoding='ascii')
    original='experiment=mt6797-wifi-ccmp-stable-monitor'
    lines=raw.splitlines()
    if lines.count(original)!=1 or any(l.startswith('experiment=') and l!=original for l in lines):
        raise ValueError('wrong or duplicate deployment experiment')
    parser=Path(__file__).resolve().parents[2]/'artifacts/wifi-p2ed-host-cohort-4/experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/deployment_receipt.py'
    if parser.is_symlink() or digest(parser.read_bytes())!='a2dc643ddedf5c9c93ede43598208cafd17242fccbb45db6ddaf078f30ae6f23':
        raise ValueError('reviewed deployment parser changed')
    translated='\n'.join('experiment=a53-authenticated-baseline' if l==original else l for l in lines)
    if runpy.run_path(str(parser))['receipt'](translated,BOOT2,MANIFEST)!=previous:
        raise ValueError('deployment belongs to another Gemian boot')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-dir',type=Path,required=True)
    parser.add_argument('--receipt',type=Path)
    parser.add_argument('--previous-gemian-boot')
    args=parser.parse_args()
    if bool(args.receipt)!=bool(args.previous_gemian_boot):
        parser.error('receipt and previous Gemian boot are required together')
    validate(args.candidate_dir)
    if args.receipt:
        validate_receipt(args.receipt,args.previous_gemian_boot)
    print('exact_yield_candidate=verified; device_action=none')
