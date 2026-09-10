#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic startup refusal checks; no kernel/device/firmware operation."""
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('startup', HERE / 'startup.py')
startup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(startup)


class StartupTests(unittest.TestCase):
    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.addCleanup(patch.stopall)
        patch.object(startup, 'ROOT', self.root).start()
        patch.object(startup.os, 'getpid', return_value=1).start()
        patch.object(startup.os, 'geteuid', return_value=0).start()
        self.mount = patch.object(startup.os, 'statvfs').start()
        self.mount.return_value.f_flag = startup.os.ST_RDONLY
        patch.object(startup.platform, 'machine', return_value='aarch64').start()
        patch.object(startup.platform, 'release', return_value='fixture').start()
        files = {}
        for name, size in startup.INPUT_PATHS.items():
            data = bytes(size)
            self.write(name, data)
            files[name] = {'size': size, 'sha256': startup.sha(data)}
        self.manifest = json.dumps({'runtime_sha256': startup.RUNTIME, 'files': files}).encode()
        self.write('etc/wifi-cycle/input-manifest.json', self.manifest)
        source_files = {}
        for name in ('init', 'opt/wifi-cycle/startup.py', 'opt/wifi-cycle/cycle-controller.py',
                     'opt/wifi-cycle/respond-once.py', 'opt/wifi-cycle/check-retained-patches.py'):
            self.write(name, b'fixture source')
            source_files[name] = startup.sha(b'fixture source')
        config = b'fixture config\n'
        self.session = {'schema': 1, 'cycle_id': '12345678-1234-4234-9234-123456789abc',
                        'kernel_release': 'fixture', 'kernel_version': 'fixture version',
                        'kernel_image_sha256': 'a' * 64, 'kernel_inputs_sha256': 'b' * 64,
                        'kernel_config_sha256': startup.sha(config), 'runtime_sha256': startup.RUNTIME,
                        'input_manifest_sha256': startup.sha(self.manifest), 'startup_files': source_files,
                        'cpu_online': '0-7'}
        self.save_session()
        self.write('proc/config.gz', gzip.compress(config))
        self.write('proc/version', 'fixture version\n')
        self.cmdline = 'rdinit=/init panic=0 cpuidle.off=1 wifi_cycle=' + self.session['cycle_id']
        self.write('proc/cmdline', self.cmdline)
        for path, data in {
            'proc/sys/kernel/panic': '0', 'proc/sys/kernel/sysrq': '0',
            'proc/sys/kernel/hotplug': '', 'sys/module/cpuidle/parameters/off': '1',
            'sys/module/firmware_class/parameters/path': '', 'sys/devices/system/cpu/online': '0-7',
            'sys/class/net/lo/flags': '0x8',
            'proc/sys/kernel/random/boot_id': 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee',
            'proc/2/stat': '2 (kernel thread) S 0 0 0 0 0 2097152 0',
        }.items():
            self.write(path, data)

    def save_session(self):
        self.raw = json.dumps(self.session).encode()
        self.write('etc/wifi-cycle/session.json', self.raw)

    def test_identity_joins_exact_session_boot_and_inputs(self):
        _, identity = startup.prepare()
        self.assertEqual(len(identity), 96)
        self.assertEqual(identity[16:48], bytes.fromhex(startup.sha(self.raw)))
        self.assertEqual(identity[48:64], startup.uuid.UUID('aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee').bytes)
        self.assertEqual(identity[64:], bytes.fromhex(startup.sha(self.manifest)))

    def test_writable_mount_refused(self):
        self.mount.return_value.f_flag = 0
        with self.assertRaisesRegex(ValueError, 'writable'):
            startup.prepare()

    def test_changed_private_input_refused(self):
        path = next(iter(startup.INPUT_PATHS))
        self.write(path, b'x' * startup.INPUT_PATHS[path])
        with self.assertRaisesRegex(ValueError, 'private input bytes'):
            startup.prepare()

    def test_changed_controller_refused_before_import(self):
        self.write('opt/wifi-cycle/cycle-controller.py', b'changed')
        with self.assertRaisesRegex(ValueError, 'startup source'):
            startup.prepare()

    def test_duplicate_boot_setting_refused(self):
        self.write('proc/cmdline', self.cmdline + ' panic=1')
        with self.assertRaisesRegex(ValueError, 'boot parameter'):
            startup.prepare()

    def test_sysrq_override_refused(self):
        self.write('proc/cmdline', self.cmdline + ' sysrq_always_enabled')
        with self.assertRaisesRegex(ValueError, 'SysRq override'):
            startup.prepare()

    def test_firmware_override_refused(self):
        self.write('sys/module/firmware_class/parameters/path', '/another')
        with self.assertRaisesRegex(ValueError, 'startup state'):
            startup.prepare()

    def test_earlier_lookup_refused(self):
        (self.root / 'storage').symlink_to('/does-not-exist')
        with self.assertRaisesRegex(ValueError, 'earlier WLAN'):
            startup.prepare()

    def test_alternate_directory_symlink_refused(self):
        (self.root / 'lib/firmware/updates').symlink_to(self.root / 'opt')
        with self.assertRaisesRegex(ValueError, 'alternate input'):
            startup.prepare()

    def test_userspace_process_with_empty_cmdline_refused(self):
        self.write('proc/3/stat', '3 (zombie) Z 1 0 0 0 0 0 0')
        with self.assertRaisesRegex(ValueError, 'userspace process'):
            startup.prepare()

    def test_interface_up_refused(self):
        self.write('sys/class/net/wlan0/flags', '0x1003')
        with self.assertRaisesRegex(ValueError, 'administratively up'):
            startup.prepare()

    def test_configuration_mismatch_refused(self):
        self.write('proc/config.gz', gzip.compress(b'other config'))
        with self.assertRaisesRegex(ValueError, 'configuration mismatch'):
            startup.prepare()


if __name__ == '__main__':
    unittest.main()
