#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Assemble private startup inputs in the RE VM; contains no init or trigger."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
RUNTIME_SHA256 = '7ff2ebf4153d8055f92f3baa1c550a3376b913e680162de60a3557ca2d855294'
INPUTS = {
    'ROMv3_patch_1_1_hdr.bin': ('lib/firmware/ROMv3_patch_1_1_hdr.bin', 46472),
    'ROMv3_patch_1_0_hdr.bin': ('lib/firmware/ROMv3_patch_1_0_hdr.bin', 210904),
    'WMT_SOC.cfg': ('lib/firmware/WMT_SOC.cfg', 80),
    'WIFI_RAM_CODE_6797': ('vendor/firmware/WIFI_RAM_CODE_6797', 411632),
    'WIFI': ('data/nvram/APCFG/APRDEB/WIFI', 514),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    if len(sys.argv) != 4 or platform.system() != 'Linux':
        raise SystemExit('usage in RE VM: build-startup-filesystem.py PRIVATE_INPUTS RUNTIME_TAR NEW_PACKAGE')
    private, runtime, package = (Path(value).resolve() for value in sys.argv[1:])
    if package.exists() or not package.parent.is_dir():
        raise ValueError('requires a new package in an existing parent')
    if shutil.disk_usage(package.parent).free < 1024 ** 3:
        raise ValueError('requires 1 GiB free')
    if runtime.is_symlink() or digest(runtime) != RUNTIME_SHA256:
        raise ValueError('runtime archive mismatch')
    if {p.name for p in private.iterdir()} != set(INPUTS) | {'manifest.json'}:
        raise ValueError('private input inventory mismatch')
    manifest = json.loads((private / 'manifest.json').read_text())
    if set(manifest['files']) != set(INPUTS):
        raise ValueError('private manifest roles mismatch')
    files = {}
    for name, (target, size) in INPUTS.items():
        source = private / name
        if source.is_symlink() or not source.is_file() or source.stat().st_size != size:
            raise ValueError('private input type or size mismatch')
        expected = manifest['files'][name]
        if expected['size'] != size or digest(source) != expected['sha256']:
            raise ValueError('private input checksum mismatch')
        files[target] = {'size': size, 'sha256': expected['sha256']}
    calibration = PROJECT / 'experiments/2026-09-05-mt6797-wifi-contract/scripts'
    sys.path.insert(0, str(calibration))
    storage = module('wifi_storage', calibration / 'wifi_nvram_storage.py')
    inspected = storage.inspect_storage((private / 'WIFI').read_bytes(),
                                         driver_own_version=0x200, driver_peer_version=0)
    if not inspected['source_record_versions_compatible']:
        raise ValueError('retained calibration version predicate failed')
    module('retained_patches', HERE / 'check-retained-patches.py').check_directory(private)
    # The runtime archive is pinned and its symlink entries were reviewed.
    # Reject any input role already supplied by that archive.
    with tarfile.open(runtime) as archive:
        members = archive.getmembers()
        names = {m.name.removeprefix('./') for m in members}
        if any(name in names for name in ('init', 'lib/firmware', 'vendor', 'data')):
            raise ValueError('runtime already supplies startup inputs')
    # Caller serializes this output directory; only managed unfinished staging.
    for stale in package.parent.glob('.wifi-startup-filesystem-*'):
        if stale.is_symlink() or not stale.is_dir():
            raise ValueError('unsafe stale staging directory')
        shutil.rmtree(stale)
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix='.wifi-startup-filesystem-', dir=package.parent) as tmp:
        work = Path(tmp)
        root = work / 'root'
        root.mkdir()
        subprocess.run(['tar', '--no-same-owner', '--same-permissions', '-xzf', str(runtime),
                        '-C', str(root)], check=True)
        for name, (target, _) in INPUTS.items():
            destination = root / target
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(private / name, destination)
            destination.chmod(0o400)
        identity = {'runtime_sha256': RUNTIME_SHA256, 'files': files,
                    'private_origin_manifest_sha256': digest(private / 'manifest.json')}
        target = root / 'etc/wifi-cycle/input-manifest.json'
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(identity, sort_keys=True, indent=2) + '\n')
        target.chmod(0o400)
        paths = [root] + sorted(root.rglob('*'))
        for path in paths:
            if not path.is_symlink() and path.is_dir():
                path.chmod(0o1777 if path == root / 'tmp' else 0o755)
            os.utime(path, (0, 0), follow_symlinks=False)
        listing = b'\0'.join(str(p.relative_to(root)).encode() for p in paths) + b'\0'
        output = work / 'package'
        output.mkdir()
        cpio = work / 'rootfs.cpio'
        with cpio.open('wb') as destination:
            subprocess.run(['cpio', '--null', '--create', '--format=newc', '--owner=0:0',
                            '--reproducible', '--quiet'], cwd=root, input=listing,
                           stdout=destination, check=True)
        with (output / 'rootfs.cpio.gz').open('wb') as destination:
            subprocess.run(['gzip', '-n', '-9', '-c', str(cpio)], stdout=destination, check=True)
        for target, expected in files.items():
            if digest(root / target) != expected['sha256']:
                raise ValueError('copied input mismatch')
        if (root / 'init').exists() or (root / 'storage').exists():
            raise ValueError('unexpected startup or earlier WLAN lookup')
        shutil.copyfile(root / 'etc/wifi-cycle/input-manifest.json', output / 'input-manifest.json')
        receipt = {'scope': 'private input filesystem; no init, trigger or boot admission',
                   'builder_sha256': digest(Path(__file__)), 'runtime_sha256': RUNTIME_SHA256,
                   'input_manifest_sha256': digest(output / 'input-manifest.json'),
                   'filesystem_sha256': digest(output / 'rootfs.cpio.gz'),
                   'filesystem_bytes': (output / 'rootfs.cpio.gz').stat().st_size,
                   'members': len(paths), 'private_input_files': len(INPUTS),
                   'calibration_storage_bytes_preserved': 514,
                   'calibration_envelope': 'matched; not proof of authenticity or applicability'}
        (output / 'private-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
        (output / 'SHA256SUMS').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in sorted(output.iterdir())))
        output.rename(package)
        print('startup_input_filesystem=assembled private_inputs=5 init=absent device_access=none')
        print('filesystem_bytes=' + str(receipt['filesystem_bytes']))


if __name__ == '__main__':
    main()
