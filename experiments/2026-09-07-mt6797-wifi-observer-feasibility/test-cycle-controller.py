#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Real fork/pipe joins and mocked ioctls; never opens a device or changes hardware."""
import importlib.util
import os
from pathlib import Path
import select
import socket
import time
import unittest
from unittest.mock import patch
import uuid

spec = importlib.util.spec_from_file_location('cycle_controller', Path(__file__).with_name('cycle-controller.py'))
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


class ProcessTests(unittest.TestCase):
    def exercise(self, fault=None):
        parent = os.getpid()
        device, peer = socket.socketpair()
        peer.settimeout(1)
        children, calls = [], []
        real_fork, real_exit = os.fork, os._exit

        def fork():
            child = real_fork()
            if child: children.append(child)
            return child

        def serve(fd, deadline, records, chip, version):
            assert os.getpid() != parent
            poller = select.poll();poller.register(fd, select.POLLIN)
            if not poller.poll(150): raise TimeoutError('fixture received no ON')
            assert os.read(fd, 2) == b'ON'
            assert os.write(fd, b'OK') == 2
            if fault == 'responder': raise RuntimeError('injected responder failure')
            return {'stage': 'reply-written'}

        def ioctl(fd, request, argument):
            self.assertEqual(os.getpid(), parent)
            self.assertEqual((fd, request), (device.fileno(), controller.FUNC_ONOFF))
            calls.append(argument)
            if argument == controller.WLAN_ON:
                if fault == 'on': raise OSError('injected ON failure')
                peer.sendall(b'ON')
                self.assertEqual(peer.recv(2), b'OK')
                return 1 if fault == 'on-status' else 0
            self.assertEqual(argument, controller.WLAN_OFF)
            # OFF is only reached after this exact responder has been reaped.
            with self.assertRaises(ChildProcessError): os.waitpid(children[0], os.WNOHANG)
            if fault == 'off': raise OSError('injected OFF failure')
            return 0

        try:
            with patch.object(controller.os, 'fork', side_effect=fork), \
                 patch.object(controller.os, '_exit', side_effect=lambda status: real_exit(7 if fault == 'exit' else status)), \
                 patch.object(controller.responder, 'serve', side_effect=serve), \
                 patch.object(controller.fcntl, 'ioctl', side_effect=ioctl):
                if fault is None:
                    result = controller.request_pair(device.fileno(), [], 0x0279, 0, time.monotonic_ns() + 2000000000)
                    self.assertTrue(result['responder_joined'])
                else:
                    with self.assertRaises((OSError, RuntimeError)):
                        controller.request_pair(device.fileno(), [], 0x0279, 0, time.monotonic_ns() + 2000000000)
            self.assertEqual(calls, [controller.WLAN_ON, controller.WLAN_OFF] if fault in (None, 'off') else [controller.WLAN_ON])
        finally:
            # Test-only cleanup of these socket-only children after failure.
            # The production controller deliberately does not block here.
            for child in children:
                try: os.waitpid(child, 0)
                except ChildProcessError: pass
            device.close();peer.close()

    def test_real_responder_is_reaped_before_off(self):
        self.exercise()

    def test_failures_do_not_issue_another_request(self):
        for fault in ('on', 'on-status', 'responder', 'exit', 'off'):
            with self.subTest(fault=fault): self.exercise(fault)

    def test_old_command_refuses_before_fork_or_ioctl(self):
        device, peer = socket.socketpair()
        try:
            peer.sendall(b'old')
            with patch.object(controller.os, 'fork') as fork, patch.object(controller.fcntl, 'ioctl') as ioctl:
                with self.assertRaises(RuntimeError):
                    controller.request_pair(device.fileno(), [], 0x0279, 0, time.monotonic_ns() + 1000000000)
                fork.assert_not_called();ioctl.assert_not_called()
        finally:
            device.close();peer.close()


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.boot = uuid.UUID('33333333-3333-3333-3333-333333333333')
        self.identity = bytes([1])*16 + bytes([2])*32 + self.boot.bytes + bytes([4])*32
        self.order = []
        targets = [
            (controller.platform, 'machine', {'return_value': 'aarch64'}),
            (controller.platform, 'release', {'return_value': 'fixture'}),
            (controller.threading, 'active_count', {'return_value': 1}),
            (controller.Path, 'read_text', {'return_value': str(self.boot)}),
            (controller.responder, 'check_abi', {}),
            (controller.responder, 'check_descriptor', {'side_effect': lambda *args: self.order.append(('descriptor', args))}),
            (controller.responder, 'prepare_patches', {'side_effect': lambda *args: self.order.append(('prepare', args)) or []}),
            (controller.os, 'open', {'return_value': 42}),
            (controller.os, 'close', {}),
            (controller.fcntl, 'ioctl', {'side_effect': self.ioctl}),
            (controller, 'request_pair', {'side_effect': lambda *args: self.order.append(('pair', args)) or {'done': True}}),
        ]
        for obj, name, kwargs in targets:
            mocker = patch.object(obj, name, **kwargs)
            setattr(self, name, mocker.start());self.addCleanup(mocker.stop)

    def ioctl(self, fd, request, argument):
        self.order.append(('ioctl', (fd, request, argument)))
        return controller.CAPTURE_ABI_VERSION if request == controller.CAPTURE_ABI else 0

    def run_cycle(self, identity=None):
        return controller.run_cycle(41, self.identity if identity is None else identity, 'fixture', '/fixture', 0x0279, 0)

    def test_prepares_before_takeover_and_configures_before_requests(self):
        self.assertEqual(self.run_cycle(), {'done': True})
        self.assertEqual([name for name, _ in self.order], ['descriptor', 'ioctl', 'prepare', 'ioctl', 'descriptor', 'ioctl', 'pair'])
        self.assertEqual(self.order[1][1], (41, controller.CAPTURE_ABI, 0))
        self.assertEqual(self.order[3][1], (41, controller.CAPTURE_INIT, bytearray(self.identity)))
        self.assertEqual(self.order[5][1], (42, controller.SET_STP_MODE, 0x23))
        self.close.assert_called_once_with(42)

    def test_preflight_failure_has_no_device_effect(self):
        for identity in (b'', bytes(96), self.identity[:48] + bytes([5])*16 + self.identity[64:]):
            with self.assertRaises(ValueError): self.run_cycle(identity)
        self.ioctl.assert_not_called();self.open.assert_not_called()
        self.prepare_patches.side_effect = ValueError('firmware mismatch')
        with self.assertRaises(ValueError): self.run_cycle()
        self.ioctl.assert_called_once_with(41, controller.CAPTURE_ABI, 0)
        self.open.assert_not_called()

    def test_legacy_zero_success_cannot_start_controller(self):
        self.ioctl.side_effect = None
        self.ioctl.return_value = 0
        with self.assertRaises(RuntimeError): self.run_cycle()
        self.ioctl.assert_called_once_with(41, controller.CAPTURE_ABI, 0)
        self.prepare_patches.assert_not_called();self.open.assert_not_called()

    def test_initializer_and_configuration_failure_stop(self):
        self.ioctl.side_effect = [controller.CAPTURE_ABI_VERSION, OSError('initialization failed')]
        with self.assertRaises(OSError): self.run_cycle()
        self.open.assert_not_called();self.request_pair.assert_not_called()
        self.ioctl.side_effect = [controller.CAPTURE_ABI_VERSION, 0, OSError('configuration failed')]
        with self.assertRaises(OSError): self.run_cycle()
        self.request_pair.assert_not_called()


if __name__ == '__main__':
    unittest.main()
