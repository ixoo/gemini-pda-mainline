#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive and independently validate a RAM-only no-workload boot candidate.

Output is an offline composition, not deployment authorization. No device IO.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO=Path(__file__).resolve().parents[3]
BUILD='c2ddeea9cccb85ef28d7bacafa376d7adea7e478'
PACKAGE='linux-7.1.3-gemini-gemini-thermal-snapshot-candidate-22d22d94-8fe1675a'
OLD='candidate-mt6797-a72-frequency-zero-divider-398ca636'
NODE='/chosen/gemini-late-cpu-provenance'
INPUTS={
 'SHA256SUMS':'c9d107fe6e6291aeed76c6f7afe0d6a0fc363b6b7bb396c2e43f89f0edafd3cf',
 'Image.gz':'c7cbd7086daed5913ce6b123b628fe57a22905dd088f3a195896cbddc2af5d78',
 'kernel.config':'31139f006eb177b841348c321c0a552f0cb99a69cab867aad9b59304f7e5d66c',
 'provenance/build.json':'cde283df4858b0185f0005f296d0ae7dc56022e5e5ecbb46ada53f403c366460',
 'provenance/a41-record.json':'1105cb4c6c9ff8df5146e3345645eb1d8b032ff6de935e63f3c3e7b11db5e521',
 'dtbs/mediatek/mt6797-gemini-pda.dtb':'20dc368731165d5ffdcbb9bc5dac376fd33b0e182335114ccf2694f621d99c25',
}

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def require(condition, reason):
    if not condition: raise ValueError(reason)
def pinned(path, sha):
    require(path.is_file() and not path.is_symlink() and digest(path)==sha,'input identity: '+str(path.relative_to(REPO)))
    return path

def module(relative, sha, name):
    path=pinned(REPO/relative,sha)
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    sys.modules[name]=result
    spec.loader.exec_module(result)
    return result

def run(args):
    result = subprocess.run([str(a) for a in args],capture_output=True,text=True)
    if result.returncode: raise ValueError(result.stderr.strip())
    return result.stdout

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    output=args.output.absolute()
    allowed=REPO/'artifacts/thermal-snapshot-composition'
    require(output.parent==allowed and output.name=='candidate-c2ddeea9','managed output path')
    require(not output.exists() and not output.is_symlink(),'output already exists')
    allowed.mkdir(mode=0o700,exist_ok=True)
    require(not allowed.is_symlink(),'managed root is a symlink')
    package=REPO/'artifacts/buildbox'/BUILD/PACKAGE
    for name,sha in INPUTS.items(): pinned(package/name,sha)
    for line in (package/'SHA256SUMS').read_text().splitlines():
        sha,name=line.split('  ',1)
        require(name.startswith('./') and '..' not in Path(name).parts,'package manifest path')
        pinned(package/name,sha)
    build=json.loads((package/'provenance/build.json').read_text())
    require(build['repository_commit']==BUILD and build['repository_dirty'] is False,'build revision')
    require(build['build_profile']=='gemini-thermal-snapshot-candidate' and build['kernel_release']=='7.1.3-gemini-thermal-snapshot','build profile')
    baseline=REPO/'artifacts/mt6797-a72-frequency-observation-zero-divider-candidate'/OLD
    base=pinned(baseline/'mt6797-gemini-pda-a72-frequency-thermal.dtb','46be0ae62bf66bf8e9f905ec3ad5eebbdc51c79ff3dc21859077ebe3f1aec363')
    ramdisk=pinned(baseline/'gemini-a72-frequency-thermal-initramfs.img','e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f')
    fdt=module('experiments/2026-08-30-mainline-a72-provenance-serviceability-composition/scripts/validate-composed-dtb.py','b76e7fa49f6f02c948a7563613c502d67ef287f0cba0db224d17f312427fe438','snapshot_fdt')
    cpu=module('experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/validate-cpu-map.py','99495d59d047f312f416076b788014a64d267cbe4bf899a59d0120d5dd22d7c5','snapshot_cpu_map')
    serializer=pinned(REPO/'experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py','569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4')
    analyzer=pinned(REPO/'experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py','aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95')
    original,reservations,boot_cpu=fdt.parse_fdt(base)
    record=json.loads((package/'provenance/a41-record.json').read_text())
    leaf=fdt.expected_record(record)
    packaged,_,_=fdt.parse_fdt(package/'dtbs/mediatek/mt6797-gemini-pda.dtb')
    require(packaged[NODE]==leaf and original[NODE].keys()==leaf.keys(),'record leaf shape')
    expected=copy.deepcopy(original);expected[NODE]=leaf
    def validate_dtb(path):
        actual,r,b=fdt.parse_fdt(path)
        require((actual,r,b)==(expected,reservations,boot_cpu),'DT delta outside exact provenance leaf')
    with tempfile.TemporaryDirectory(prefix='.derive.',dir=allowed) as work:
        root=Path(work); stage=root/'stage';stage.mkdir(mode=0o700)
        for name in ('first','second'):
            dtb=root/(name+'.dtb');shutil.copyfile(base,dtb)
            for prop,value in leaf.items():
                run(['fdtput','-t','bx',dtb,NODE,prop,*[f'{byte:x}' for byte in value]])
            validate_dtb(dtb);cpu.validate(dtb)
        require((root/'first.dtb').read_bytes()==(root/'second.dtb').read_bytes(),'DT reproduction mismatch')
        # Mutation checks use independent parsed-tree comparison.
        for kind in ('extra-property','wrong-record'):
            mutant=root/'mutant.dtb';shutil.copyfile(root/'first.dtb',mutant)
            if kind=='extra-property': run(['fdtput','-t','s',mutant,'/','unexpected-property','x'])
            else: run(['fdtput','-t','bx',mutant,NODE,'record-identity',*(['0']*32)])
            try: validate_dtb(mutant)
            except ValueError: pass
            else: raise ValueError('DT mutation accepted: '+kind)
        shutil.copyfile(root/'first.dtb',stage/'candidate.dtb')
        shutil.copyfile(package/'Image.gz',stage/'Image.gz')
        shutil.copyfile(ramdisk,stage/'initramfs.img')
        for name in ('first','second'):
            run([sys.executable,serializer,'--kernel',stage/'Image.gz','--ramdisk',stage/'initramfs.img',
                 '--dtb',stage/'candidate.dtb','--output',root/(name+'.img'),'--name','gemini-tsnap',
                 '--cmdline','bootopt=64S3,32N2,64N2','--kernel-addr','0x40200000','--ramdisk-addr','0x45000000',
                 '--second-addr','0x40f00000','--tags-addr','0x44000000','--lk-android8'])
        raw=(root/'first.img').read_bytes()
        require(raw==(root/'second.img').read_bytes(),'container reproduction mismatch')
        require(0<len(raw)<16777216,'boot2 capacity')
        (stage/'candidate.boot.img').write_bytes(raw)
        (stage/'boot2-padded.img').write_bytes(raw+bytes(16777216-len(raw)))
        analysis=run([sys.executable,analyzer,'--validate-lk','--expected-image-gz',stage/'Image.gz',
                      '--expected-ramdisk',stage/'initramfs.img','--expected-dtb',stage/'candidate.dtb',
                      '--expected-name','gemini-tsnap','--expected-cmdline','bootopt=64S3,32N2,64N2',stage/'candidate.boot.img'])
        (stage/'container-validation.txt').write_text(analysis)
        result={'build_revision':BUILD,'package':PACKAGE,'release':build['kernel_release'],
                'record_identity':record['record_identity'],'candidate_raw_size':len(raw),
                'candidate_raw_sha256':digest(stage/'candidate.boot.img'),
                'candidate_padded_sha256':digest(stage/'boot2-padded.img'),
                'dtb_sha256':digest(stage/'candidate.dtb'),'initramfs_sha256':digest(ramdisk),
                'dt_delta':'exact-package-provenance-leaf-only','dt_mutations_rejected':2,
                'independent_DT_compositions':2,'independent_container_assemblies':2,
                'device_action':'none','classification':'offline-composition-not-deployed'}
        frozen = {
            'candidate_raw_sha256':'a4947cfe8079f9e9864f0edf1b30a446b9eb5089fb69e66f950d9901f2654ee0',
            'candidate_padded_sha256':'666961b636b21b8598a64999e9dbf72af280ad99f07a6b745045320f24ca361b',
            'dtb_sha256':'c8e0a1483704acb4f6ec9843d2a04284059378543e44fac521bbea132d62b525',
            'candidate_raw_size':7131136,
        }
        require(all(result[k]==v for k,v in frozen.items()),'frozen composition identity changed')
        (stage/'composition.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        for path in stage.iterdir(): path.chmod(0o600)
        (stage/'SHA256SUMS').write_text(''.join(digest(p)+'  '+p.name+'\n' for p in sorted(stage.iterdir())))
        (stage/'SHA256SUMS').chmod(0o600)
        os.rename(stage,output)
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__': main()
