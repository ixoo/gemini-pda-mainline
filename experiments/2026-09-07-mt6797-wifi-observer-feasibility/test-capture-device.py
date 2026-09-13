#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Injected candidate filesystem/USB identity with a real duplex local PTY."""
import importlib.util
import os
from pathlib import Path
import pty
import socket
import stat
import struct
import threading
import tty
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

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
        self.log = patch.object(startup, 'log_stage').start()
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
        self.duplex_export(False)

    def test_duplex_export_return_requires_preservation_ack(self):
        self.duplex_export(True)

    def test_tcp_sender_requires_request_and_preservation_ack(self):
        # A real socket pair exercises the sender. Only listener addressing,
        # network configuration and runtime identity are injected here.
        host, candidate = socket.socketpair()
        self.addCleanup(host.close)
        self.addCleanup(candidate.close)
        host.setblocking(False)
        listener = MagicMock()
        listener.__enter__.return_value = listener
        listener.accept.return_value = (candidate, ('10.15.19.1', 40000))
        session_hash = self.identity[16:48].hex()
        errors = []

        def receive():
            try:
                stream = export.SerialStream(host.fileno(), 3)
                export.request_snapshot(stream, PREVIOUS, session_hash)
                # Read the complete frame without involving the fixture's uid.
                header = export.HEADER.unpack(export.read_exact(stream, export.HEADER.size))
                self.assertEqual(header[1], export.uuid.UUID(BOOT).bytes)
                self.assertEqual(export.read_exact(stream, export.SIZE), SNAPSHOT)
                stream.write(export.PRESERVED.pack(b'WFA1', header[1], header[2], header[3]))
            except Exception as error:
                errors.append(error)

        receiver = threading.Thread(target=receive, daemon=True)
        receiver.start()
        with patch.object(device, 'configure_ethernet') as configure, \
                patch.object(device, 'check_capture') as check, \
                patch.object(device.socket, 'socket', return_value=listener), \
                patch.object(device.socket, 'SO_BINDTODEVICE', 25, create=True):
            fd = device.export_tcp(startup, self.session, BOOT, session_hash, SNAPSHOT, export)
            self.addCleanup(os.close, fd)
            configure.assert_called_once_with(startup)
            listener.setsockopt.assert_called_once_with(socket.SOL_SOCKET, 25, b'usb0\0')
            listener.bind.assert_called_once_with(('10.15.19.82', 2323))
            listener.accept.assert_called_once_with()
            self.assertEqual(check.call_count, 3)
            for call in check.call_args_list:
                self.assertEqual(call.kwargs, {'usb_export': True})
        receiver.join(timeout=4)
        self.assertFalse(receiver.is_alive())
        self.assertEqual(errors, [])

    def test_ethernet_setup_only_changes_usb0_and_stops_on_failure(self):
        (self.root / 'sys/class/android_usb/android0/enable').unlink()
        (self.root / 'sys/class/android_usb/android0/functions').unlink()
        (self.root / 'sys/class/android_usb/android0').rmdir()
        (self.root / 'sys/module/g_ether').mkdir()
        self.write('sys/class/net/usb0/type', '1')
        self.write('sys/class/net/usb0/flags', '0x1002')
        self.write('proc/sys/net/ipv4/ip_forward', '0')
        self.write('proc/sys/net/ipv6/conf/usb0/disable_ipv6', '0\n')
        with patch.object(device.subprocess, 'run') as run:
            device.configure_ethernet(startup)
            self.assertEqual([call.args[0][1:] for call in run.call_args_list], [
                ['ip', 'addr', 'add', '10.15.19.82/24', 'dev', 'usb0'],
                ['ip', 'link', 'set', 'dev', 'usb0', 'up']])
            self.assertEqual(startup.text('proc/sys/net/ipv6/conf/usb0/disable_ipv6'), '1')
        with patch.object(device.subprocess, 'run', side_effect=OSError('injected')) as run:
            with self.assertRaises(OSError):
                device.configure_ethernet(startup)
            self.assertEqual(run.call_count, 1)

    def duplex_export(self, acknowledge):
        if acknowledge:
            fixture.StartupTests.arm_return(self)
            self.session, self.identity = startup.prepare()
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
                export.receive_snapshot(stream, output, PREVIOUS, session_hash,
                                        acknowledge=acknowledge)
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
            self.assertEqual([call.args for call in self.log.call_args_list],
                             [('entered',), ('entered',), ('waiting',)])
        self.assertEqual((output / 'snapshot.raw').read_bytes(), SNAPSHOT)
        self.assertEqual(controls, [('f_acm/instances', '1'), ('android0/functions', 'acm'),
                                    ('android0/enable', '1')])


if __name__ == '__main__':
    unittest.main()
