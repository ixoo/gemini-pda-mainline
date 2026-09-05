#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Hardware-free collector fixtures: fake SSH processes only, never a socket."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import runpy
import signal
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('baseline_collector', HERE / 'collect-baseline.py')
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)
HISTORY_FIXTURE = runpy.run_path(str(C.HISTORICAL / 'test_runtime_tools.py'))
WORK_ROOT = Path(os.environ.get('GEMINI_TEST_WORK_ROOT', '/tmp')).resolve()
BOOT = HISTORY_FIXTURE['MAINLINE']
RECOVERY = HISTORY_FIXTURE['RECOVERY']


def write(path, data):
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    path.write_bytes(data)
    path.chmod(0o600)


def make_fixture(root):
    repo = root / 'repo'
    repo.mkdir(mode=0o700)
    subprocess.run(['/usr/bin/git', 'init', '-q', str(repo)], check=True, capture_output=True)
    (repo / '.gitignore').write_text('artifacts/\n')
    raw_boot = b'fixture-not-a-bootable-image'
    padded = raw_boot + bytes(16777216 - len(raw_boot))
    config = b'fixture-kernel-configuration\n'
    candidate_dir = repo / 'artifacts/a53-authenticated/candidates' / ('candidate-' + C.sha(raw_boot))
    keys = repo / 'artifacts/credentials/a53-auth'
    for path in (candidate_dir, keys):
        path.mkdir(mode=0o700, parents=True)
    (repo / 'artifacts/a53-authenticated').chmod(0o700)
    public_blob = b'\0\0\0\x0bssh-ed25519\0\0\0\x20' + bytes(32)
    known = b'10.15.19.82 ssh-ed25519 ' + base64.b64encode(public_blob) + b'\n'
    authorized = b'fixture-authorization-not-a-real-key\n'
    for name, data in (('known_hosts', known), ('admin', b'fixture-not-a-private-key\n'),
                       ('authorized_keys', authorized)):
        write(keys / name, data)
    members = {name: {'mode': '0o100755', 'size': 32, 'sha256': C.sha(name.encode())}
               for name in C.MEMBERS.values()}
    members['etc/gemini-us.bkeymap']['sha256'] = C.MAP_SHA
    members['root/.ssh/authorized_keys'] = {'mode': '0o100600', 'size': len(authorized), 'sha256': C.sha(authorized)}
    candidate = {'schema': 1, 'experiment': 'a53-authenticated-baseline', 'secret_bearing': True,
                 'physical_admission': False, 'preparation_state': 'preparing',
                 'members': members, 'known_hosts_sha256': C.sha(known),
                 'files': {name: C.sha(data) for name, data in
                           (('boot.img', raw_boot), ('boot2-padded.img', padded), ('kernel.config', config))}}
    for name, data in (('boot.img', raw_boot), ('boot2-padded.img', padded), ('kernel.config', config)):
        write(candidate_dir / name, data)
    candidate_raw = (json.dumps(candidate, sort_keys=True) + '\n').encode()
    write(candidate_dir / 'candidate.json', candidate_raw)
    padded_sha = candidate['files']['boot2-padded.img']
    receipt = {'experiment': 'a53-authenticated-baseline', 'target_logical_name': 'boot2',
               'boot2_device_guard': 'passed',
               'boot2_device_guard_sha256': '0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf',
               'fresh_predecessor_backup': 'no', 'candidate_sha256': padded_sha,
               'candidate_manifest_sha256': C.sha(candidate_raw), 'readback_sha256': padded_sha,
               'temporary_readback_removed': 'yes', 'shutdown': 'requested-after-evidence-flush',
               'post_shutdown_reachability': 'unreachable', 'reboot': 'no',
               'next_action': 'owner-physically-selects-boot2', 'result': 'skipped-already-matching',
               'target': '/dev/mmcblk0p30', 'root': '/dev/mmcblk0p29',
               'target_major_minor': '179:30', 'root_major_minor': '179:29',
               'predecessor_sha256': padded_sha, 'boot_id': RECOVERY,
               'power': '1|90|Good|0', 'poweroff_ssh_rc': '0'}
    deployment = repo / 'artifacts/a53-authenticated/records/deployment-summary.txt'
    receipt_raw = ''.join(key + '=' + value + '\n' for key, value in receipt.items()).encode()
    write(deployment, receipt_raw)
    admission = {'schema': 1, 'experiment': 'a53-authenticated-baseline', 'action': 'first-baseline-observation',
                 'admission_id': '00000000-0000-0000-0000-000000000003', 'candidate_sha256': C.sha(raw_boot),
                 'candidate_manifest_sha256': C.sha(candidate_raw), 'deployment_receipt_sha256': C.sha(receipt_raw),
                 'collector_sha256': C.sha((HERE / 'collect-baseline.py').read_bytes()),
                 'custodian_role': 'Fixture custodian', 'custody_handoff_sha256': '1' * 64,
                 'custody_exclusive': True, 'physical_selection_confirmed': True,
                 'no_other_device_operations': True, 'observation_budget': 1}
    admission_path = deployment.with_name('admission.json')
    write(admission_path, (json.dumps(admission) + '\n').encode())
    return repo, admission_path, deployment


def good_capture(prepared):
    pre = {'expected_candidate_sha256': prepared['admission']['candidate_sha256'],
           **{key: prepared['candidate']['members'][member]['sha256'] for key, member in C.MEMBERS.items()},
           'boot_id_before': BOOT, 'init_boot_id': BOOT,
           'live_config_sha256': prepared['candidate']['files']['kernel.config'], 'console_status': 'ready',
           'active_vt': 'tty1', 'kernel_vt_console_count': '0', 'map_verify_before': 'pass',
           'matrix_input_count': '1', 'historical_auto_observers': 'absent'}
    post = {'boot_id_after': BOOT, 'cpu_online_after': '0-7', 'cpu_offline_after': '8-9',
            'map_verify_after': 'pass', 'console_status_after': 'ready', 'active_vt_after': 'tty1',
            'kernel_vt_console_count_after': '0'}
    text = C.BEGIN + '\n' + ''.join(key + '=' + value + '\n' for key, value in pre.items()) + C.PRE_END + '\n'
    text += HISTORY_FIXTURE['frame']() + C.POST_BEGIN + '\n'
    text += ''.join(key + '=' + value + '\n' for key, value in post.items()) + C.END + '\n'
    return text.encode()


def fake_ssh(root, capture, scenario='pass', attempt=None):
    path = root / 'fake-ssh'
    source = ('#!' + sys.executable + '\nimport json,os,pathlib,signal,sys,time\n' +
              f"root=pathlib.Path({str(root)!r})\n" +
              "with (root/'calls').open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')\n")
    if attempt:
        source += f"assert pathlib.Path({str(attempt / 'claim.json')!r}).is_file()\n"
    if scenario == 'early-exit':
        source += 'sys.exit(7)\n'
    else:
        source += "data=sys.stdin.buffer.read()\n(root/'received-stdin').write_bytes(data)\n"
        if scenario == 'pass':
            source += f'sys.stdout.buffer.write({capture!r})\n'
        elif scenario == 'stdout-limit':
            source += f'os.write(1,b"x"*{C.STDOUT_LIMIT + 4096})\ntime.sleep(5)\n'
        elif scenario == 'stderr-limit':
            source += f'os.write(2,b"x"*{C.STDERR_LIMIT + 4096})\ntime.sleep(5)\n'
        elif scenario in ('timeout', 'interrupt'):
            source += 'os.write(1,b"partial-evidence\\n")\n'
            if scenario == 'interrupt':
                source += 'os.kill(os.getppid(),signal.SIGTERM)\n'
            source += 'time.sleep(5)\n'
    path.write_text(source)
    path.chmod(0o700)
    return path


class CollectorTests(unittest.TestCase):
    def setUp(self):
        prior_umask = os.umask(0o077)
        self.addCleanup(os.umask, prior_umask)
        self.temporary = tempfile.TemporaryDirectory(prefix='a53-collect-fixture-', dir=WORK_ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo, self.admission, self.deployment = make_fixture(self.root)

    def prepared(self):
        return C.prepare(self.repo, self.admission, self.deployment)

    def rewrite_admission(self, **changes):
        data = json.loads(self.admission.read_bytes())
        data.update(changes)
        write(self.admission, (json.dumps(data) + '\n').encode())

    def classify(self, data=None):
        prepared = self.prepared()
        return C.classify_capture(prepared, data or good_capture(prepared), b'',
                                  {'exit_status': 0, 'reason': None, 'stdin_complete': True})

    def test_dry_run_never_consumes_or_starts_ssh(self):
        result = C.collect(self.prepared())
        self.assertEqual(result['classification'], 'dry-run')
        self.assertFalse((self.repo / 'artifacts/a53-authenticated/attempts').exists())
        self.assertFalse((self.root / 'calls').exists())

    def test_good_fake_connection_claim_precedes_process(self):
        prepared = self.prepared()
        attempt = self.repo / 'artifacts/a53-authenticated/attempts' / prepared['admission']['admission_id']
        ssh = fake_ssh(self.root, good_capture(prepared), attempt=attempt)
        result = C.collect(prepared, True, _ssh=ssh, _timeout=3)
        self.assertEqual(result['classification'], 'baseline-observation-only-pass')
        self.assertEqual(result['readiness'], 'not-established')
        self.assertEqual((self.root / 'received-stdin').read_bytes(), C.remote_script(prepared))
        self.assertEqual(len((self.root / 'calls').read_text().splitlines()), 1)
        for path in attempt.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        with self.assertRaises(FileExistsError):
            C.collect(prepared, True, _ssh=ssh)
        self.assertEqual(len((self.root / 'calls').read_text().splitlines()), 1)

    def test_existing_interrupted_attempt_refuses(self):
        prepared = self.prepared()
        attempt = self.repo / 'artifacts/a53-authenticated/attempts' / prepared['admission']['admission_id']
        attempt.mkdir(parents=True, mode=0o700)
        attempt.parent.chmod(0o700)
        with self.assertRaises(FileExistsError):
            C.collect(prepared, True, _ssh=self.root / 'never-executed')

    def test_stream_limits_and_partial_evidence(self):
        for scenario, expected in (('stdout-limit', C.STDOUT_LIMIT), ('stderr-limit', C.STDERR_LIMIT)):
            with self.subTest(scenario=scenario):
                directory = self.root / scenario
                directory.mkdir(mode=0o700)
                ssh = fake_ssh(directory, b'', scenario)
                result = C.run_once(C.ssh_command(self.root, ssh), b'fixed\n', directory, 3)
                self.assertEqual(result['reason'], scenario)
                self.assertEqual((directory / (scenario.split('-')[0] + '.txt')).stat().st_size, expected)

    def test_timeout_preserves_partial_output_and_reaps(self):
        directory = self.root / 'timeout'
        directory.mkdir(mode=0o700)
        ssh = fake_ssh(directory, b'', 'timeout')
        result = C.run_once(C.ssh_command(self.root, ssh), b'fixed\n', directory, .3)
        self.assertEqual(result['reason'], 'outer-timeout')
        self.assertLess(result['elapsed_seconds'], 1)
        self.assertEqual((directory / 'stdout.txt').read_bytes(), b'partial-evidence\n')

    def test_interruption_restores_parent_signal_handler(self):
        directory = self.root / 'interrupt'
        directory.mkdir(mode=0o700)
        ssh = fake_ssh(directory, b'', 'interrupt')
        prior = signal.getsignal(signal.SIGTERM)
        result = C.run_once(C.ssh_command(self.root, ssh), b'fixed\n', directory, 3)
        self.assertEqual(result['reason'], 'interrupted')
        self.assertEqual(signal.getsignal(signal.SIGTERM), prior)
        self.assertEqual((directory / 'stdout.txt').read_bytes(), b'partial-evidence\n')

    def test_early_ssh_exit_is_inconclusive(self):
        prepared = self.prepared()
        ssh = fake_ssh(self.root, b'', 'early-exit')
        result = C.collect(prepared, True, _ssh=ssh, _timeout=3)
        self.assertEqual(result['classification'], 'inconclusive')
        self.assertNotEqual(result['process']['exit_status'], 0)

    def test_caller_fixed_larger_log_cap(self):
        directory = self.root / 'larger-log'
        directory.mkdir(mode=0o700)
        payload = b'x' * (C.STDOUT_LIMIT + 1)
        ssh = fake_ssh(directory, payload)
        result = C.run_once(C.ssh_command(self.root, ssh), b'fixed\n', directory, 3, stdout_limit=3145728)
        self.assertIsNone(result['reason'])
        self.assertEqual(result['stdout_bytes'], len(payload))

    def test_all_ssh_ambient_authentication_and_forwarding_paths_disabled(self):
        command = C.ssh_command(self.root)
        self.assertEqual(command[0], '/usr/bin/ssh')
        self.assertEqual(command[-2:], ['root@10.15.19.82', '/bin/busybox sh -s'])
        for setting in ('BatchMode=yes', 'IdentitiesOnly=yes', 'IdentityAgent=none',
                        'StrictHostKeyChecking=yes', 'GlobalKnownHostsFile=/dev/null',
                        'PasswordAuthentication=no', 'KbdInteractiveAuthentication=no',
                        'ConnectionAttempts=1', 'ClearAllForwardings=yes', 'ControlPath=none',
                        'ProxyCommand=none', 'ProxyJump=none', 'UpdateHostKeys=no'):
            self.assertIn(setting, command)
        self.assertEqual(command[1:4], ['-F', '/dev/null', '-T'])

    def test_unconfirmed_custody_refuses(self):
        self.rewrite_admission(custody_exclusive=False)
        with self.assertRaisesRegex(ValueError, 'custody/budget'):
            self.prepared()

    def test_budget_change_refuses(self):
        self.rewrite_admission(observation_budget=2)
        with self.assertRaisesRegex(ValueError, 'custody/budget'):
            self.prepared()

    def test_collector_drift_refuses(self):
        self.rewrite_admission(collector_sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'collector revision'):
            self.prepared()

    def test_candidate_manifest_drift_refuses(self):
        self.rewrite_admission(candidate_manifest_sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'candidate manifest'):
            self.prepared()

    def test_wrong_known_host_refuses(self):
        keys = self.repo / 'artifacts/credentials/a53-auth'
        write(keys / 'known_hosts', b'wrong\n')
        with self.assertRaisesRegex(ValueError, 'known_hosts identity'):
            self.prepared()

    def test_publicly_readable_key_refuses(self):
        (self.repo / 'artifacts/credentials/a53-auth/admin').chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'private input permissions'):
            self.prepared()

    def test_symlink_key_refuses(self):
        keys = self.repo / 'artifacts/credentials/a53-auth'
        (keys / 'admin').unlink()
        (keys / 'admin').symlink_to(keys / 'known_hosts')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.prepared()

    def test_deployment_receipt_digest_refuses(self):
        self.rewrite_admission(deployment_receipt_sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'deployment receipt identity'):
            self.prepared()

    def test_deployment_manifest_binding_refuses(self):
        data = self.deployment.read_text()
        manifest = json.loads(self.admission.read_bytes())['candidate_manifest_sha256']
        write(self.deployment, data.replace('candidate_manifest_sha256=' + manifest,
                                          'candidate_manifest_sha256=' + '0' * 64).encode())
        self.rewrite_admission(deployment_receipt_sha256=C.sha(self.deployment.read_bytes()))
        with self.assertRaises(ValueError):
            self.prepared()

    def test_duplicate_admission_fields_refuse(self):
        data = self.admission.read_text().replace('{', '{"schema":1,', 1)
        write(self.admission, data.encode())
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            self.prepared()

    def test_exact_historical_observer_is_embedded_once(self):
        script = C.remote_script(self.prepared())
        original = (C.HISTORICAL / 'remote_observe.sh').read_bytes()
        self.assertEqual(script.count(original), 1)
        for forbidden in (b'/dev/mmcblk', b'loadkmap', b'--preflight', b'>/sys', b'> /sys', b'/bin/reboot\n'):
            self.assertNotIn(forbidden, script)
        self.assertEqual(script.count(b'/bin/console-keymap-verify --verify '), 2)
        result = subprocess.run(['/bin/bash', '-n'], input=script, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_valid_frame(self):
        self.assertEqual(self.classify()['classification'], 'baseline-observation-only-pass')

    def test_historical_failure_retains_rejection(self):
        data = good_capture(self.prepared()).replace(b'mmc_error_count=0', b'mmc_error_count=1')
        result = self.classify(data)
        self.assertEqual(result['classification'], 'baseline-observation-rejected')
        self.assertEqual(result['reason'], 'mmc_error_count')

    def test_missing_and_trailing_frames(self):
        data = good_capture(self.prepared())
        for changed in (data[:-20], b'banner\n' + data, data + b'extra\n', data.replace(C.PRE_END.encode(), b'')):
            with self.subTest(changed=changed[:20]):
                self.assertEqual(self.classify(changed)['classification'], 'inconclusive')

    def test_unknown_historical_field(self):
        data = good_capture(self.prepared()).replace(b'cpu_possible=0-9', b'unknown=1\ncpu_possible=0-9')
        self.assertEqual(self.classify(data)['classification'], 'inconclusive')

    def test_unchanged_recovery_boot_refuses(self):
        data = good_capture(self.prepared()).replace(BOOT.encode(), RECOVERY.encode())
        self.assertEqual(self.classify(data)['classification'], 'inconclusive')

    def test_postflight_boot_change_refuses(self):
        data = good_capture(self.prepared()).replace(('boot_id_after=' + BOOT).encode(),
                                                   ('boot_id_after=' + RECOVERY).encode())
        self.assertEqual(self.classify(data)['classification'], 'inconclusive')

    def test_kernel_logs_on_keyboard_vt_refuse(self):
        data = good_capture(self.prepared()).replace(b'kernel_vt_console_count_after=0', b'kernel_vt_console_count_after=1')
        self.assertEqual(self.classify(data)['classification'], 'inconclusive')

    def test_map_readback_failure_refuses(self):
        data = good_capture(self.prepared()).replace(b'map_verify_after=pass', b'map_verify_after=failed')
        self.assertEqual(self.classify(data)['classification'], 'inconclusive')

    def test_duplicate_live_identity_refuses(self):
        data = good_capture(self.prepared()).replace(b'active_vt=tty1\n', b'active_vt=tty1\nactive_vt=tty1\n')
        self.assertEqual(self.classify(data)['classification'], 'inconclusive')


if __name__ == '__main__':
    unittest.main()
