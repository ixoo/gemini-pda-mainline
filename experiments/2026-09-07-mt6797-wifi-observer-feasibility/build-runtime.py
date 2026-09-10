#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Package and test an ARM64 runtime subset; no init, firmware or device access."""
import hashlib
import json
import lzma
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
SOURCES = ('cycle-controller.py', 'respond-once.py', 'check-retained-patches.py')
TESTS = ('test-cycle-controller.py', 'test-respond-once.py')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, **kwargs):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False, **kwargs)
    if result.returncode:
        raise RuntimeError(f'{args[0]} exited {result.returncode}:\n{result.stdout}')
    return result.stdout


def fetch(cache, name, url, expected):
    target = cache / name
    if not target.exists():
        with tempfile.NamedTemporaryFile(dir=cache, prefix='.wifi-runtime-download-', delete=False) as out:
            temporary = Path(out.name)
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    shutil.copyfileobj(response, out)
                out.flush()
                if digest(temporary) != expected:
                    raise ValueError('download checksum mismatch')
                temporary.rename(target)
            finally:
                temporary.unlink(missing_ok=True)
    if target.is_symlink() or digest(target) != expected:
        raise ValueError(f'cached input mismatch: {name}')
    return target


def main():
    if len(sys.argv) != 3 or platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise SystemExit('usage on Linux x86_64 with ARM64 QEMU: build-runtime.py CACHE NEW_PACKAGE')
    cache, package = (Path(arg).resolve() for arg in sys.argv[1:])
    cache.mkdir(parents=True, exist_ok=True)
    if package.exists() or not package.parent.is_dir():
        raise ValueError('package must be new, with an existing parent')
    if shutil.disk_usage(package.parent).free < 1024 ** 3:
        raise ValueError('requires 1 GiB free')
    # Caller serializes this cache/output pair. Only this builder's temporary
    # names may be removed after an interrupted run; completed packages remain.
    for stale in cache.glob('.wifi-runtime-download-*'):
        if stale.is_symlink() or not stale.is_file():
            raise ValueError('unsafe stale download')
        stale.unlink()
    for stale in package.parent.glob('.wifi-runtime-staging-*'):
        if stale.is_symlink() or not stale.is_dir():
            raise ValueError('unsafe stale staging directory')
        shutil.rmtree(stale)
    pins = json.loads((HERE / 'runtime-inputs.json').read_text())
    repository = pins['repository']
    release = fetch(cache, 'InRelease', repository + '/dists/bookworm/InRelease', pins['release_sha256'])
    signature = run(['gpgv', '--keyring', '/usr/share/keyrings/debian-archive-keyring.gpg', str(release)])
    if '4CB50190207B4758A3F73A796ED0E7B82643E131' not in signature:
        raise ValueError('missing selected Bookworm archive signer')
    index = fetch(cache, 'Packages.xz', repository + '/dists/bookworm/main/binary-arm64/Packages.xz',
                  pins['packages_index_sha256'])
    row = [pins['packages_index_sha256'], str(index.stat().st_size), 'main/binary-arm64/Packages.xz']
    if not any(line.split() == row for line in release.read_text().splitlines()):
        raise ValueError('index is not in signed release')
    commit = run(['git', '-C', str(PROJECT), 'rev-parse', 'HEAD']).strip()
    if run(['git', '-C', str(PROJECT), 'status', '--porcelain']).strip():
        raise ValueError('requires a clean project checkout')
    indexed = {}
    for paragraph in lzma.decompress(index.read_bytes()).decode().split('\n\n'):
        fields = dict(line.split(': ', 1) for line in paragraph.splitlines()
                      if ': ' in line and not line.startswith(' '))
        if 'Package' in fields:
            indexed[fields['Package']] = fields
    for item in pins['packages']:
        fields = indexed[item['name']]
        for key, field in (('version', 'Version'), ('architecture', 'Architecture'),
                           ('path', 'Filename'), ('size', 'Size'), ('sha256', 'SHA256')):
            if str(item[key]) != fields[field]:
                raise ValueError('package pin is not in authenticated index')
    source_hashes = {name: digest(HERE / name) for name in SOURCES + TESTS}
    qemu = Path(shutil.which('qemu-aarch64-static'))
    with tempfile.TemporaryDirectory(prefix='.wifi-runtime-staging-', dir=package.parent) as temporary:
        work = Path(temporary)
        root = work / 'root'
        root.mkdir()
        for item in pins['packages']:
            archive = fetch(cache, Path(item['path']).name, repository + '/' + item['path'], item['sha256'])
            if archive.stat().st_size != item['size']:
                raise ValueError('package size mismatch')
            fields = run(['dpkg-deb', '-f', str(archive), 'Package', 'Version', 'Architecture'])
            expected = f"Package: {item['name']}\nVersion: {item['version']}\nArchitecture: {item['architecture']}\n"
            if fields != expected:
                raise ValueError('package control identity mismatch')
            run(['dpkg-deb', '-x', str(archive), str(root)])
        # Extraction runs no maintainer scripts and starts no service.
        controller = root / 'opt/wifi-cycle'
        controller.mkdir(parents=True)
        for name in SOURCES + TESTS:
            shutil.copyfile(HERE / name, controller / name)
        (root / 'tmp').mkdir(exist_ok=True)
        (root / 'tmp').chmod(0o1777)
        shutil.copyfile(qemu, root / 'qemu-aarch64-static')
        (root / 'qemu-aarch64-static').chmod(0o755)
        prefix = ['unshare', '--user', '--map-root-user', shutil.which('chroot'), str(root),
                  '/qemu-aarch64-static']
        # Chroot excludes host ARM64 libraries and Python modules. QEMU translates
        # syscalls to the host kernel; it does not emulate the PDA's Linux 3.18.
        environment = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}
        log = run(prefix + ['/usr/bin/python3.11', '-I', '-B', '-c',
                  'import sys,platform,struct,hashlib,time; '
                  'assert platform.machine()=="aarch64" and struct.calcsize("P")==8; '
                  'assert sys.byteorder=="little"; '
                  'assert hashlib.sha256(b"abc").hexdigest()=='
                  '"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"; '
                  'assert time.monotonic_ns()>0; print(sys.version)'], env=environment, timeout=60)
        for name in TESTS:
            log += run(prefix + ['/usr/bin/python3.11', '-I', '-B', '/opt/wifi-cycle/' + name],
                       env=environment, timeout=60)
            (controller / name).unlink()
        log += run(prefix + ['/bin/busybox', 'sh', '-c', 'echo busybox-runtime-pass'],
                   env=environment, timeout=30)
        (root / 'qemu-aarch64-static').unlink()
        # No firmware and no init: this archive cannot start the observation.
        assert not (root / 'init').exists()
        output = work / 'package'
        output.mkdir()
        tar = work / 'runtime.tar'
        run(['tar', '--sort=name', '--mtime=@0', '--owner=0', '--group=0', '--numeric-owner',
             '-cf', str(tar), '-C', str(root), '.'])
        with (output / 'runtime.tar.gz').open('wb') as destination:
            subprocess.run(['gzip', '-n', '-9', '-c', str(tar)], stdout=destination, check=True)
        (output / 'test.log').write_text(log)
        (output / 'signature.log').write_text(signature)
        receipt = {'scope': 'offline ARM64 runtime, not boot candidate or hardware evidence',
                   'repository_commit': commit, 'inputs_sha256': digest(HERE / 'runtime-inputs.json'),
                   'sources': source_hashes, 'packages': len(pins['packages']),
                   'qemu_version': run([str(qemu), '--version']).splitlines()[0],
                   'qemu_sha256': digest(qemu), 'root_bytes': sum(p.stat().st_size for p in root.rglob('*')
                       if p.is_file() and not p.is_symlink()),
                   'runtime_sha256': digest(output / 'runtime.tar.gz'),
                   'runtime_bytes': (output / 'runtime.tar.gz').stat().st_size,
                   'tests': list(TESTS), 'test_environment': 'user-namespace chroot, QEMU user-mode, host kernel'}
        if source_hashes != {name: digest(HERE / name) for name in SOURCES + TESTS}:
            raise ValueError('controller inputs changed during packaging')
        (output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
        (output / 'SHA256SUMS').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in sorted(output.iterdir())))
        output.rename(package)
        print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
