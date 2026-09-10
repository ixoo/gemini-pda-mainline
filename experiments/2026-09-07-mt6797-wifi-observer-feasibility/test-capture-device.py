#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Injected candidate filesystem/USB identity with a real duplex local PTY."""
import importlib.util
import os
from pathlib import Path
import pty
import stat
import struct
import threading
import tty
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixture = load('startup_tests', 'test-startup.py')
device = load('capture_device', 'capture-device.py')
export = load('capture_export', 'capture-export.py')
startup = fixture.startup
BOOT = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'
PREVIOUS = '00000000-0000-4000-8000-000000000002'
SNAPSHOT = bytes(range(256)) * 256


class DeviceTests(unittest.TestCase):
    write = fixture.StartupTests.write
    save_session = fixture.StartupTests.save_session

    def setUp(self):
        fixture.StartupTests.setUp(self)
        self.session['startup_action'] = 'export'
        for name in ('capture-export.py', 'capture-device.py'):
            content = (HERE / name).read_bytes()
            path = 'opt/wifi-cycle/' + name
            self.write(path, content)
            self.session['startup_files'][path] = startup.sha(content)
        self.save_session()
        for name, value in {
            'pmsg_capture': 'Y', 'pmsg_capture_denials': '0',
            'mem_address': str(0x44410000), 'mem_size': str(0xe0000),
            'record_size': '4096', 'console_size': '65536', 'ftrace_size': '4096',
            'pmsg_size': '65536', 'mem_type': '0', 'ecc': '0',
        }.items():
            self.write('sys/module/ramoops/parameters/' + name, value)
        reserved = 'sys/firmware/devicetree/base/reserved-memory/'
        self.write(reserved + 'pstore-reserved-memory@44410000/reg',
                   struct.pack('>IIII', 0, 0x44410000, 0, 0xd0000))
        self.write(reserved + 'pmsg-capture-reserved-memory@444e0000/reg',
                   struct.pack('>IIII', 0, 0x444e0000, 0, 0x10000))
        self.write(reserved + 'pmsg-capture-reserved-memory@444e0000/no-map', b'')
        self.write('proc/self/mountinfo', '25 23 0:20 / /sys/fs/pstore ro,nosuid,nodev,noexec - pstore pstore ro\n')
        self.write('sys/fs/pstore/pmsg-ramoops-0', SNAPSHOT)
        for name, value in {'android0/enable': '0', 'android0/functions': '',
                            'f_acm/instances': '0', 'f_acm/port_index': '0,0,0,0'}.items():
            self.write('sys/class/android_usb/' + name, value)
        self.write('sys/class/tty/ttyGS0/dev', '233:0')
        self.session, self.identity = startup.prepare()

    def test_exact_preserved_snapshot(self):
        self.assertEqual(device.read_snapshot(startup, self.session, BOOT), SNAPSHOT)

    def test_layout_boot_and_interference_refusals_before_usb_write(self):
        for path, value in {
            'sys/module/ramoops/parameters/pmsg_capture': 'N',
            'sys/module/ramoops/parameters/pmsg_capture_denials': '1',
            'sys/module/ramoops/parameters/pmsg_size': '65524',
            'sys/firmware/devicetree/base/reserved-memory/pmsg-capture-reserved-memory@444e0000/reg': bytes(16),
            'sys/firmware/devicetree/base/reserved-memory/pmsg-capture-reserved-memory@444e0000/no-map': b'x',
            'proc/sys/kernel/random/boot_id': PREVIOUS,
            'proc/self/mountinfo': '25 23 0:20 / /sys/fs/pstore rw - pstore pstore rw\n',
            'sys/fs/pstore/pmsg-ramoops-0': bytes(65524),
        }.items():
            old = (self.root / path).read_bytes()
            try:
                self.write(path, value)
                with self.subTest(path=path), patch.object(device, 'control_write') as write:
                    with self.assertRaises(ValueError):
                        device.export_snapshot(startup, self.session, self.identity)
                    write.assert_not_called()
            finally:
                self.write(path, old)

    def test_ambiguous_snapshot_and_existing_usb_owner_refused(self):
        self.write('sys/fs/pstore/pmsg-other-0', SNAPSHOT)
        with patch.object(device, 'control_write') as write:
            with self.assertRaises(ValueError):
                device.export_snapshot(startup, self.session, self.identity)
            write.assert_not_called()
        (self.root / 'sys/fs/pstore/pmsg-other-0').unlink()
        self.write('sys/class/android_usb/android0/enable', '1')
        with patch.object(device, 'control_write') as write:
            with self.assertRaises(ValueError):
                device.export_snapshot(startup, self.session, self.identity)
            write.assert_not_called()

    def test_duplex_export_with_injected_usb_controls(self):
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        tty.setraw(slave)
        os.set_blocking(master, False)
        os.set_blocking(slave, False)
        node = self.root / 'dev/ttyGS0'
        expected = os.makedev(233, 0)
        original_open, original_fstat, original_lstat = os.open, os.fstat, Path.lstat
        serial_fds, controls, errors = [], [], []

        def open_node(path, flags, *args, **kwargs):
            if Path(path) == node:
                fd = os.dup(slave)
                serial_fds.append(fd)
                return fd
            return original_open(path, flags, *args, **kwargs)

        def fstat(fd):
            if fd in serial_fds:
                return SimpleNamespace(st_mode=stat.S_IFCHR, st_rdev=expected)
            info = original_fstat(fd)
            # The shared startup fixture injects uid 0 for device PID1. Keep
            # the host directory owner consistent with that injected uid.
            if stat.S_ISDIR(info.st_mode):
                return SimpleNamespace(st_mode=info.st_mode, st_uid=0)
            return info

        def lstat(path, *args, **kwargs):
            if path == node:
                return SimpleNamespace(st_mode=stat.S_IFCHR, st_rdev=expected)
            return original_lstat(path, *args, **kwargs)

        def control_write(unused, name, value):
            controls.append((name, value))
            self.write('sys/class/android_usb/' + name, value)
            if name == 'android0/enable':
                self.write('sys/class/android_usb/android0/state', 'CONFIGURED')

        output = self.root / 'received'
        session_hash = self.identity[16:48].hex()

        def receive():
            try:
                stream = export.SerialStream(master, 3)
                export.request_snapshot(stream, PREVIOUS, session_hash)
                export.receive_snapshot(stream, output, PREVIOUS, session_hash)
            except Exception as error:
                errors.append(error)

        with patch.object(os, 'open', side_effect=open_node), patch.object(os, 'fstat', side_effect=fstat), \
                patch.object(Path, 'lstat', lstat), patch.object(device, 'control_write', side_effect=control_write):
            receiver = threading.Thread(target=receive, daemon=True)
            receiver.start()
            fd = device.export_snapshot(startup, self.session, self.identity)
            self.addCleanup(os.close, fd)
            receiver.join(timeout=4)
            self.assertFalse(receiver.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(original_fstat(fd).st_rdev, original_fstat(slave).st_rdev)
        self.assertEqual((output / 'snapshot.raw').read_bytes(), SNAPSHOT)
        self.assertEqual(controls, [('f_acm/instances', '1'), ('android0/functions', 'acm'),
                                    ('android0/enable', '1')])


if __name__ == '__main__':
    unittest.main()
