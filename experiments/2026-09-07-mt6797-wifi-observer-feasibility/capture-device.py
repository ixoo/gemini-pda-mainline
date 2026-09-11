#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""PID1-only preserved-snapshot export; no capture initialization or clearing."""
import importlib.util
import os
import stat
import struct
import tty
import uuid


def check_capture(startup, session, boot_id):
    startup.check_runtime(session)
    startup.mark('capture-layout')
    if startup.text('proc/sys/kernel/random/boot_id') != boot_id:
        raise ValueError('capture boot identity changed')
    parameters = 'sys/module/ramoops/parameters/'
    if (startup.text(parameters + 'pmsg_capture') != 'Y' or
            startup.text(parameters + 'pmsg_capture_denials') != '0'):
        raise ValueError('capture mode or exclusion mismatch')
    for name, expected in {
        'mem_address': 0x44410000, 'mem_size': 0xe0000,
        'record_size': 4096, 'console_size': 65536, 'ftrace_size': 4096,
        'pmsg_size': 65536, 'mem_type': 0, 'ecc': 0,
    }.items():
        if int(startup.text(parameters + name), 0) != expected:
            raise ValueError('capture layout mismatch')
    reserved = 'sys/firmware/devicetree/base/reserved-memory/'
    for name, base, size in (
        ('pstore-reserved-memory@44410000', 0x44410000, 0xd0000),
        ('pmsg-capture-reserved-memory@444e0000', 0x444e0000, 0x10000),
    ):
        if startup.file_bytes(reserved + name + '/reg', 16) != struct.pack('>IIII', 0, base, 0, size):
            raise ValueError('capture reservation mismatch')
    if startup.file_bytes(reserved + 'pmsg-capture-reserved-memory@444e0000/no-map', 0) != b'':
        raise ValueError('invalid capture no-map property')
    mounts = []
    for line in startup.text('proc/self/mountinfo').splitlines():
        left, separator, right = line.partition(' - ')
        fields = left.split()
        if len(fields) >= 6 and fields[4] == '/sys/fs/pstore':
            mounts.append((separator, fields[5].split(','), right.split()[0]))
    if len(mounts) != 1 or mounts[0][0] != ' - ' or 'ro' not in mounts[0][1] or mounts[0][2] != 'pstore':
        raise ValueError('expected the read-only pstore mount')


def read_snapshot(startup, session, boot_id):
    check_capture(startup, session, boot_id)
    startup.mark('snapshot-read')
    directory = startup.ROOT / 'sys/fs/pstore'
    if sorted(p.name for p in directory.iterdir() if p.name.startswith('pmsg-')) != ['pmsg-ramoops-0']:
        raise ValueError('ambiguous or absent preserved PMSG snapshot')
    snapshot = startup.file_bytes('sys/fs/pstore/pmsg-ramoops-0', 65536)
    if len(snapshot) != 65536:
        raise ValueError('expected the complete raw capture-mode snapshot')
    check_capture(startup, session, boot_id)
    return snapshot


def control_write(startup, name, value):
    fd = os.open(startup.ROOT / ('sys/class/android_usb/' + name),
                 os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        data = (value + '\n').encode('ascii')
        if os.write(fd, data) != len(data):
            raise OSError('incomplete USB control write; no retry')
    finally:
        os.close(fd)


def check_usb(startup, enabled, functions, instances):
    for name, expected in {
        'android0/enable': enabled, 'android0/functions': functions,
        'f_acm/instances': instances, 'f_acm/port_index': '0,0,0,0',
    }.items():
        if startup.text('sys/class/android_usb/' + name) != expected:
            raise ValueError('USB function ownership mismatch')


def export_snapshot(startup, session, identity):
    """Called only after the startup source/session checks; return the live fd.

    Keep that descriptor open while PID1 parks. Queued bytes alone do not
    establish host preservation; no clearing or controller call follows.
    """
    if (os.getpid() != 1 or os.geteuid() != 0 or len(identity) != 96 or
            session.get('startup_action') != 'export'):
        raise ValueError('export requires the checked root PID1 session')
    boot_id = str(uuid.UUID(bytes=identity[48:64]))
    session_sha256 = identity[16:48].hex()
    startup.mark('snapshot')
    startup.log_stage('entered')
    snapshot = read_snapshot(startup, session, boot_id)
    startup.mark('usb-ownership')
    startup.log_stage('entered')
    check_usb(startup, '0', '', '0')
    startup.mark('acm-node')
    device = startup.ROOT / 'dev/ttyGS0'
    numbers = startup.text('sys/class/tty/ttyGS0/dev').split(':')
    if len(numbers) != 2 or int(numbers[0]) <= 0 or numbers[1] != '0':
        raise ValueError('unexpected first ACM terminal identity')
    expected = os.makedev(int(numbers[0]), 0)
    info = device.lstat()
    if not stat.S_ISCHR(info.st_mode) or info.st_rdev != expected:
        raise ValueError('ACM terminal node mismatch')
    startup.mark('export-protocol-import')
    spec = importlib.util.spec_from_file_location('capture_export', startup.ROOT / 'opt/wifi-cycle/capture-export.py')
    export = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(export)
    startup.mark('acm-instance')
    control_write(startup, 'f_acm/instances', '1')
    startup.mark('acm-function')
    control_write(startup, 'android0/functions', 'acm')
    check_usb(startup, '0', 'acm', '1')
    startup.mark('usb-enable')
    control_write(startup, 'android0/enable', '1')
    check_usb(startup, '1', 'acm', '1')
    startup.mark('acm-open')
    fd = os.open(device, os.O_RDWR | os.O_NONBLOCK | os.O_NOCTTY |
                 os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if not stat.S_ISCHR(info.st_mode) or info.st_rdev != expected or not os.isatty(fd):
            raise ValueError('opened ACM terminal mismatch')
        tty.setraw(fd, when=tty.TCSANOW)
        stream = export.SerialStream(fd)
        startup.mark('host-request')
        startup.log_stage('waiting')
        # Host first opens/configures its terminal, then requests this session.
        export.await_request(stream, boot_id, session_sha256)
        if startup.text('sys/class/android_usb/android0/state') != 'CONFIGURED':
            raise ValueError('ACM gadget is not configured')
        check_usb(startup, '1', 'acm', '1')
        check_capture(startup, session, boot_id)
        startup.mark('snapshot-send')
        export.send_snapshot(stream, snapshot, boot_id, session_sha256)
        check_capture(startup, session, boot_id)
        return fd
    except BaseException:
        os.close(fd)
        raise
