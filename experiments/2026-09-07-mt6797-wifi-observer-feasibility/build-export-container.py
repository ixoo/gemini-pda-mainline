#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Construct an unselected private export-kernel diagnostic in the RE VM."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import struct
import subprocess

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / '2026-08-02-gemian-a72-bounded-observer-boot/scripts/assemble.py'
PARENT_SHA256 = '532f6f0dec5030a7b066f3baefa53580ec148317f633d4dd8d43308d30ac03b3'
KERNEL_SHA256 = '4fc02b373433bba5ca2ee8dc00990ea8698ad2d817ed7f7aa2e9fc7e08cda06b'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(active, kernel, filesystem, session_raw):
    if sha(PARENT.read_bytes()) != PARENT_SHA256:
        raise ValueError('native parent assembler changed')
    native = load('native_container', PARENT)
    native.KERNEL_FIELD_SHA256 = KERNEL_SHA256
    # This validates the retained image, all native addresses, original ramdisk,
    # and the exact selected kernel without changing its native ARM64 header.
    baseline, _ = native.build(active, kernel)
    session = json.loads(session_raw)
    load('startup', HERE / 'startup.py').validate_session(session)
    if session['startup_action'] not in ('export', 'export-return', 'boot-entry') or session['kernel_image_sha256'] != KERNEL_SHA256:
        raise ValueError('requires the selected export kernel and diagnostic action')
    if session['kernel_inputs_sha256'] != sha((HERE / 'full-kernel-inputs.json').read_bytes()):
        raise ValueError('kernel inputs changed')
    for name, expected in session['startup_files'].items():
        init = 'boot-entry-init.sh' if session['startup_action'] == 'boot-entry' else 'startup-init.sh'
        source = HERE / (init if name == 'init' else Path(name).name)
        if sha(source.read_bytes()) != expected:
            raise ValueError('startup source changed')
    extracted = subprocess.run(['cpio', '--quiet', '-i', '--to-stdout',
                                'etc/wifi-cycle/session.json'],
                               input=gzip.decompress(filesystem), capture_output=True, check=True)
    if extracted.stderr or extracted.stdout != session_raw:
        raise ValueError('filesystem session identity mismatch')
    command = (native.CMDLINE + ' rdinit=/init panic=0 cpuidle.off=1'
               ' ramoops.pmsg_capture=1 wifi_cycle=' + session['cycle_id'] +
               (' wifi_return=1 maxcpus=8' if session['startup_action'] == 'export-return' else '')).encode('ascii')
    if len(command) >= 512:
        raise ValueError('startup command line exceeds first header field')
    header = bytearray(baseline[:native.PAGE_SIZE])
    struct.pack_into('<I', header, 16, len(filesystem))
    header[64:576] = command.ljust(512, b'\0')
    header[608:1632] = bytes(1024)
    identity = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, filesystem, b''):
        identity.update(payload)
        identity.update(struct.pack('<I', len(payload)))
    header[576:608] = identity.digest() + bytes(12)
    raw = bytes(header) + kernel.ljust(native.align(len(kernel)), b'\0')
    raw += filesystem.ljust(native.align(len(filesystem)), b'\0')
    if len(raw) >= native.ACTIVE_SIZE:
        raise ValueError('export container does not fit boot2')
    expected = list(native.boot_fields(baseline))
    expected[2] = len(filesystem)
    if native.boot_fields(raw) != tuple(expected):
        raise ValueError('serialized native header mismatch')
    offset = native.PAGE_SIZE + native.align(len(kernel))
    if raw[offset:offset + len(filesystem)] != filesystem:
        raise ValueError('serialized filesystem mismatch')
    return raw, raw.ljust(native.ACTIVE_SIZE, b'\0')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('active-boot', 'kernel-field', 'filesystem', 'session', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--filesystem-sha256', required=True)
    parser.add_argument('--session-sha256', required=True)
    args = parser.parse_args()
    if platform.system() != 'Linux':
        raise ValueError('run private container construction in the RE VM')
    os.umask(0o077)
    for path in (args.active_boot, args.kernel_field, args.filesystem, args.session):
        if path.is_symlink() or not path.is_file():
            raise ValueError('requires regular input files')
    filesystem, session = args.filesystem.read_bytes(), args.session.read_bytes()
    if sha(filesystem) != args.filesystem_sha256 or sha(session) != args.session_sha256:
        raise ValueError('externally pinned filesystem or session changed')
    raw, padded = build(args.active_boot.read_bytes(), args.kernel_field.read_bytes(), filesystem, session)
    args.output.mkdir(mode=0o700)
    for name, data in (('export.boot.img', raw), ('boot2-padded.img', padded)):
        with (args.output / name).open('xb') as stream:
            stream.write(data)
    (args.output / 'private-result.json').write_text(json.dumps({
        'scope': 'unselected native diagnostic container; device validation outstanding',
        'startup_action': json.loads(session)['startup_action'],
        'assembler_sha256': sha(Path(__file__).read_bytes()),
        'parent_assembler_sha256': PARENT_SHA256,
        'kernel_sha256': KERNEL_SHA256,
        'filesystem_sha256': sha(filesystem), 'session_sha256': sha(session),
        'raw_sha256': sha(raw), 'padded_sha256': sha(padded),
        'raw_bytes': len(raw), 'padded_bytes': len(padded),
    }, sort_keys=True, indent=2) + '\n')
    (args.output / 'SHA256SUMS').write_text(''.join(
        sha((args.output / name).read_bytes()) + '  ' + name + '\n'
        for name in ('export.boot.img', 'boot2-padded.img', 'private-result.json')))
    print('container_bytes=' + str(len(raw)))
    print('padded_bytes=' + str(len(padded)))
    print('selected_for_boot=false device_access=none')


if __name__ == '__main__':
    main()
