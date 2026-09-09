#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Focused assembly checks; shared guards have their existing fixture coverage."""
import base64
from pathlib import Path
import re
import runpy
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
F = runpy.run_path(str(HERE/'focused-session.py'))


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.files = {name: (name+'\n').encode() for name in F['A_FILES']+F['B_FILES']}
        self.ident = '12345678-1234-1234-1234-123456789abc'
        self.methods = {'guard': lambda *_: 'set -e\nBB=/bin/busybox\n',
            'delivery_script': lambda _: b'mkdir /a53-keyboard-delivery\n__KEYBOARD_DELIVERY_PASS__\n',
            'capture_script': lambda _: b'BB=/bin/busybox\nset +e\n/a53-keyboard-delivery/keyboard-monitor event0 64\n__KEYBOARD_POSTFLIGHT_PASS__\n',
            'export_script': lambda _: b'read /a53-keyboard-delivery/keyboard-attempt/observer.stdout\n'}

    def test_second_delivery_and_capture_bind_every_file_and_ready_id(self):
        with patch.dict(F['M'], self.methods):
            commands = F['commands']({}, self.files, self.ident)
        second = commands['delivery-b.sh'].decode()
        encoded = re.findall(r"<<'FOCUSED_FILE_\d+'\n([^\n]+)\nFOCUSED_FILE_\d+", second)
        self.assertEqual([base64.b64decode(raw) for raw in encoded],
                         [self.files[name] for name in F['B_FILES']])
        capture = commands['capture.sh'].decode()
        for raw in self.files.values():
            self.assertIn(F['sha'](raw), capture.split('set +e')[0])
        self.assertIn(F['sha']((self.ident+'\n').encode()), capture.split('set +e')[0])
        self.assertIn('set -C', second)
        self.assertIn('/proc/mounts', capture)
        self.assertNotIn('/a53-keyboard-delivery', b''.join(commands.values()).decode())

    def test_template_drift_and_oversized_command_refuse(self):
        with patch.dict(F['M'], {**self.methods, 'capture_script': lambda _: b'changed\n'}):
            with self.assertRaisesRegex(ValueError, 'template changed'):
                F['commands']({}, self.files, self.ident)
        with patch.dict(F['M'], self.methods):
            with self.assertRaisesRegex(ValueError, 'byte ceiling'):
                F['commands']({}, {**self.files, 'keyboard-observe': b'x'*262144}, self.ident)


if __name__ == '__main__':
    unittest.main()
