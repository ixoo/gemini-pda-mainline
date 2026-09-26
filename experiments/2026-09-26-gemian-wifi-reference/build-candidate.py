#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Assemble the pinned Gemian Wi-Fi kernel into an offline boot2 image."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = '59e00a9144d782e148332009a835b99c43382467'
BUILDS = {
    'v1': {
        'commit': 'bf079c8be55e623b9fb5bc0e51a6a3feaed55f94',
        'inventory': '7822d68966364b16e943f76d7e56f9ffaa3a5ebfa978bec09d366d466d480205',
        'kernel': '327dd5e4e27632de69b8b578a7b51a9df9f110b843223fca45cc003e63e48473',
    },
    'v2': {
        'commit': '6f6487e7ace7d0af8135b9d5ba76b3bcd8066aeb',
        'inventory': '49a4dca4703ad9a690b463f89552193018237353484a7bbdee60d8c337000e4b',
        'kernel': '996135ddfa203e2bf61d826b5382b302c10195d7d03a9fe8c6f2843da408b21b',
    },
}
ASSEMBLER = (REPO / 'experiments/2026-08-02-gemian-a72-bounded-observer-boot'
             / 'scripts/assemble.py')
ASSEMBLER_SHA = '532f6f0dec5030a7b066f3baefa53580ec148317f633d4dd8d43308d30ac03b3'
BOOT_SHA = '1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513'
SIZE = 16 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    assert path.is_file() and not path.is_symlink(), path
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', choices=BUILDS, default='v1')
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--active-boot', type=Path, required=True)
    parser.add_argument('--output-parent', type=Path, required=True)
    args = parser.parse_args()
    expected = BUILDS[args.revision]
    os.umask(0o077)
    bundle = args.bundle.resolve(strict=True)
    assert bundle.is_dir() and not args.bundle.is_symlink()
    assert digest(regular(bundle / 'SHA256SUMS')) == expected['inventory']
    subprocess.run(['sha256sum', '--check', '--strict', 'SHA256SUMS'],
                   cwd=bundle, check=True, stdout=subprocess.DEVNULL)
    result = json.loads(regular(bundle / 'result.json'))
    assert result['repository_commit'] == expected['commit']
    assert result['source_commit'] == SOURCE
    assert result['full_kernel_link'] is True and result['device_execution'] is False
    kernel = regular(bundle / 'Image.gz-dtb')
    assert digest(kernel) == expected['kernel']
    active = regular(args.active_boot)
    assert len(active) == SIZE and digest(active) == BOOT_SHA
    assert digest(regular(ASSEMBLER)) == ASSEMBLER_SHA
    spec = importlib.util.spec_from_file_location('gemian_boot_assembler', ASSEMBLER)
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    assembler.KERNEL_FIELD_SHA256 = expected['kernel']
    raw, fields = assembler.build(active, kernel)
    padded = raw + bytes(SIZE - len(raw))
    assert len(raw) < SIZE and len(padded) == SIZE
    assert padded[:len(raw)] == raw and not any(padded[len(raw):])
    parent = args.output_parent.resolve(strict=True)
    assert parent.is_dir() and not args.output_parent.is_symlink()
    name = 'candidate-' + digest(padded)
    destination = parent / name
    assert not destination.exists() and not destination.is_symlink()
    with tempfile.TemporaryDirectory(prefix='.gemian-wifi-reference-', dir=parent) as tmp:
        stage = Path(tmp) / name
        stage.mkdir(mode=0o700)
        (stage / 'boot.img').write_bytes(raw)
        (stage / 'boot2-padded.img').write_bytes(padded)
        receipt = {'experiment': '2026-09-26-gemian-wifi-reference',
                   'repository_commit': expected['commit'], 'source_commit': SOURCE,
                   'package_inventory_sha256': expected['inventory'],
                   'assembler_sha256': ASSEMBLER_SHA,
                   'active_boot_sha256': BOOT_SHA,
                   'kernel_field_sha256': expected['kernel'],
                   'raw_sha256': digest(raw), 'raw_bytes': len(raw),
                   'boot2_sha256': digest(padded), 'boot2_bytes': len(padded),
                   'ramdisk_sha256': fields['ramdisk_sha256'],
                   'boot_candidate': True, 'device_execution': False}
        (stage / 'candidate.json').write_text(json.dumps(receipt, indent=2) + '\n')
        (stage / 'SHA256SUMS').write_text(''.join(
            digest((stage / name).read_bytes()) + '  ' + name + '\n'
            for name in ('boot.img', 'boot2-padded.img', 'candidate.json')))
        stage.rename(destination)
    print('candidate=' + str(destination))
    print('boot2_sha256=' + receipt['boot2_sha256'])


if __name__ == '__main__':
    main()
