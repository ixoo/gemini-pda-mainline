#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only exact quiet-console candidate check, shared with the guarded installer."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import runpy

MANIFEST='6abba2a5e72d0b13623e6295ff715fb2934adced331935757bd0ee86e4c6e373'  # Seal from the composed quiet-console candidate.
BOOT2='da4fadcc6f8efd0e934d602f8b82e37420c2c38247b2ef2f39fca8685452b8ba'
BOOT='a4158f4185527d3cd63260172821f73d4b762fd491e48d29324792b1c9b9911b'
NOTES='4eba0b543c0c2d52f31f6a83a1113b107926714960938895ef7bd70c9a4dc69f'
NOTES_OFFSET=12900184
COMMIT='7237af148aa5eeeeab40d34ce93bd21f3d3013a6'  # Seal from the pushed quiet-console build input.
PROFILE='mt6797-a53-wifi-quiet-console'
RELEASE='7.1.3-gemini-a53-private-p2e-delivery'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate(candidate):
    if None in (MANIFEST, BOOT2, BOOT, NOTES, NOTES_OFFSET, COMMIT):
        raise ValueError('quiet-console candidate binding is not sealed')
    if candidate.is_symlink():
        raise ValueError('symlink candidate refused')
    candidate=candidate.resolve(strict=True)
    raw=(candidate/'candidate.json').read_bytes()
    if digest(raw)!=MANIFEST:
        raise ValueError('quiet-console manifest changed')
    value=json.loads(raw)
    if (candidate.name!='candidate-'+BOOT or
        {p.name for p in candidate.iterdir()}!=set(value['files'])|{'candidate.json'}):
        raise ValueError('quiet-console candidate inventory changed')
    for name,identity in value['files'].items():
        path=candidate/name
        if (path.is_symlink() or not path.is_file() or
            path.stat().st_size!=identity['bytes'] or digest(path.read_bytes())!=identity['sha256']):
            raise ValueError('quiet-console member changed: '+name)
    if (value['kernel_build_commit']!=COMMIT or
        value['kernel_profile']!=PROFILE or value['kernel_release']!=RELEASE or
        value['files']['boot2-padded.img']['sha256']!=BOOT2 or
        value['files']['boot2-padded.img']['bytes']!=16777216 or
        value['kernel_notes_sha256']!=NOTES or value['kernel_notes_bytes']!=84 or
        value.get('tx_pump_pending_yield_ms')!=1 or value.get('tx_pump_progress_resets') is not True or
        value.get('tx_pump_data_phase_pending') is not False or
        value.get('console_loglevel')!=4 or value.get('ignore_loglevel') is not False or
        set(value.get('kernel_config_change',{}))!={'CONFIG_CMDLINE'} or
        value.get('data_tx_depth')!=4 or value.get('kernel_notes_offset')!=NOTES_OFFSET or
        value['snapshot_enabled'] or value['key_reuse'] or value['reconnect']):
        raise ValueError('quiet-console identity/admission contract changed')
    image=gzip.decompress((candidate/'Image.gz').read_bytes())
    if digest(image[NOTES_OFFSET:NOTES_OFFSET+84])!=NOTES:
        raise ValueError('Image notes do not match reviewed System.map identity')
    config=(candidate/'kernel.config').read_text()
    cmdline=[l for l in config.splitlines() if l.startswith('CONFIG_CMDLINE=')]
    if ('CONFIG_MT6797_CCMP_TX_PUMP=y\n' not in config or
        'CONFIG_MT6797_CCMP_TX_DEPTH=4\n' not in config or
        'CONFIG_MT6797_CCMP_LIFETIME_PREREQUISITES=y\n' in config or
        'CONFIG_CFG80211_DEBUGFS=y\n' in config or
        'CONFIG_LOCALVERSION="-gemini-a53-private-p2e-delivery"\n' not in config or
        len(cmdline)!=1 or ' loglevel=4 ' not in cmdline[0] or 'ignore_loglevel' in cmdline[0]):
        raise ValueError('quiet-console config changed')
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
    print('exact_quiet_console_candidate=verified; device_action=none')
