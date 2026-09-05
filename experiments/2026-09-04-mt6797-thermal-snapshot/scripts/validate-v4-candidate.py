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
EXPECTED={'Image.gz': 'dfc47d82176de99e68e8cd28305d5732a02d0cfe64f1424554876c7d3186ad34', 'boot2-padded.img': 'b007af3d7025b804b34c6f1e717b2eca5e9fecf09b0ff731cede2a12116d993c', 'candidate.boot.img': '0430cee5f6891f48c90d5ab196c7d9141cd50870efe44c3328499e7d89b20fd2', 'candidate.dtb': '94f5ee8ae61b938b1717ab0990d16dddeb883bd556f8794efa6e1b97b84b4a72', 'composition.json': 'adb8b5af8863b517756087b9b4c1dd92a908545a952ad6abc53a9d0deb921071', 'container-validation.txt': 'ccb104c8416ff56b191a116321608bf838a8b828c8b68327f493f2f6cc281919', 'initramfs.img': 'e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f'}

def require(condition, reason):
    if not condition: raise ValueError(reason)

def padding(raw, padded):
    require(len(raw)==7131136 and len(padded)==16777216,'candidate size')
    require(padded[:len(raw)]==raw and not any(padded[len(raw):]),'padding content')

def manifest(raw):
    observed={}
    for line in raw.splitlines():
        sha,sep,name=line.partition('  ')
        require(sep and name not in observed and name in EXPECTED,'manifest inventory')
        observed[name]=sha
    require(observed==EXPECTED,'manifest identities')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,required=True)
    args=parser.parse_args(); candidate=args.candidate.absolute()
    require(candidate==REPO/'artifacts/thermal-snapshot-composition/candidate-v4-ba906730','candidate path')
    require(candidate.is_dir() and not candidate.is_symlink(),'candidate directory')
    require({p.name for p in candidate.iterdir()}==set(EXPECTED)|{'SHA256SUMS'},'candidate inventory')
    require(not (candidate/'SHA256SUMS').is_symlink(),'manifest symlink')
    manifest((candidate/'SHA256SUMS').read_text())
    for name,sha in EXPECTED.items():
        path=candidate/name
        require(path.is_file() and not path.is_symlink(),'candidate file')
        require(hashlib.sha256(path.read_bytes()).hexdigest()==sha,'candidate checksum '+name)
    good=(candidate/'SHA256SUMS').read_text()
    lines=good.splitlines(keepends=True)
    for bad in (good+lines[0], ''.join(lines[1:]), good+'0'*64+'  extra\n', good.replace(EXPECTED['Image.gz'],'0'*64)):
        try: manifest(bad)
        except ValueError: pass
        else: raise ValueError('manifest mutation accepted')
    raw=(candidate/'candidate.boot.img').read_bytes(); padded=(candidate/'boot2-padded.img').read_bytes()
    padding(raw,padded)
    analyzer=REPO/'experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py'
    require(hashlib.sha256(analyzer.read_bytes()).hexdigest()=='aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95','analyzer identity')
    command=[sys.executable,str(analyzer),'--validate-lk','--expected-image-gz',str(candidate/'Image.gz'),
             '--expected-ramdisk',str(candidate/'initramfs.img'),'--expected-dtb',str(candidate/'candidate.dtb'),
             '--expected-name','gemini-tv4','--expected-cmdline','bootopt=64S3,32N2,64N2']
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
                      'padding_mutations_rejected':2,'manifest_mutations_rejected':4,'device_action':'none'},indent=2,sort_keys=True))

if __name__=='__main__': main()
