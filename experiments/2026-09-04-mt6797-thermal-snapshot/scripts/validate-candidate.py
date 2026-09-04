#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate frozen offline candidate bytes and reject container mutations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

REPO=Path(__file__).resolve().parents[3]
EXPECTED={
 'candidate.boot.img':'a4947cfe8079f9e9864f0edf1b30a446b9eb5089fb69e66f950d9901f2654ee0',
 'boot2-padded.img':'666961b636b21b8598a64999e9dbf72af280ad99f07a6b745045320f24ca361b',
 'candidate.dtb':'c8e0a1483704acb4f6ec9843d2a04284059378543e44fac521bbea132d62b525',
 'Image.gz':'c7cbd7086daed5913ce6b123b628fe57a22905dd088f3a195896cbddc2af5d78',
 'initramfs.img':'e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f',
}

def require(condition, reason):
    if not condition: raise ValueError(reason)

def padding(raw, padded):
    require(len(raw)==7131136 and len(padded)==16777216,'candidate size')
    require(padded[:len(raw)]==raw and not any(padded[len(raw):]),'padding content')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,required=True)
    args=parser.parse_args(); candidate=args.candidate.absolute()
    require(candidate==REPO/'artifacts/thermal-snapshot-composition/candidate-c2ddeea9','candidate path')
    for name,sha in EXPECTED.items():
        path=candidate/name
        require(path.is_file() and not path.is_symlink(),'candidate file')
        require(hashlib.sha256(path.read_bytes()).hexdigest()==sha,'candidate checksum '+name)
    raw=(candidate/'candidate.boot.img').read_bytes(); padded=(candidate/'boot2-padded.img').read_bytes()
    padding(raw,padded)
    analyzer=REPO/'experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py'
    require(hashlib.sha256(analyzer.read_bytes()).hexdigest()=='aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95','analyzer identity')
    command=[sys.executable,str(analyzer),'--validate-lk','--expected-image-gz',str(candidate/'Image.gz'),
             '--expected-ramdisk',str(candidate/'initramfs.img'),'--expected-dtb',str(candidate/'candidate.dtb'),
             '--expected-name','gemini-tsnap','--expected-cmdline','bootopt=64S3,32N2,64N2']
    subprocess.run(command+[str(candidate/'candidate.boot.img')],capture_output=True,check=True)
    with tempfile.TemporaryDirectory(prefix='.validate.',dir=candidate.parent) as work:
        mutant=Path(work)/'mutant.img'
        for offset in (0,48):
            data=bytearray(raw);data[offset]^=1;mutant.write_bytes(data)
            result=subprocess.run(command+[str(mutant)],capture_output=True)
            require(result.returncode!=0,'header mutation accepted')
        for data in (padded[:-1],padded[:-1]+b'\x01'):
            try: padding(raw,data)
            except ValueError: pass
            else: raise ValueError('padding mutation accepted')
    print(json.dumps({'classification':'frozen-offline-candidate-pass','candidate_padded_sha256':EXPECTED['boot2-padded.img'],
                      'candidate_raw_sha256':EXPECTED['candidate.boot.img'],'container_mutations_rejected':2,
                      'padding_mutations_rejected':2,'device_action':'none'},indent=2,sort_keys=True))

if __name__=='__main__': main()
