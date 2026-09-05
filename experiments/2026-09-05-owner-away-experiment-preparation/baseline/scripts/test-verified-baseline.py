#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic retained archives only; creates no keys, sockets or boot images."""
import builtins
import copy
import io
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('aggregate', HERE / 'verified_baseline.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
C, F, D = A.tools()
CF = A.module('collect_fixture', A.REPO / A.BASELINE / 'test-collect-baseline.py')
SF = A.module('session_fixture', A.REPO / A.BASELINE / 'test-session-steps.py')
NEW = '33333333-3333-4333-8333-333333333333'


def write(path, raw):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(raw)
    path.chmod(0o600)


def save(path, value):
    write(path, F.json_bytes(value))


def refresh(directory):
    raw = ''.join(A.digest(path.read_bytes()) + '  ' + path.relative_to(directory).as_posix() + '\n'
                  for path in sorted(directory.rglob('*')) if path.is_file() and path.name != 'SHA256SUMS').encode()
    write(directory / 'SHA256SUMS', raw)
    return A.digest(raw)


def execution(directory, label, script, out, err=b'', status=0):
    child = directory / label
    child.mkdir(mode=0o700)
    write(child / 'command.sh', script)
    write(child / 'stdout.txt', out)
    write(child / 'stderr.txt', err)
    proc = {'exit_status': status, 'reason': None, 'stdin_complete': True,
            'stdout_bytes': len(out), 'stderr_bytes': len(err), 'elapsed_seconds': 0.1}
    save(child / 'process.json', proc)
    return proc


def make_archive(root, *, candidate_override=None, member_overrides=None):
    root.mkdir(mode=0o700)
    ident = '00000000-0000-0000-0000-000000000003'
    attempt = root / 'attempts' / ident
    attempt.mkdir(mode=0o700, parents=True)
    sessions = root / 'sessions' / ident
    sessions.mkdir(mode=0o700, parents=True)
    members = {name: {'mode': '0o100755', 'size': 32, 'sha256': C.sha(name.encode())} for name in C.MEMBERS.values()}
    members['etc/gemini-us.bkeymap']['sha256'] = C.MAP_SHA
    members['bin/reboot']['sha256'] = F.S['REBOOT_SHA']
    candidate = {'schema': 1, 'experiment': 'a53-authenticated-baseline', 'secret_bearing': True,
                 'members': members, 'known_hosts_sha256': 'f' * 64,
                 'files': {'boot.img': 'a' * 64, 'boot2-padded.img': 'b' * 64, 'kernel.config': 'c' * 64}}
    if candidate_override is not None:
        candidate = copy.deepcopy(candidate_override)
    if member_overrides is not None:
        candidate['members'].update(copy.deepcopy(member_overrides))
    candidate_raw = F.json_bytes(candidate)
    receipt = {'experiment': 'a53-authenticated-baseline', 'target_logical_name': 'boot2', 'boot2_device_guard': 'passed',
               'boot2_device_guard_sha256': '0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf',
               'fresh_predecessor_backup': 'no', 'candidate_sha256': candidate['files']['boot2-padded.img'],
               'candidate_manifest_sha256': C.sha(candidate_raw), 'readback_sha256': candidate['files']['boot2-padded.img'],
               'temporary_readback_removed': 'yes', 'shutdown': 'requested-after-evidence-flush',
               'post_shutdown_reachability': 'unreachable', 'reboot': 'no', 'next_action': 'owner-physically-selects-boot2',
               'result': 'skipped-already-matching', 'target': '/dev/mmcblk0p30', 'root': '/dev/mmcblk0p29',
               'target_major_minor': '179:30', 'root_major_minor': '179:29', 'predecessor_sha256': candidate['files']['boot2-padded.img'],
               'boot_id': CF.RECOVERY, 'power': '1|90|Good|0', 'poweroff_ssh_rc': '0'}
    deployment = ''.join(key + '=' + value + '\n' for key, value in receipt.items()).encode()
    admission = {'schema': 1, 'experiment': 'a53-authenticated-baseline', 'action': 'first-baseline-observation',
                 'admission_id': ident, 'candidate_sha256': candidate['files']['boot.img'],
                 'candidate_manifest_sha256': C.sha(candidate_raw), 'deployment_receipt_sha256': C.sha(deployment),
                 'collector_sha256': C.sha((A.REPO / A.BASELINE / 'collect-baseline.py').read_bytes()),
                 'custodian_role': 'Fixture custodian', 'custody_handoff_sha256': '1' * 64,
                 'custody_exclusive': True, 'physical_selection_confirmed': True,
                 'no_other_device_operations': True, 'observation_budget': 1}
    prepared = {'candidate': candidate, 'candidate_raw': candidate_raw, 'admission': admission,
                'admission_raw': F.json_bytes(admission), 'deployment_raw': deployment, 'recovery_id': CF.RECOVERY}
    script = C.remote_script(prepared)
    out = CF.good_capture(prepared)
    proc = {'exit_status': 0, 'reason': None, 'stdin_complete': True,
            'stdout_bytes': len(out), 'stderr_bytes': 0, 'elapsed_seconds': 0.1}
    baseline = C.classify_capture(prepared, out, b'', proc)
    base = {'candidate_sha256': admission['candidate_sha256'], 'remote_script_sha256': C.sha(script),
            'outer_timeout_seconds': C.TOTAL_SECONDS, 'stdout_limit_bytes': C.STDOUT_LIMIT, 'stderr_limit_bytes': C.STDERR_LIMIT}
    claim = {**base, 'budget': 'consumed', 'ssh_attempts_max': 1, 'admission_id': ident,
             'admission_sha256': C.sha(prepared['admission_raw']), 'deployment_receipt_sha256': C.sha(deployment),
             'candidate_manifest_sha256': C.sha(candidate_raw),
             'deployment_parser_sha256': C.sha((A.REPO / A.BASELINE / 'deployment_receipt.py').read_bytes()),
             'historical_sources': {str(p.relative_to(C.REPO)): d for p, d in C.SOURCE_PINS.items()}}
    for name, raw in (('admission.json', prepared['admission_raw']), ('candidate.json', candidate_raw),
                      ('deployment-summary.txt', deployment), ('stdout.txt', out), ('stderr.txt', b''),
                      ('remote-observe.sh', script), ('claim.json', F.json_bytes(claim)),
                      ('result.json', F.json_bytes({**base, **baseline, 'process': proc}))):
        write(attempt / name, raw)
    baseline_pin = refresh(attempt)
    context = {'attempt': attempt, 'prepared': prepared, 'baseline': baseline, 'manifest': (attempt / 'SHA256SUMS').read_bytes()}
    pins, proof = {}, {}
    for action in F.STEPS:
        confirming = action == 'confirm-recovery'
        directory = sessions / action
        directory.mkdir(mode=0o700)
        value = {'schema': 1, 'experiment': 'a53-authenticated-baseline', 'action': action,
                 'baseline_admission_id': ident, 'baseline_manifest_sha256': baseline_pin,
                 'candidate_manifest_sha256': C.sha(candidate_raw),
                 'finish_source_sha256': C.sha((A.REPO / A.BASELINE / 'finish-baseline.py').read_bytes()),
                 'steps_source_sha256': C.sha((A.REPO / A.BASELINE / 'session_steps.py').read_bytes()),
                 'custodian_role': 'Fixture custodian', 'custody_handoff_sha256': '1' * 64,
                 'custody_exclusive': True, 'no_other_device_operations': True, 'action_budgets': F.STEPS[action],
                 'owner_console_accepted': confirming, 'physical_recovery_confirmed': confirming,
                 'known_good_known_hosts_sha256': '9' * 64 if confirming else None,
                 'auth_checks_manifest_sha256': pins.get('auth-checks') if confirming else None,
                 'log_export_manifest_sha256': pins.get('preserve-log') if action in ('request-recovery', 'confirm-recovery') else None,
                 'native_request_manifest_sha256': pins.get('request-recovery') if confirming else None,
                 'recovery_mode': 'ordinary' if action == 'request-recovery' else None,
                 'emergency_reason': None, 'acknowledge_unique_ram_loss': None}
        child_context = {**context, 'admission': value, 'admission_raw': F.json_bytes(value)}
        save(directory / 'admission.json', value)
        save(directory / 'claim.json', F.phase_claim(child_context))
        boot = baseline['boot_id']
        if action == 'auth-checks':
            probe = F.S['probe_script'](candidate, boot)
            execution(directory, 'rejected-key', probe, b'', b'Permission denied (publickey)', 255)
            execution(directory, 'wrong-host', probe, b'', b'Host key verification failed', 255)
            execution(directory, 'positive-probe', probe, ('authenticated_boot_id=' + boot + '\n').encode())
            result = F.recheck_auth(directory, boot)
        elif action == 'preserve-log':
            raw = SF.frame()
            proc = execution(directory, 'log-export', F.S['seal_script'](candidate, boot), raw)
            parsed = F.S['parse_log_export'](raw, b'', proc)
            for name in F.EXPORT_FILES:
                write(directory / name, parsed['files'].get(name, b''))
            result = F.recheck_export(directory, boot)
        elif action == 'request-recovery':
            raw = (f'__A53_NATIVE_RECOVERY_BEGIN__\nboot_id={boot}\nreboot_sha256={F.S["REBOOT_SHA"]}\n'
                   'request_count=1\npartition_access=none\nsync_requested=no\n__A53_NATIVE_RECOVERY_END__\n').encode()
            proc = execution(directory, 'native-reboot', F.S['recovery_script'](candidate, boot), raw, b'Connection closed\n', 255)
            result = F.S['parse_recovery_request'](raw, proc, boot)
            child_context['preservation_proof'] = proof['preserve-log']
            result.update(F.recovery_context(child_context))
        else:
            raw = f'kernel=3.18.41+\narchitecture=aarch64\nboot_id={NEW}\n'.encode()
            proc = execution(directory, 'known-good-probe', F.S['GEMIAN_PROBE'], raw)
            result = F.S['parse_gemian'](raw, b'', proc, CF.RECOVERY, boot)
            result.update(prior_proof=copy.deepcopy(proof), baseline_classification='first-authenticated-baseline-and-recovery-pass')
        save(directory / 'result.json', result)
        pins[action] = refresh(directory)
        if action in F.PRIOR_FIELDS:
            item = {'classification': 'verified', 'manifest_sha256': pins[action]}
            if action == 'preserve-log':
                item.update(preservation_complete=True, complete_log=True)
            if action == 'request-recovery':
                item['recovery_mode'] = 'ordinary'
            proof[action] = item
    bindings = {'admission_id': ident, 'candidate_sha256': admission['candidate_sha256'],
                'candidate_manifest_sha256': C.sha(candidate_raw), 'baseline_manifest_sha256': baseline_pin,
                'confirmation_manifest_sha256': pins['confirm-recovery']}
    return bindings, context, sessions


class AggregateTests(unittest.TestCase):
    def setUp(self):
        work = A.REPO / 'artifacts/a53-authenticated/development/baseline-proof/work'
        work.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='aggregate-fixture-', dir=work)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'evidence'
        self.bindings, self.context, self.sessions = make_archive(self.root)
        self.attempt = self.context['attempt']

    def verify(self):
        return A.verify(self.root, self.bindings)

    def rebind_phase(self, phase):
        directory = self.sessions / phase
        pin = refresh(directory)
        if phase == 'confirm-recovery':
            self.bindings['confirmation_manifest_sha256'] = pin
            return
        confirmation = self.sessions / 'confirm-recovery'
        value = A.load(confirmation / 'admission.json')
        value[F.PRIOR_FIELDS[phase]] = pin
        save(confirmation / 'admission.json', value)
        save(confirmation / 'claim.json', F.phase_claim({**self.context, 'admission': value, 'admission_raw': F.json_bytes(value)}))
        result = A.load(confirmation / 'result.json')
        result['prior_proof'][phase]['manifest_sha256'] = pin
        save(confirmation / 'result.json', result)
        self.bindings['confirmation_manifest_sha256'] = refresh(confirmation)

    def test_complete_archive_reparsed_without_credentials_or_processes(self):
        real_open, real_builtin_open, real_io_open = os.open, builtins.open, io.open
        def allowed_path(path):
            if isinstance(path, (str, bytes, os.PathLike)):
                text = os.fsdecode(path)
                if ('/credentials/' in text or '/candidates/' in text or
                        Path(text).name in {'boot.img', 'boot2-padded.img', 'admin', 'known_hosts', 'authorized_keys'}):
                    raise AssertionError('credential or image access forbidden')
        def guarded_open(path, flags, *args, **kwargs):
            allowed_path(path)
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                raise AssertionError('write forbidden')
            return real_open(path, flags, *args, **kwargs)
        def stream_open(opener, path, mode='r', *args, **kwargs):
            allowed_path(path)
            if any(value in mode for value in 'wax+'):
                raise AssertionError('stream write forbidden')
            return opener(path, mode, *args, **kwargs)
        with patch('os.open', side_effect=guarded_open), \
             patch('builtins.open', side_effect=lambda *a, **k: stream_open(real_builtin_open, *a, **k)), \
             patch('io.open', side_effect=lambda *a, **k: stream_open(real_io_open, *a, **k)), \
             patch('socket.socket', side_effect=AssertionError('network forbidden')), \
             patch('subprocess.Popen', side_effect=AssertionError('process forbidden')), \
             patch('subprocess.run', side_effect=AssertionError('process forbidden')):
            result = self.verify()
        self.assertEqual(result['classification'], 'verified-first-authenticated-baseline-and-recovery')
        self.assertEqual(result['recovered_boot_id'], NEW)
        self.assertFalse(result['dependent_admission'])
        self.assertEqual(result['dependency_scope'], 'one-first-baseline-plus-recovery')
        self.assertEqual(result['baseline_admission_sha256'], A.digest(self.context['prepared']['admission_raw']))
        self.assertEqual(result['deployment_receipt_sha256'], A.digest(self.context['prepared']['deployment_raw']))
        self.assertEqual(result['original_known_good_boot_id'], self.context['prepared']['recovery_id'])
        self.assertNotIn('keyboard_admission', result)

    def test_complete_source_closure_refuses_changes_before_imports(self):
        self.assertEqual(len(A.SOURCE_PINS), 7)
        self.assertEqual({Path(name).name for name in A.SOURCE_PINS},
                         {'collect-baseline.py', 'finish-baseline.py', 'session_steps.py', 'deployment_receipt.py',
                          'remote_observe.sh', 'classify_observation.py', 'v4_deployment_receipt.py'})
        real_read = A.safe_read
        for name in A.SOURCE_PINS:
            with self.subTest(name=name):
                def changed_read(path, *args, **kwargs):
                    data = real_read(path, *args, **kwargs)
                    return data + b'\n# changed source\n' if Path(path) == A.REPO / name else data
                with patch.object(A, 'safe_read', side_effect=changed_read), \
                     patch.object(A, 'module', side_effect=AssertionError('source import before closure verification')):
                    with self.assertRaisesRegex(ValueError, 'changed-source:'):
                        self.verify()

    def test_candidate_and_manifest_pins_are_external(self):
        for key in ('candidate_sha256', 'candidate_manifest_sha256', 'baseline_manifest_sha256', 'confirmation_manifest_sha256'):
            with self.subTest(key=key):
                bindings = {**self.bindings, key: '8' * 64}
                with self.assertRaises(ValueError):
                    A.verify(self.root, bindings)

    def test_returned_result_hashes_use_the_validated_snapshot(self):
        for relative, key in (('attempt', 'baseline_first_boot_result_sha256'),
                              ('confirmation', 'baseline_recovery_result_sha256')):
            with self.subTest(relative=relative):
                path = (self.attempt if relative == 'attempt' else self.sessions / 'confirm-recovery') / 'result.json'
                original = path.read_bytes()
                calls = []
                original_sources = A.sources
                def replace_after_final_checks():
                    value = original_sources()
                    calls.append(True)
                    if len(calls) == 2:
                        save(path, {'classification': 'unverified-replacement'})
                    return value
                with patch.object(A, 'sources', side_effect=replace_after_final_checks):
                    result = self.verify()
                self.assertEqual(result[key], A.digest(original))
                self.assertNotEqual(result[key], A.digest(path.read_bytes()))
                write(path, original)

    def test_snapshot_hardlink_race_refuses_on_bytes_descriptor(self):
        real_tools = A.tools
        outside = self.root.parent / 'outside-hardlink'
        for location in ('attempt', 'auth-checks', 'confirm-recovery'):
            with self.subTest(location=location):
                directory = self.attempt if location == 'attempt' else self.sessions / location
                def raced_tools():
                    collector, finish, receipt = real_tools()
                    original = finish.verified_snapshot
                    def snapshot(path, manifest):
                        if path == directory and not outside.exists():
                            os.link(directory / 'result.json', outside)
                        return original(path, manifest)
                    finish.verified_snapshot = snapshot
                    return collector, finish, receipt
                with patch.object(A, 'tools', side_effect=raced_tools):
                    with self.assertRaisesRegex(ValueError, 'archive-file-permissions-or-links'):
                        self.verify()
                self.assertTrue(outside.exists(), 'race hook was not reached')
                outside.unlink()

    def test_prior_parsers_cannot_reopen_live_evidence(self):
        real_tools = A.tools
        calls = []
        def snapshot_only_tools():
            collector, finish, receipt = real_tools()
            for name in ('verify_phase_commands', 'recheck_auth', 'recheck_export'):
                original = getattr(finish, name)
                def wrapped(*args, _name=name, _original=original, snapshot=None):
                    self.assertIsNotNone(snapshot, 'verified snapshot not passed to ' + _name)
                    calls.append(_name)
                    with patch.object(finish, 'regular', side_effect=AssertionError('live evidence reopen forbidden')):
                        return _original(*args, snapshot=snapshot)
                setattr(finish, name, wrapped)
            return collector, finish, receipt
        with patch.object(A, 'tools', side_effect=snapshot_only_tools):
            result = self.verify()
        self.assertEqual(result['classification'], 'verified-first-authenticated-baseline-and-recovery')
        self.assertEqual(calls.count('verify_phase_commands'), 3)
        self.assertEqual(calls.count('recheck_auth'), 1)
        self.assertEqual(calls.count('recheck_export'), 1)

    def test_stored_original_pass_cannot_mask_raw_failure(self):
        path = self.attempt / 'stdout.txt'
        write(path, path.read_bytes().replace(b'cpu_online=0-7', b'cpu_online=0-9'))
        self.bindings['baseline_manifest_sha256'] = refresh(self.attempt)
        with self.assertRaisesRegex(ValueError, 'observation-not-independent-pass'):
            self.verify()

    def test_original_claim_and_admission_are_rechecked(self):
        for file, key, value in (('claim.json', 'ssh_attempts_max', 2), ('admission.json', 'custody_exclusive', False)):
            path = self.attempt / file
            original = path.read_bytes()
            data = json.loads(original)
            data[key] = value
            save(path, data)
            self.bindings['baseline_manifest_sha256'] = refresh(self.attempt)
            with self.assertRaises(ValueError):
                self.verify()
            write(path, original)
            self.bindings['baseline_manifest_sha256'] = refresh(self.attempt)

    def test_missing_phase_extra_session_and_extra_phase_member(self):
        extra = self.sessions / 'unreviewed-extra-session'
        extra.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError, 'session-inventory'):
            self.verify()
        extra.rmdir()
        path = self.sessions / 'auth-checks' / 'unreviewed'
        write(path, b'extra')
        self.rebind_phase('auth-checks')
        with self.assertRaises(ValueError):
            self.verify()

    def test_prior_source_budget_and_custody_mutations(self):
        path = self.sessions / 'auth-checks/admission.json'
        original = path.read_bytes()
        for key, value in (('finish_source_sha256', '8' * 64), ('action_budgets', {'rejected_key': 2}),
                           ('custody_exclusive', False), ('candidate_manifest_sha256', '8' * 64),
                           ('action', 'confirm-recovery')):
            with self.subTest(key=key):
                data = json.loads(original)
                data[key] = value
                save(path, data)
                self.rebind_phase('auth-checks')
                with self.assertRaises(ValueError):
                    self.verify()
        write(path, original)

    def test_negative_auth_transport_failure_not_refusal_proof(self):
        child = self.sessions / 'auth-checks/rejected-key'
        write(child / 'stderr.txt', b'Network is unreachable')
        proc = A.load(child / 'process.json')
        proc['stderr_bytes'] = len((child / 'stderr.txt').read_bytes())
        save(child / 'process.json', proc)
        self.rebind_phase('auth-checks')
        with self.assertRaisesRegex(ValueError, 'negative auth evidence'):
            self.verify()

    def test_changed_fixed_command_refuses(self):
        write(self.sessions / 'auth-checks/positive-probe/command.sh', b'exit 0\n')
        self.rebind_phase('auth-checks')
        with self.assertRaisesRegex(ValueError, 'fixed command changed'):
            self.verify()

    def test_process_boolean_count_and_deadline_refusal(self):
        path = self.sessions / 'auth-checks/positive-probe/process.json'
        original = path.read_bytes()
        for key, value in (('exit_status', False), ('stdout_bytes', True), ('elapsed_seconds', 17), ('elapsed_seconds', float('nan'))):
            with self.subTest(key=key):
                proc = json.loads(original)
                proc[key] = value
                save(path, proc)
                self.rebind_phase('auth-checks')
                with self.assertRaises(ValueError):
                    self.verify()
        write(path, original)

    def test_stored_phase_result_not_accepted_on_its_own(self):
        path = self.sessions / 'auth-checks/result.json'
        value = A.load(path)
        value['boot_id'] = NEW
        save(path, value)
        self.rebind_phase('auth-checks')
        with self.assertRaisesRegex(ValueError, 'prior-result-not-reparsed'):
            self.verify()

    def test_late_terminal_log_is_not_baseline_acceptance(self):
        directory = self.sessions / 'preserve-log'
        raw = SF.frame(terminal_before_export='no')
        child = directory / 'log-export'
        write(child / 'stdout.txt', raw)
        proc = A.load(child / 'process.json')
        proc['stdout_bytes'] = len(raw)
        save(child / 'process.json', proc)
        save(directory / 'result.json', F.recheck_export(directory, self.context['baseline']['boot_id']))
        self.rebind_phase('preserve-log')
        with self.assertRaisesRegex(ValueError, 'incomplete-baseline-log'):
            self.verify()

    def test_retained_log_differs_from_export_refusal(self):
        write(self.sessions / 'preserve-log/kmsg.log', b'replaced evidence\n')
        self.rebind_phase('preserve-log')
        with self.assertRaisesRegex(ValueError, 'raw evidence differs'):
            self.verify()

    def test_emergency_chain_never_satisfies_dependency(self):
        path = self.sessions / 'request-recovery/admission.json'
        value = A.load(path)
        value.update(recovery_mode='emergency', emergency_reason='immediate-safety-stop', acknowledge_unique_ram_loss=True)
        save(path, value)
        self.rebind_phase('request-recovery')
        with self.assertRaisesRegex(ValueError, 'emergency-chain'):
            self.verify()

    def test_recovery_request_interruption_and_wrong_id(self):
        path = self.sessions / 'request-recovery/native-reboot/process.json'
        value = A.load(path)
        value['reason'] = 'interrupted'
        save(path, value)
        self.rebind_phase('request-recovery')
        with self.assertRaises(ValueError):
            self.verify()

    def test_confirm_requires_changed_boot_exact_gemian_and_no_noise(self):
        path = self.sessions / 'confirm-recovery/known-good-probe/stdout.txt'
        original = path.read_bytes()
        for raw in (original.replace(NEW.encode(), CF.RECOVERY.encode()),
                    original.replace(NEW.encode(), CF.BOOT.encode()), original.replace(b'3.18.41+', b'7.1.3'),
                    original + b'extra=1\n'):
            write(path, raw)
            procpath = path.with_name('process.json')
            proc = A.load(procpath)
            proc['stdout_bytes'] = len(raw)
            save(procpath, proc)
            self.rebind_phase('confirm-recovery')
            with self.assertRaises(ValueError):
                self.verify()

    def test_confirm_stored_pass_owner_and_command_mutations(self):
        directory = self.sessions / 'confirm-recovery'
        for name, key, value in (('result.json', 'boot_id', CF.BOOT),
                                  ('admission.json', 'owner_console_accepted', False),
                                  ('admission.json', 'physical_recovery_confirmed', False),
                                  ('admission.json', 'known_good_known_hosts_sha256', None)):
            path = directory / name
            original = path.read_bytes()
            data = json.loads(original)
            data[key] = value
            save(path, data)
            self.rebind_phase('confirm-recovery')
            with self.assertRaises(ValueError):
                self.verify()
            write(path, original)
        write(directory / 'known-good-probe/command.sh', b'exit 0\n')
        self.rebind_phase('confirm-recovery')
        with self.assertRaisesRegex(ValueError, 'gemian-probe'):
            self.verify()

    def test_archive_duplicate_json_symlink_and_hardlink_refusal(self):
        path = self.sessions / 'confirm-recovery/result.json'
        original = path.read_bytes()
        write(path, b'{"classification":"pass","classification":"pass"}\n')
        self.rebind_phase('confirm-recovery')
        with self.assertRaises(ValueError):
            self.verify()
        write(path, original)
        self.rebind_phase('confirm-recovery')
        link = self.sessions / 'outside-hardlink'
        os.link(path, link)
        with self.assertRaises(ValueError):
            self.verify()
        link.unlink()
        path.unlink()
        path.symlink_to(self.sessions / 'auth-checks/result.json')
        with self.assertRaises(ValueError):
            self.verify()


if __name__ == '__main__':
    unittest.main(verbosity=2)
