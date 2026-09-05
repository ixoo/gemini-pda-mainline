#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose one private authenticated initramfs on the exact historical kernel/DT."""
import argparse
from dataclasses import replace
import fcntl
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import stat
import subprocess

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parents[2]
FOUNDATION = runpy.run_path(str(HERE / 'audit_foundation.py'))
regular = FOUNDATION['regular']
digest = FOUNDATION['digest']
require = FOUNDATION['require']
safe_directory = FOUNDATION['safe_directory']
REMOVED = {'bin/usb-net', 'bin/usb-shell', 'bin/local-shell', 'bin/emmc-flash-boot2',
           'bin/x-probe', 'bin/input-event-capture', 'bin/ac-record'}
SOURCES = {'init': 'init', 'inittab': 'etc/inittab', 'usb-auth': 'bin/usb-auth',
           'console-status': 'bin/console-status', 'admin-shell': 'bin/admin-shell'}


def parser_tools():
    parser = REPO / 'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'
    serializer = REPO / 'experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/build-diagnostic-initramfs.py'
    require(digest(regular(parser)) == '19c1c63df5f4732d3cae253a5b7edbb90d0ad609ed1ea411a200dc0060adba9c', 'archive parser changed')
    require(digest(regular(serializer)) == '0abe8a8b02ec3767c21fc018c69cc7e2db5ddb475a00e443247474a582f29f38', 'archive serializer changed')
    return runpy.run_path(str(parser))['parse_newc'], runpy.run_path(str(serializer))['encode_newc']


def userspace_inventory(package, expected):
    sums = regular(package / 'SHA256SUMS')
    require(digest(sums) == expected, 'userspace manifest pin')
    records = sums.decode().splitlines()
    FOUNDATION['inventory'](package, {'manifest_sha256': expected, 'inventory_count': len(records)})
    required = {'dropbear', 'dropbearkey', 'dropbearconvert', 'keyboard-observe', 'kmsg-capture',
                'auth-tests.json', 'localoptions.h', 'effective-options.txt', 'provenance.txt'}
    require(required <= {p.name for p in package.iterdir()}, 'userspace package incomplete')
    require(regular(package / 'localoptions.h') == regular(HERE / 'localoptions.h'), 'server options drift')
    auth = json.loads(regular(package / 'auth-tests.json'))
    require(auth.get('classification') == 'offline-authentication-pass', 'authentication tests missing')
    for binary in ('dropbear', 'keyboard-observe', 'kmsg-capture'):
        data = regular(package / binary)
        require(data[:6] == b'\x7fELF\x02\x01' and data[18:20] == b'\xb7\x00', 'AArch64 binary required')


def credentials(directory):
    directory = safe_directory(directory)
    require(directory == REPO / 'artifacts/credentials/a53-auth', 'unexpected credential bundle')
    require(stat.S_IMODE(directory.stat().st_mode) == 0o700, 'credential directory permissions')
    for path in directory.iterdir():
        require(stat.S_IMODE(path.lstat().st_mode) == 0o600 and path.is_file() and not path.is_symlink(), 'credential file permissions')
    provision = runpy.run_path(str(HERE / 'scripts/provision.py'))
    require(provision['convert_ed25519'](regular(directory / 'host')) == regular(directory / 'dropbear_host_key'), 'host key conversion mismatch')
    public = regular(directory / 'admin.pub').split()
    require(len(public) == 2 and public[0] == b'ssh-ed25519', 'administrator public-key format')
    expected = b'no-port-forwarding,no-agent-forwarding,no-X11-forwarding ' + b' '.join(public) + b'\n'
    require(regular(directory / 'authorized_keys') == expected, 'authorized key mismatch')
    return directory


def compose(parent, package, keys):
    parse, encode = parser_tools()
    baseline = parse(regular(parent / 'gemini-pwrap-reset-serviceability-initramfs.img'))
    members = dict(baseline)
    for name in REMOVED:
        require(name in members, 'removal member absent')
        del members[name]
    file_template = baseline['bin/reboot']
    dir_template = baseline['etc']
    for name in ('root', 'root/.ssh', 'etc/dropbear'):
        require(name not in members, 'new credential directory already exists')
        members[name] = replace(dir_template, mode=stat.S_IFDIR | 0o700, data=b'')
    require({p.name for p in (HERE / 'initramfs').iterdir()} == set(SOURCES), 'init source inventory changed')
    for source, name in SOURCES.items():
        mode = 0o644 if source == 'inittab' else 0o755
        members[name] = replace(file_template, mode=stat.S_IFREG | mode, data=regular(HERE / 'initramfs' / source))
    added = {
        'bin/dropbear': (regular(package / 'dropbear'), 0o755),
        'bin/kmsg-capture': (regular(package / 'kmsg-capture'), 0o755),
        'bin/keyboard-observe': (regular(package / 'keyboard-observe'), 0o755),
        'bin/emmc-observe': (regular(HERE.parent / 'emmc/observe.sh'), 0o755),
        'etc/passwd': (b'root:x:0:0:Administrator:/root:/bin/admin-shell\n', 0o644),
        'etc/group': (b'root:x:0:\n', 0o644),
        'etc/shells': (b'/bin/admin-shell\n', 0o644),
        'root/.ssh/authorized_keys': (regular(keys / 'authorized_keys'), 0o600),
        'etc/dropbear/host_key': (regular(keys / 'dropbear_host_key'), 0o600),
    }
    for name, (data, mode) in added.items():
        require(name not in members, 'new member collision')
        members[name] = replace(file_template, mode=stat.S_IFREG | mode, data=data)
    output = encode(members)
    require(parse(output) == members, 'archive round-trip changed metadata')
    # Independent second serialization exercises a freshly parsed parent.
    require(encode(parse(output)) == output, 'archive serialization unstable')
    return output, members


def write_file(path, data, mode=0o600):
    with path.open('xb') as stream:
        stream.write(data)
    path.chmod(mode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--foundation-candidate', type=Path, required=True)
    parser.add_argument('--userspace', type=Path, required=True)
    parser.add_argument('--userspace-manifest-sha256', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    require(not subprocess.check_output(['git', '-C', str(REPO), 'status', '--porcelain'], text=True).strip(), 'candidate source checkout must be clean')
    require(subprocess.check_output(['git', '-C', str(REPO), 'remote', 'get-url', 'origin'], text=True).strip() == 'https://github.com/ixoo/gemini-pda-mainline.git', 'unexpected origin')
    package, parent, userspace = map(safe_directory, (args.package, args.foundation_candidate, args.userspace))
    foundation = json.loads(regular(HERE / 'foundation.json'))
    FOUNDATION['audit'](REPO, package, parent, foundation)
    userspace_inventory(userspace, args.userspace_manifest_sha256)
    keys = credentials(REPO / 'artifacts/credentials/a53-auth')
    output_root = REPO / 'artifacts/a53-authenticated/candidates'
    for path in (output_root, *output_root.parents):
        require(not path.is_symlink(), 'symlink output root')
    output_root.mkdir(parents=True, mode=0o700, exist_ok=True)
    with (output_root / '.build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stage = output_root / '.candidate-stage'
        require(not stage.is_symlink(), 'unsafe stale candidate stage')
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(mode=0o700)
        try:
            ramdisk, members = compose(parent, userspace, keys)
            replica, replica_members = compose(parent, userspace, keys)
            require(replica == ramdisk and set(replica_members) == set(members), 'independent initramfs assembly differs')
            write_file(stage / 'initramfs.img', ramdisk)
            write_file(stage / 'Image.gz', regular(parent / 'Image.gz'))
            write_file(stage / 'board.dtb', regular(parent / 'mt6797-gemini-pda-pwrap-reset-serviceability.dtb'))
            write_file(stage / 'kernel.config', regular(parent / 'kernel.config'))
            serializer = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py'
            command = ['python3', str(serializer), '--kernel', str(stage / 'Image.gz'), '--ramdisk', str(stage / 'initramfs.img'),
                       '--dtb', str(stage / 'board.dtb'), '--name', 'gemini-obs-L', '--cmdline', 'bootopt=64S3,32N2,64N2',
                       '--kernel-addr', '0x40200000', '--ramdisk-addr', '0x45000000', '--second-addr', '0x40f00000',
                       '--tags-addr', '0x44000000', '--lk-android8']
            for name in ('boot.img', 'replica.img'):
                subprocess.run(command + ['--output', str(stage / name)], check=True, stdout=subprocess.DEVNULL)
            raw = regular(stage / 'boot.img')
            require(raw == regular(stage / 'replica.img') and len(raw) < 16777216, 'container repetition/size')
            (stage / 'replica.img').unlink()
            write_file(stage / 'boot2-padded.img', raw + bytes(16777216 - len(raw)))
            manifest = {
                'schema': 1, 'experiment': 'a53-authenticated-baseline', 'preparation_state': 'preparing',
                'repository_commit': subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(),
                'foundation_commit': foundation['repository_build_commit'], 'foundation_manifest_sha256': digest(regular(HERE / 'foundation.json')),
                'userspace_manifest_sha256': args.userspace_manifest_sha256,
                'secret_bearing': True, 'physical_admission': False,
                'files': {p.name: digest(regular(p)) for p in stage.iterdir()},
                'members': {name: {'mode': oct(m.mode), 'sha256': digest(m.data), 'size': len(m.data)} for name, m in sorted(members.items())},
                'removed': sorted(REMOVED), 'known_hosts_sha256': digest(regular(keys / 'known_hosts')),
            }
            write_file(stage / 'candidate.json', (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode())
            validator = HERE / 'scripts/validate-candidate.py'
            subprocess.run(['python3', str(validator), '--candidate', str(stage), '--foundation', str(parent),
                            '--userspace', str(userspace)], check=True)
            name = 'candidate-' + digest(raw)
            require(not (output_root / name).exists(), 'candidate already exists; never overwrite')
            stage.rename(output_root / name)
            print('candidate=artifacts/a53-authenticated/candidates/' + name)
            print('secret_bearing=yes; physical_admission=no')
        finally:
            if stage.exists():
                shutil.rmtree(stage)


if __name__ == '__main__':
    main()
