#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic startup refusal checks; no kernel/device/firmware operation."""
import gzip
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
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
        # Inject every possible restart even when a test arms the return path.
        self.restart = patch.object(startup.os, 'spawnv', return_value=1).start()
        patch.object(startup, 'RETURN_ATTEMPTED', False).start()
        patch.object(startup, 'LOG_WRITES', 0).start()
        patch.dict(startup.os.environ, {}, clear=True).start()
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
                     'opt/wifi-cycle/respond-once.py', 'opt/wifi-cycle/check-retained-patches.py',
                     'opt/wifi-cycle/capture-export.py', 'opt/wifi-cycle/capture-device.py'):
            self.write(name, b'fixture source')
            source_files[name] = startup.sha(b'fixture source')
        config = b'fixture config\n'
        self.session = {'schema': 2, 'startup_action': 'cycle', 'cycle_id': '12345678-1234-4234-9234-123456789abc',
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
            'proc/hps/enabled': '0',
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

    def test_action_and_schema_are_explicit(self):
        for action in ('cycle', 'export'):
            self.session['startup_action'] = action
            self.save_session()
            self.assertEqual(startup.prepare()[0]['startup_action'], action)
        self.session['startup_action'] = 'clear'
        self.save_session()
        with self.assertRaisesRegex(ValueError, 'action'):
            startup.prepare()
        self.session['startup_action'] = 'export'
        self.session['schema'] = 1
        self.save_session()
        with self.assertRaisesRegex(ValueError, 'schema'):
            startup.prepare()

    def test_changed_private_input_refused(self):
        path = next(iter(startup.INPUT_PATHS))
        self.write(path, b'x' * startup.INPUT_PATHS[path])
        with self.assertRaisesRegex(ValueError, 'private input bytes'):
            startup.prepare()

    def arm_return(self):
        self.session['startup_action'] = 'export-return'
        self.save_session()
        self.write('proc/cmdline', self.cmdline + ' wifi_return=1 maxcpus=5 maxcpus=8')
        startup.os.environ.update(WIFI_EXPORT_RETURN_BOOT='aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee',
                                  WIFI_EXPORT_RETURN_CYCLE=self.session['cycle_id'])

    def test_usb_network_exception_is_limited_to_tcp_export_after_setup(self):
        self.arm_return()
        self.session['startup_action'] = 'export-tcp-return'
        self.save_session()
        self.write('sys/class/net/usb0/flags', '0x1002')
        self.write('proc/sys/net/ipv4/ip_forward', '0')
        self.write('proc/sys/net/ipv6/conf/usb0/disable_ipv6', '1')
        startup.prepare()
        with self.assertRaisesRegex(ValueError, 'USB export network'):
            startup.check_runtime(self.session, usb_export=True)
        self.write('sys/class/net/usb0/flags', '0x1003')
        with self.assertRaisesRegex(ValueError, 'administratively up'):
            startup.prepare()
        startup.check_runtime(self.session, usb_export=True)
        for path, bad in (('sys/class/net/lo/flags', '0x9'),
                          ('proc/sys/net/ipv4/ip_forward', '1'),
                          ('proc/sys/net/ipv6/conf/usb0/disable_ipv6', '0')):
            old = (self.root / path).read_bytes()
            self.write(path, bad)
            with self.subTest(path=path), self.assertRaises(ValueError):
                startup.check_runtime(self.session, usb_export=True)
            self.write(path, old)
        self.session['startup_action'] = 'export-return'
        with self.assertRaisesRegex(ValueError, 'network exception'):
            startup.check_runtime(self.session, usb_export=True)
        self.restart.assert_not_called()

    def test_export_return_requires_ordered_boot_cpu_limit(self):
        self.arm_return()
        startup.prepare()
        for arguments in ('', 'maxcpus=5', 'maxcpus=8', 'maxcpus=8 maxcpus=5',
                          'maxcpus=0 maxcpus=8', 'maxcpus=5 maxcpus=8 maxcpus=8',
                          'maxcpus=5 maxcpus=8 maxcpus=10',
                          'maxcpus=5 maxcpus=8 nosmp', 'maxcpus=5 maxcpus=8 nr_cpus=8'):
            with self.subTest(arguments=arguments):
                self.write('proc/cmdline', self.cmdline + ' wifi_return=1 ' + arguments)
                with self.assertRaisesRegex(ValueError, 'boot CPU limit'):
                    startup.prepare()
        self.restart.assert_not_called()

    def test_boot_cpu_limit_does_not_replace_online_mask_check(self):
        self.arm_return()
        self.write('sys/devices/system/cpu/online', '0-4')
        with patch.object(startup, 'log_stage') as log:
            with self.assertRaisesRegex(ValueError, 'kernel startup state'):
                startup.prepare()
            log.assert_called_once_with('observed-0-4')
        self.restart.assert_not_called()

    def test_export_return_requires_exact_flag_and_shell_handoff(self):
        self.arm_return()
        startup.prepare()
        for suffix in ('', ' wifi_return=0', ' wifi_return=1 wifi_return=1'):
            self.write('proc/cmdline', self.cmdline + suffix)
            with self.assertRaisesRegex(ValueError, 'return boot parameter'):
                startup.prepare()
        self.write('proc/cmdline', self.cmdline + ' wifi_return=1')
        startup.os.environ['WIFI_EXPORT_RETURN_BOOT'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'shell handoff'):
            startup.prepare()
        self.session['startup_action'] = 'export'
        self.save_session()
        with self.assertRaisesRegex(ValueError, 'return boot parameter'):
            startup.prepare()
        self.restart.assert_not_called()

    def test_return_once_requires_marker_and_never_retries(self):
        self.arm_return()
        info = SimpleNamespace(st_mode=stat.S_IFCHR, st_rdev=startup.os.makedev(1, 11))
        with patch.object(startup.platform, 'release', return_value='3.18.41+'), \
                patch.object(startup, 'text', side_effect=lambda path: (self.root / path).read_text().rstrip('\n')), \
                patch.object(startup.os, 'fstat', return_value=info), \
                patch.object(startup.os, 'write', side_effect=lambda fd, data: len(data)) as write:
            for outcome in ('preserved', 'stopped'):
                startup.RETURN_ATTEMPTED = False
                self.restart.reset_mock()
                write.reset_mock()
                startup.return_once(outcome)
                startup.return_once(outcome)
                self.restart.assert_called_once_with(startup.os.P_WAIT, '/bin/busybox',
                                                      ['/bin/busybox', 'reboot', '-f'])
                write.assert_called_once()
                self.assertIn(('outcome=' + outcome).encode(), write.call_args.args[1])
                self.assertLessEqual(len(write.call_args.args[1]), 192)
            for failure in ('short-write', 'bad-node', 'budget', 'wrong-boot', 'duplicate-flag'):
                startup.RETURN_ATTEMPTED = False
                startup.LOG_WRITES = 0
                self.restart.reset_mock()
                write.side_effect = lambda fd, data: len(data)
                info.st_rdev = startup.os.makedev(1, 11)
                self.write('proc/cmdline', self.cmdline + ' wifi_return=1')
                if failure == 'short-write':
                    write.side_effect = lambda fd, data: len(data) - 1
                elif failure == 'bad-node':
                    info.st_rdev = startup.os.makedev(1, 3)
                elif failure == 'budget':
                    startup.LOG_WRITES = 8
                elif failure == 'wrong-boot':
                    self.write('proc/sys/kernel/random/boot_id', 'changed')
                else:
                    self.write('proc/sys/kernel/random/boot_id', startup.os.environ['WIFI_EXPORT_RETURN_BOOT'])
                    self.write('proc/cmdline', self.cmdline + ' wifi_return=1 wifi_return=1')
                startup.return_once('stopped')
                startup.return_once('stopped')
                self.restart.assert_not_called()

    def test_caught_startup_failure_requests_one_return_and_parks(self):
        self.arm_return()
        info = SimpleNamespace(st_mode=stat.S_IFCHR, st_rdev=startup.os.makedev(1, 11))
        with patch.object(startup.platform, 'release', return_value='3.18.41+'), \
                patch.object(startup, 'text', side_effect=lambda path: (self.root / path).read_text().rstrip('\n')), \
                patch.object(startup.os, 'fstat', return_value=info), \
                patch.object(startup.os, 'write', side_effect=lambda fd, data: len(data)) as write, \
                patch.object(startup, 'prepare', side_effect=ValueError('injected')), \
                patch.object(startup.time, 'sleep', side_effect=SystemExit('parked')), \
                patch('builtins.print'):
            with self.assertRaisesRegex(SystemExit, 'parked'):
                startup.main()
            self.restart.assert_called_once()
            self.assertIn(b'outcome=stopped', write.call_args.args[1])

    def test_unarmed_startup_failure_does_not_restart(self):
        startup.return_once('stopped')
        self.restart.assert_not_called()
        self.assertFalse(startup.RETURN_ATTEMPTED)

    def test_preserved_export_requests_return_without_importing_cycle(self):
        self.preserved_export_returns('export-return')

    def test_preserved_tcp_export_requests_return_without_importing_cycle(self):
        self.preserved_export_returns('export-tcp-return')

    def preserved_export_returns(self, action):
        self.arm_return()
        self.session['startup_action'] = action
        self.save_session()
        identity = startup.prepare()[1]
        device = SimpleNamespace(export_snapshot=lambda *args: 99)
        loader = SimpleNamespace(exec_module=lambda module: None)
        info = SimpleNamespace(st_mode=stat.S_IFCHR, st_rdev=startup.os.makedev(1, 11))
        with patch.object(startup.platform, 'release', return_value='3.18.41+'), \
                patch.object(startup, 'prepare', return_value=(self.session, identity)), \
                patch.object(startup, 'text', side_effect=lambda path: (self.root / path).read_text().rstrip('\n')), \
                patch.object(startup.os, 'fstat', return_value=info), \
                patch.object(startup.os, 'write', side_effect=lambda fd, data: len(data)) as write, \
                patch.object(startup.importlib.util, 'spec_from_file_location',
                             return_value=SimpleNamespace(loader=loader)) as load, \
                patch.object(startup.importlib.util, 'module_from_spec', return_value=device), \
                patch.dict(startup.sys.modules, {'startup': startup}), \
                patch.object(startup.time, 'sleep', side_effect=SystemExit('parked')), \
                patch('builtins.print'):
            with self.assertRaisesRegex(SystemExit, 'parked'):
                startup.main()
            self.restart.assert_called_once()
            load.assert_called_once()
            self.assertEqual(load.call_args.args[0], 'capture_device')
            rows = [call.args[1] for call in write.call_args_list]
            self.assertEqual(sum(b'outcome=preserved' in row for row in rows), 1)
            self.assertFalse(any(b'outcome=stopped' in row for row in rows))

    def test_boot_entry_control_is_bound_and_cannot_enter_cycle(self):
        self.session['startup_action'] = 'boot-entry'
        with self.assertRaisesRegex(ValueError, 'control identity'):
            startup.validate_session(self.session)
        self.session['cycle_id'] = startup.BOOT_ENTRY_CYCLE_ID
        startup.validate_session(self.session)
        script = (HERE / 'boot-entry-init.sh').read_text()
        self.assertIn('wifi_cycle=' + startup.BOOT_ENTRY_CYCLE_ID, script)
        self.assertIn('control=' + startup.BOOT_ENTRY_CYCLE_ID, script)
        with patch.object(startup, 'prepare', return_value=(self.session, bytes(96))), \
                patch.object(startup, 'log_stage'), \
                patch.object(startup.importlib.util, 'spec_from_file_location') as load, \
                patch.object(startup.time, 'sleep', side_effect=SystemExit('parked')), \
                patch('builtins.print'):
            with self.assertRaisesRegex(SystemExit, 'parked'):
                startup.main()
            load.assert_not_called()

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

    def test_failure_stage_names_the_rejected_runtime_field(self):
        self.write('sys/module/cpuidle/parameters/off', '0')
        with self.assertRaises(ValueError):
            startup.prepare()
        self.assertEqual(startup.STAGE, 'runtime:sys/module/cpuidle/parameters/off')

    def test_active_hotplug_policy_refused_before_cpu_check(self):
        self.write('proc/hps/enabled', '1')
        with self.assertRaisesRegex(ValueError, 'startup state'):
            startup.prepare()
        self.assertEqual(startup.STAGE, 'runtime:proc/hps/enabled')

    def test_cpu_refusal_logs_only_a_short_numeric_cpu_list(self):
        for value in ('0-3', '0,2-7', 'private text', '1' * 33, '0-3\nsecret'):
            self.write('sys/devices/system/cpu/online', value)
            with patch.object(startup, 'log_stage') as log:
                with self.assertRaisesRegex(ValueError, 'startup state'):
                    startup.prepare()
                if value in ('0-3', '0,2-7'):
                    log.assert_called_once_with('observed-' + value)
                else:
                    log.assert_not_called()
            self.assertEqual(startup.STAGE, 'runtime:sys/devices/system/cpu/online')

    def test_log_descriptor_budget_and_short_write(self):
        info = SimpleNamespace(st_mode=stat.S_IFCHR, st_rdev=startup.os.makedev(1, 11))
        with patch.object(startup, 'LOG_WRITES', 0), \
                patch.object(startup, 'text', return_value='aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'), \
                patch.object(startup.os, 'fstat', return_value=info), \
                patch.object(startup.os, 'write', side_effect=lambda fd, data: len(data)) as write:
            startup.mark('session')
            for _ in range(8):
                startup.log_stage('stopped')
            with self.assertRaisesRegex(ValueError, 'budget'):
                startup.log_stage('stopped')
            self.assertEqual(write.call_count, 8)
            self.assertEqual(write.call_args.args, (3,
                b'<11>wifi-bootstrap-v1 boot=aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee python=session status=stopped\n'))
            startup.LOG_WRITES = 0
            write.reset_mock()
            info.st_rdev = startup.os.makedev(1, 3)
            with self.assertRaisesRegex(ValueError, 'descriptor'):
                startup.log_stage('stopped')
            write.assert_not_called()
            info.st_rdev = startup.os.makedev(1, 11)
            write.side_effect = lambda fd, data: len(data) - 1
            with self.assertRaises(OSError):
                startup.log_stage('stopped')
            self.assertEqual(write.call_count, 1)

    def test_logging_failure_still_parks_without_retry(self):
        with patch.object(startup, 'log_stage', side_effect=OSError('private detail')) as log, \
                patch.object(startup, 'prepare') as prepare, \
                patch.object(startup.time, 'sleep', side_effect=SystemExit('parked')), \
                patch('builtins.print', side_effect=OSError('console unavailable')) as output:
            with self.assertRaisesRegex(SystemExit, 'parked'):
                startup.main()
            prepare.assert_not_called()
            self.assertEqual(log.call_count, 2)
            self.assertNotIn('private detail', repr(output.call_args_list))


if __name__ == '__main__':
    unittest.main()
