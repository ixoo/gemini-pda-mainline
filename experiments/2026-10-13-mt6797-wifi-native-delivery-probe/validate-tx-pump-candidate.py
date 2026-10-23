#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only exact pump candidate check, shared with the guarded installer."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import runpy

MANIFEST='16eb08d56be896e0d607b12142aaee6e52e95a1332a7f669932fe1e529d5ac9f'
BOOT2='e33c85f94b1217918ffe4bb886195fa469c564a49684b4f9c3fc62234540970d'
BOOT='08bab27ae571e6e8e59e6d2112e9b30736148b750b28950861cdd7a4e03fe038'
NOTES='e875f110f15fefaba186133a7092c5476566ce3262de927d8d73db7c99622c22'
COMMIT='23745fe907c48ae0137cf5151b1117770545ce07'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate(candidate):
    if candidate.is_symlink():
        raise ValueError('symlink candidate refused')
    candidate=candidate.resolve(strict=True)
    raw=(candidate/'candidate.json').read_bytes()
    if digest(raw)!=MANIFEST:
        raise ValueError('pump manifest changed')
    value=json.loads(raw)
    if (candidate.name!='candidate-'+BOOT or
        {p.name for p in candidate.iterdir()}!=set(value['files'])|{'candidate.json'}):
        raise ValueError('pump candidate inventory changed')
    for name,identity in value['files'].items():
        path=candidate/name
        if (path.is_symlink() or not path.is_file() or
            path.stat().st_size!=identity['bytes'] or digest(path.read_bytes())!=identity['sha256']):
            raise ValueError('pump member changed: '+name)
    if (value['kernel_build_commit']!=COMMIT or
        value['kernel_profile']!='mt6797-a53-wifi-tx-pump-measurement' or
        value['files']['boot2-padded.img']['sha256']!=BOOT2 or
        value['files']['boot2-padded.img']['bytes']!=16777216 or
        value['kernel_notes_sha256']!=NOTES or value['kernel_notes_bytes']!=84 or
        value['snapshot_enabled'] or value['key_reuse'] or value['reconnect']):
        raise ValueError('pump identity/admission contract changed')
    image=gzip.decompress((candidate/'Image.gz').read_bytes())
    if digest(image[0xc4d758:0xc4d7ac])!=NOTES:
        raise ValueError('Image notes do not match reviewed System.map identity')
    config=(candidate/'kernel.config').read_text()
    if ('CONFIG_MT6797_CCMP_TX_PUMP=y\n' not in config or
        'CONFIG_MT6797_CCMP_LIFETIME_PREREQUISITES=y\n' in config or
        'CONFIG_CFG80211_DEBUGFS=y\n' in config):
        raise ValueError('pump config changed')
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
    print('exact_pump_candidate=verified; device_action=none')
