#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic local fixtures only; every transport is replaced and Popen refused."""
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
L = runpy.run_path(str(HERE / 'collect-emmc.py'))
G = L['collect'].__globals__
C, F, S, E = L['C'], L['F'], L['S'], L['E']
T = runpy.run_path(str(L['EXPERIMENT'] / 'baseline/scripts/test-collect-baseline.py'))
FIRST, RECOVERED, OLD, BOOT = [f'00000000-0000-0000-0000-{n:012d}' for n in (1, 2, 3, 4)]
ADMISSION, BASELINE = [f'00000000-0000-0000-0000-{n:012d}' for n in (5, 6)]


def write(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(0o600)


def process(out, err=b'', **changes):
    return {'exit_status': 0, 'reason': None, 'stdin_complete': True, 'stdout_bytes': len(out),
            'stderr_bytes': len(err), 'elapsed_seconds': 0.1} | changes


def read_frame(prepared, **changes):
    values = dict(boot_id=BOOT, kernel_release=S['RELEASE'],
        expected_sha256=prepared['candidate']['files']['boot2-padded.img'],
        busybox_sha256=prepared['candidate']['members']['bin/busybox']['sha256'],
        target='/dev/mmcblk0p31', target_major_minor='179:31', target_start_sector='1024',
        read_attempts='1', requested_bytes='16777216', read_timeout_seconds='20', dd_status='0',
        read_sha256=prepared['candidate']['files']['boot2-padded.img'], elapsed_seconds='1',
        controller_error_count='0', kernel_log_before_sha256='a' * 64, kernel_log_after_sha256='b' * 64,
        guards_after='pass', device_storage_writes='none', mount_requests='none', sysfs_writes='none')
    values.update(changes)
    return (E['BEGIN'] + '\n' + ''.join(k + '=' + v + '\n' for k, v in values.items()) + E['END'] + '\n').encode()


class LauncherTests(unittest.TestCase):
    def setUp(self):
        old_umask = os.umask(0o077)
        self.addCleanup(os.umask, old_umask)
        work = L['REPO'] / 'artifacts/a53-authenticated/development/emmc-runtime-tests'
        work.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='fixture-', dir=work)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        # A missed mock fails before any process/network/device operation.
        self.no_process = patch('subprocess.Popen', side_effect=AssertionError('fixture may not spawn a process'))
        self.no_process.start()
        self.addCleanup(self.no_process.stop)
        observer = (L['EXPERIMENT'] / 'emmc/observe.sh').read_bytes()
        candidate = {'members': {name: {'sha256': 'a' * 64, 'size': 1, 'mode': '0o100755'} for name in C['MEMBERS'].values()},
                     'files': {'boot2-padded.img': 'b' * 64, 'kernel.config': 'c' * 64},
                     'known_hosts_sha256': L['sha'](b'fixture-host-pin')}
        candidate['members']['bin/emmc-observe'] = {'sha256': L['sha'](observer), 'size': len(observer), 'mode': '0o100755'}
        self.prepared = {'candidate': candidate, 'candidate_raw': b'synthetic-candidate', 'deployment_raw': b'synthetic-receipt',
                         'recovery_id': OLD, 'keys': self.root / 'absent-credentials',
                         'admission': {'candidate_sha256': 'd' * 64}}
        self.admission = {'schema': 1, 'experiment': 'a53-emmc-readonly', 'action': 'single-read-session',
            'admission_id': ADMISSION, 'baseline_admission_id': BASELINE,
            'baseline_manifest_sha256': L['sha'](b'baseline-manifest'), 'confirmation_manifest_sha256': 'f' * 64,
            'candidate_manifest_sha256': L['sha'](self.prepared['candidate_raw']),
            'deployment_receipt_sha256': L['sha'](self.prepared['deployment_raw']),
            'source_identity': L['source_identity'](), 'action_budgets': copy.deepcopy(L['BUDGETS']),
            'custodian_role': 'Synthetic fixture', 'custody_handoff_sha256': 'e' * 64,
            'custody_exclusive': True, 'physical_selection_confirmed': True,
            'no_other_device_operations': True, 'stable_power_confirmed': True,
            'prerequisite_selector': 'original-strict', 'prerequisite_phase_manifests': None}
        self.dependency = {'prepared': self.prepared, 'first_boot': FIRST, 'recovered_boot': RECOVERED,
                           'confirmation': {'fixture': True}}
        self.context = {'admission': self.admission, 'admission_raw': L['json_bytes'](self.admission), 'dependency': self.dependency}
        self.capture = T['good_capture'](self.prepared).replace(T['BOOT'].encode(), BOOT.encode())
        self.calls = []

    def test_admission_refuses_missing_custody_budget_and_identity(self):
        L['check_admission'](self.admission)
        changes = [('schema', True), ('action', 'first-baseline-observation'), ('admission_id', BASELINE),
                   ('baseline_admission_id', '../escape'), ('source_identity', {}), ('extra', True)]
        changes += [(key, False) for key in ('custody_exclusive', 'physical_selection_confirmed', 'no_other_device_operations', 'stable_power_confirmed')]
        for key, value in changes:
            bad = copy.deepcopy(self.admission); bad[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError): L['check_admission'](bad)
        for key in L['BUDGETS']:
            bad = copy.deepcopy(self.admission); bad['action_budgets'][key] += 1
            with self.subTest(budget=key), self.assertRaises(ValueError): L['check_admission'](bad)
        bad = copy.deepcopy(self.admission); bad['action_budgets']['read_attempts'] = True
        with self.assertRaises(ValueError): L['check_admission'](bad)

    def test_dry_run_creates_no_claim_or_connection(self):
        with patch.dict(G, {'ATTEMPT_ROOT': self.root / 'attempt'}):
            self.assertEqual(L['collect'](self.context)['classification'], 'dry-run')
            self.assertFalse((self.root / 'attempt').exists())
        self.assertEqual(self.calls, [])

    def test_staged_cli_cannot_execute(self):
        with self.assertRaisesRegex(ValueError, 'execution disabled'):
            L['collect'](self.context, True)

    def test_exact_candidate_observer_command_and_no_extra_read(self):
        script = L['script_for'](self.context, 'read', BOOT)
        self.assertEqual(script.count(b'exec /bin/busybox sh /bin/emmc-observe '), 1)
        self.assertIn(L['sha']((L['EXPERIMENT'] / 'emmc/observe.sh').read_bytes()).encode(), script)
        self.assertIn(b'/bin/busybox', script)
        for phase in ('pre', 'post'):
            script = L['script_for'](self.context, phase, BOOT)
            self.assertNotIn(b'exec /bin/busybox sh /bin/emmc-observe ', script)
            self.assertTrue(script.endswith(C['remote_script'](self.prepared)))

    def fixture_collect(self, changes=None):
        changes = changes or {}
        real_regular = G['regular']
        def local_regular(path, limit, *args, **kwargs):
            if path == self.prepared['keys'] / 'known_hosts': return b'fixture-host-pin'
            self.assertTrue(path.is_relative_to(self.root))
            return real_regular(path, limit, *args, **kwargs)
        def fake_transport(command, script, directory, timeout, **limits):
            phase = directory.name
            self.assertTrue((directory / 'claim.json').is_file())
            self.assertTrue((directory.parent / 'claim.json').is_file())
            self.assertEqual(json.loads((directory / 'claim.json').read_bytes())['budget'], 'consumed')
            self.assertEqual((directory / 'command.sh').read_bytes(), script)
            self.assertEqual(command[-2:], ['root@10.15.19.82', '/bin/busybox sh -s'])
            self.assertEqual((timeout, limits['stdout_limit']), L['PHASES'][phase])
            self.assertEqual(limits['stderr_limit'], 16384)
            self.calls.append(phase)
            out = read_frame(self.prepared) if phase == 'read' else self.capture
            edit = changes.get(phase, {})
            out = edit.get('out', out); err = edit.get('err', b'')
            write(directory / 'stdout.txt', out); write(directory / 'stderr.txt', err)
            return process(out, err, **edit.get('process', {}))
        with patch.dict(G, {'execution_gate': lambda: None, '__file__': str(L['EXPERIMENT'] / 'emmc/collect-emmc.py'),
                            'ATTEMPT_ROOT': self.root / 'attempt', 'regular': local_regular,
                            'source_identity': lambda: self.admission['source_identity'],
                            'completed_baseline': lambda _: self.dependency}), \
             patch.dict(C, {'run_once': fake_transport}):
            return L['collect'](self.context, True)

    def test_pre_read_post_claims_and_no_automatic_completion(self):
        result = self.fixture_collect()
        self.assertEqual(self.calls, ['pre', 'read', 'post'])
        self.assertEqual(result['classification'], 'read-serviceability-only-pass')
        self.assertIn('changed-ID-known-good-recovery', result['remaining'])
        self.assertTrue((self.root / 'attempt/SHA256SUMS').is_file())
        self.assertNotIn('experiment-pass', str(result))

    def test_failed_preflight_never_reads(self):
        result = self.fixture_collect({'pre': {'out': b'incomplete\n'}})
        self.assertEqual(self.calls, ['pre'])
        self.assertEqual(result['classification'], 'inconclusive')

    def test_read_transport_timeout_interrupt_and_limits_stop_postflight(self):
        for changes in ({'reason': 'deadline'}, {'reason': 'interrupted'}, {'stdin_complete': False},
                        {'stdout_bytes': 8193}, {'exit_status': 255}):
            with self.subTest(process=changes):
                # Every case uses a fresh synthetic scope, never resets a real claim.
                case_root = self.root / str(len(self.calls)); case_root.mkdir(mode=0o700)
                with patch.object(self, 'root', case_root):
                    result = self.fixture_collect({'read': {'process': changes}})
                self.assertEqual(self.calls[-2:], ['pre', 'read'])
                self.assertEqual(result['classification'], 'inconclusive')

    def test_observer_timeout_and_definite_mismatch_keep_distinct_results(self):
        for status, digest, expected in [('137', 'b' * 64, 'inconclusive'), ('0', 'c' * 64, 'fail')]:
            case_root = self.root / status; case_root.mkdir(mode=0o700)
            with patch.object(self, 'root', case_root):
                result = self.fixture_collect({'read': {'out': read_frame(self.prepared, dd_status=status, read_sha256=digest)}})
            self.assertEqual(self.calls[-2:], ['pre', 'read'])
            self.assertEqual(result['classification'], expected)
            self.assertEqual(result['phases']['read']['classification'], 'inconclusive' if status == '137' else 'fail')

    def test_second_attempt_and_new_uuid_do_not_renew_budget(self):
        self.fixture_collect()
        self.admission['admission_id'] = '00000000-0000-0000-0000-000000000007'
        with self.assertRaises(FileExistsError): self.fixture_collect()
        self.assertEqual(self.calls, ['pre', 'read', 'post'])

    def test_old_or_changed_boot_refuses(self):
        for phase, old in [('pre', FIRST), ('pre', RECOVERED), ('post', FIRST)]:
            with self.subTest(phase=phase, old=old), self.assertRaises(ValueError):
                data = self.capture.replace(BOOT.encode(), old.encode())
                L['classify_phase'](self.context, phase, data, b'', process(data), BOOT)

    def test_process_inventory_counts_and_elapsed_are_strict(self):
        for changes in ({'elapsed_seconds': float('nan')}, {'elapsed_seconds': 42}, {'stdout_bytes': True},
                        {'exit_status': False}, {'stdin_complete': 1}, {'extra': True}):
            with self.subTest(process=changes), self.assertRaises(ValueError):
                L['process_ok'](b'x', b'', process(b'x', **changes), 40, 8192)

    def baseline_archive(self):
        # The actual shared verifier and its credential-free factory run here.
        # Only candidate/image/key validation through C.prepare is substituted.
        fixture_path = L['source_path'](L['VERIFIER_NAME']).with_name('test-verified-baseline.py')
        fixture = runpy.run_path(str(fixture_path))
        evidence = self.root / 'artifacts/a53-authenticated'
        evidence.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        observer = (L['EXPERIMENT'] / 'emmc/observe.sh').read_bytes()
        member = {'mode': '0o100755', 'size': len(observer), 'sha256': L['sha'](observer)}
        bindings, context, sessions = fixture['make_archive'](evidence, member_overrides={'bin/emmc-observe': member})
        prepared = context['prepared'] | {'keys': self.root / 'absent-credentials'}
        admission = copy.deepcopy(self.admission)
        admission.update(baseline_admission_id=bindings['admission_id'],
                         baseline_manifest_sha256=bindings['baseline_manifest_sha256'],
                         confirmation_manifest_sha256=bindings['confirmation_manifest_sha256'],
                         candidate_manifest_sha256=bindings['candidate_manifest_sha256'],
                         deployment_receipt_sha256=L['sha'](prepared['deployment_raw']))
        return fixture, context, sessions, prepared, admission

    def verified_dependency(self, prepared, admission, *, before_return=None):
        def candidate_boundary(repo, admission_path, deployment_path):
            attempt = self.root / 'artifacts/a53-authenticated/attempts' / admission['baseline_admission_id']
            self.assertEqual((repo, admission_path, deployment_path),
                             (self.root, attempt / 'admission.json', attempt / 'deployment-summary.txt'))
            if before_return is not None: before_return()
            return prepared
        with patch.dict(G, {'REPO': self.root}), patch.dict(C, {'prepare': candidate_boundary}):
            return L['completed_baseline'](admission)

    def test_actual_shared_archive_chain_and_candidate_boundary(self):
        fixture, context, sessions, prepared, admission = self.baseline_archive()
        dependency = self.verified_dependency(prepared, admission)
        verified = dependency['verification']
        self.assertIs(dependency['prepared'], prepared)
        self.assertEqual(dependency['first_boot'], context['baseline']['boot_id'])
        self.assertEqual(dependency['recovered_boot'], fixture['NEW'])
        self.assertEqual(verified['classification'], 'verified-first-authenticated-baseline-and-recovery')
        self.assertFalse(verified['dependent_admission'])
        self.assertEqual(verified['baseline_admission_sha256'], L['sha'](prepared['admission_raw']))
        self.assertEqual(verified['deployment_receipt_sha256'], L['sha'](prepared['deployment_raw']))
        self.assertEqual(set(verified['phase_manifests']), {'auth-checks', 'preserve-log', 'request-recovery'})
        self.assertFalse((self.root / 'absent-credentials').exists())
        self.assertEqual(list(self.root.rglob('*.img')), [])
        self.assertEqual(self.calls, [])
        # Candidate admission remains its own mandatory boundary even when the
        # archived baseline chain independently verifies.
        with patch.dict(G, {'REPO': self.root}), patch.dict(C, {'prepare': lambda *_: (_ for _ in ()).throw(ValueError('candidate refused'))}):
            with self.assertRaisesRegex(ValueError, 'candidate refused'): L['completed_baseline'](admission)

    def test_actual_shared_raw_chain_mutations_cannot_reuse_stored_success(self):
        fixture, context, sessions, prepared, admission = self.baseline_archive()
        locations = [(context['attempt'] / 'stdout.txt', b'raw baseline failure\n'),
                     (sessions / 'auth-checks/positive-probe/stdout.txt', b'wrong boot\n'),
                     (sessions / 'preserve-log/kmsg.log', b'forged log\n'),
                     (sessions / 'request-recovery/native-reboot/stdout.txt', b'not a native request\n'),
                     (sessions / 'confirm-recovery/known-good-probe/command.sh', b'true\n'),
                     (sessions / 'confirm-recovery/result.json', b'{"baseline_classification":"first-authenticated-baseline-and-recovery-pass"}\n')]
        for path, bad in locations:
            original = path.read_bytes(); write(path, bad)
            with self.subTest(path=path.relative_to(self.root).as_posix()), self.assertRaises(ValueError):
                self.verified_dependency(prepared, admission)
            write(path, original)

    def test_candidate_archive_hash_and_identity_cross_bindings(self):
        _fixture, _context, _sessions, prepared, admission = self.baseline_archive()
        for key in ('admission_raw', 'deployment_raw', 'candidate_raw'):
            bad = copy.deepcopy(prepared); bad[key] += b'\n'
            with self.subTest(raw=key), self.assertRaises(ValueError): self.verified_dependency(bad, admission)
        for key, value in (('recovery_id', BOOT), ('admission_id', BASELINE), ('candidate_sha256', 'e' * 64)):
            bad = copy.deepcopy(prepared)
            if key == 'recovery_id': bad[key] = value
            else: bad['admission'][key] = value
            with self.subTest(identity=key), self.assertRaises(ValueError): self.verified_dependency(bad, admission)
        bad = copy.deepcopy(prepared); bad['candidate']['files']['boot.img'] = 'e' * 64
        with self.assertRaises(ValueError): self.verified_dependency(bad, admission)
        for key in ('candidate_manifest_sha256', 'deployment_receipt_sha256', 'baseline_manifest_sha256', 'confirmation_manifest_sha256'):
            bad = copy.deepcopy(admission); bad[key] = 'e' * 64
            with self.subTest(pin=key), self.assertRaises(ValueError): self.verified_dependency(prepared, bad)

    def test_archive_substitution_after_candidate_preparation_refuses(self):
        fixture, _context, sessions, prepared, admission = self.baseline_archive()
        final = sessions / 'confirm-recovery'
        def replace_archive():
            write(final / 'known-good-probe/stdout.txt', b'kernel=3.18.41+\narchitecture=aarch64\nboot_id=' + OLD.encode() + b'\n')
            fixture['refresh'](final)
        with self.assertRaises(ValueError): self.verified_dependency(prepared, admission, before_return=replace_archive)

    def test_final_confirmation_swap_after_snapshot_cannot_supply_acceptance(self):
        fixture, context, sessions, prepared, admission = self.baseline_archive()
        final = sessions / 'confirm-recovery'; output = final / 'known-good-probe/stdout.txt'
        good = output.read_bytes()
        write(output, good.replace(fixture['NEW'].encode(), context['baseline']['boot_id'].encode()))
        pin = fixture['refresh'](final)
        admission['confirmation_manifest_sha256'] = pin
        shared = L['V']['verify'].__globals__
        original = shared['confirm_inventory']; swapped = []
        def snapshot_then_swap(*args):
            result = original(*args)
            write(output, good); swapped.append(True)
            return result
        # Instrument only the exact I/O boundary to reproduce the reviewed race;
        # aggregate verification and every genuine parser still execute.
        with patch.dict(shared, {'confirm_inventory': snapshot_then_swap}), self.assertRaises(ValueError):
            self.verified_dependency(prepared, admission)
        self.assertEqual(swapped, [True])

    def test_shared_source_resolution_refuses_absence_drift_and_symlinks(self):
        for name in (L['VERIFIER_NAME'], L['GUARD_NAME']):
            with self.subTest(source=name):
                expected = L['source_path'](name).read_bytes()
                fake_repo = self.root / ('source-fixture-' + Path(name).stem)
                fake_repo.mkdir(mode=0o700)
                experiment = fake_repo / 'experiment'
                tracked = experiment / name
                private_here = fake_repo / 'artifacts/a53-authenticated/development/emmc-launcher'
                private = fake_repo / 'artifacts/a53-authenticated/development/baseline-proof/verified_baseline.py' \
                    if name == L['VERIFIER_NAME'] else private_here / 'guarded_observation.py'
                write(private, expected)
                with patch.dict(G, {'REPO': fake_repo, 'EXPERIMENT': experiment, 'HERE': private_here}):
                    with self.assertRaises(ValueError): L['source_path'](name)
                    write(tracked, expected)
                    self.assertEqual(L['source_path'](name), tracked)
                    tracked.unlink(); tracked.symlink_to(private)
                    with self.assertRaises(ValueError): L['source_path'](name)
                    tracked.unlink(); private.unlink()
                    with self.assertRaises(ValueError): L['source_path'](name)
                    write(private, expected)
                    with patch.dict(G, {'HERE': fake_repo / 'elsewhere'}), self.assertRaises(ValueError):
                        L['source_path'](name)
                # A present tracked source must never fall back to private bytes
                # when its digest differs from the reviewed source inventory.
                original_path = G['source_path']
                write(tracked, expected + b'\n')
                with patch.dict(G, {'source_path': lambda key: tracked if key == name else original_path(key)}), self.assertRaises(ValueError):
                    L['source_identity']()


if __name__ == '__main__':
    unittest.main(verbosity=2)
