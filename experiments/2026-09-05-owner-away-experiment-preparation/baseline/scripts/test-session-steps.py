#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent sealed-log/recovery parser and offline session refusal fixtures."""
import base64
import hashlib
import json
import os
from pathlib import Path
import runpy
import stat
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
S = runpy.run_path(str(HERE / 'session_steps.py'))
F = runpy.run_path(str(HERE / 'finish-baseline.py'))
COLLECT_FIXTURE = runpy.run_path(str(HERE / 'test-collect-baseline.py'))
BOOT = '11111111-1111-4111-8111-111111111111'
OLD = '22222222-2222-4222-8222-222222222222'
NEW = '33333333-3333-4333-8333-333333333333'
PROCESS = {'reason': None, 'exit_status': 0, 'stdin_complete': True}
CANDIDATE = {'members': {name: {'sha256': S['REBOOT_SHA'] if name == 'bin/reboot' else 'a' * 64}
                        for name in ('init', 'bin/busybox', 'bin/reboot', 'bin/kmsg-capture', 'bin/kmsg-seal')}}
LOG = b'6,0,100,-;early message\n SUBSYSTEM=platform\n6,1,200,c;next message\n'


def status(log=LOG, **overrides):
    fields = {'logger_exit': '0', 'schema': 'gemini-kmsg-v1', 'sealed': 'yes', 'result': 'pass',
              'reason': 'sealed-on-sigterm', 'first_seq': '0', 'last_seq': '1', 'records': '2',
              'bytes': str(len(log)), 'elapsed_ms': '1250', 'byte_limit': '2097152', 'deadline_ms': '600000'}
    fields.update(overrides)
    return ''.join(k + '=' + str(v) + '\n' for k, v in fields.items()).encode()


def frame(log=LOG, raw_status=None, *, stop='signalled', terminal_before_export='yes', overrides=None):
    """Independent wire-format fixture, including per-file failures/prefixes."""
    overrides = overrides or {}
    raw = (f'__A53_LOG_EXPORT_BEGIN__\nschema=gemini-log-export-v2\nstop={stop}\n'
           f'signal_attempts={0 if stop == "preexisting-terminal" else 1}\n'
           f'signal_status={"none" if stop == "preexisting-terminal" else "1" if stop == "signal-failed" else "0"}\n'
           f'terminal_before_export={terminal_before_export}\n'
           '__A53_LOG_EXPORT_FILES__\n').encode()
    data = {'kmsg.log': log, 'kmsg.status': (raw_status or status(log)).removeprefix(b'logger_exit=0\n'),
            'kmsg.status.partial': None, 'kmsg-exit': b'0\n'}
    for name, ceiling in [('kmsg.log', 2097152), ('kmsg.status', 8192), ('kmsg.status.partial', 8192), ('kmsg-exit', 8192)]:
        item = data[name]
        spec = {'data': item, 'state': 'missing' if item is None else 'regular',
                'size_before': '-' if item is None else str(len(item)),
                'size_after': '-' if item is None else str(len(item)),
                'read_status': 'none' if item is None else '0', 'encode_status': 'none' if item is None else '0',
                'stable': 'not-applicable' if item is None else 'yes', 'truncated': 'no'}
        spec.update(overrides.get(name, {}))
        raw += (f'__A53_LOG_FILE_BEGIN__\nname={name}\nstate={spec["state"]}\nsize_before={spec["size_before"]}\n'
                f'limit={ceiling}\n__A53_LOG_FILE_BASE64__\n').encode()
        raw += base64.encodebytes(spec['data'] or b'') + b'\n__A53_LOG_FILE_META__\n'
        raw += ''.join(key + '=' + str(spec[key]) + '\n' for key in
                       ('size_after', 'read_status', 'encode_status', 'stable', 'truncated')).encode()
        raw += b'__A53_LOG_FILE_END__\n'
    return raw + b'__A53_LOG_EXPORT_END__\n'


class LogTests(unittest.TestCase):
    def test_complete_contiguous_log_with_metadata(self):
        log, raw, result = S['parse_seal'](frame(), b'', PROCESS)
        self.assertEqual(log, LOG)
        self.assertEqual(raw, status())
        self.assertEqual(result['classification'], 'complete-log-through-seal')
        self.assertEqual(result['records'], 2)

    def test_failed_status_fields(self):
        for name, value in [('logger_exit', '1'), ('sealed', 'no'), ('result', 'failed'),
                            ('reason', 'deadline-expired'), ('first_seq', '1'), ('last_seq', '2'),
                            ('records', '1'), ('bytes', '1'), ('elapsed_ms', '600000'),
                            ('byte_limit', '9999'), ('deadline_ms', '9999')]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                S['classify_log'](LOG, status(**{name: value}))

    def test_duplicate_unknown_missing_fields(self):
        for raw in (status() + b'bytes=1\n', status() + b'extra=yes\n', status().replace(b'sealed=yes\n', b'')):
            with self.assertRaises(ValueError):
                S['classify_log'](LOG, raw)

    def test_sequence_record_refusals(self):
        for log in (LOG.replace(b'6,0,', b'6,1,'), LOG.replace(b'6,1,', b'6,3,'),
                    LOG.replace(b'6,1,', b'6,0,'), b' orphan\n' + LOG, LOG[:-1], LOG + b'\0',
                    LOG.replace(b'6,0,', b'9999,0,'), LOG.replace(b',100,-;', b',100,,;')):
            with self.assertRaises(ValueError):
                S['classify_log'](log, status(log))

    def test_empty_truncated_or_overcap_log(self):
        for log in (b'', b'6,0,100,-;no newline', b'x' * (S['LIMIT'] + 1)):
            with self.assertRaises(ValueError):
                S['classify_log'](log, status(log))

    def test_transport_does_not_accept_ostensible_pass(self):
        for changes in ({'exit_status': 255}, {'reason': 'outer-timeout'}, {'stdin_complete': False}):
            with self.assertRaises(ValueError):
                S['parse_seal'](frame(), b'', {**PROCESS, **changes})
        with self.assertRaises(ValueError):
            S['parse_seal'](frame(), b'error', PROCESS)

    def test_log_frame_extra_missing_duplicate_invalid_base64(self):
        for raw in (b'noise' + frame(), frame() + b'noise', frame().replace(b'__A53_LOG_EXPORT_END__\n', b''),
                    frame().replace(b'__A53_LOG_FILE_BASE64__\n', b'__A53_LOG_FILE_BASE64__\n__A53_LOG_FILE_BASE64__\n'),
                    frame().replace(base64.encodebytes(LOG), b'!\n')):
            with self.assertRaises(ValueError):
                S['parse_seal'](raw, b'', PROCESS)

    def test_export_schema_refuses_forged_headers_file_order_sizes_and_metadata(self):
        original = frame()
        changes = [
            (b'stop=signalled\n', b'stop=signalled\nstop=signalled\n'),
            (b'stop=signalled\n', b'stop=signalled\nextra=1\n'),
            (b'stop=signalled\n', b'stop=preexisting-terminal\n'),
            (b'signal_attempts=1\n', b'signal_attempts=0\n'),
            (b'signal_status=0\n', b'signal_status=1\n'),
            (b'terminal_before_export=yes\n', b'terminal_before_export=unknown\n'),
            (b'terminal_before_export=yes\n', b'terminal_before_export=yes\nterminal_before_export=yes\n'),
            (b'name=kmsg.log\n', b'name=kmsg-exit\n'),
            (b'name=kmsg.log\n', b'name=kmsg.log\nname=kmsg.log\n'),
            (b'name=kmsg.log\n', b'name=kmsg.log\nextra=1\n'),
            (b'limit=2097152\n', b'limit=2097153\n'),
            (b'state=regular\n', b'state=arbitrary\n'),
            (b'size_before=' + str(len(LOG)).encode() + b'\n', b'size_before=1\n'),
            (b'size_after=' + str(len(LOG)).encode() + b'\n', b'size_after=1\n'),
            (b'read_status=0\n', b'read_status=0\nread_status=0\n'),
            (b'read_status=0\n', b'read_status=0\nextra=1\n'),
            (b'encode_status=0\n', b'encode_status=256\n'),
            (b'truncated=no\n', b'truncated=yes\n'),
            (b'stable=yes\n', b'stable=not-applicable\n'),
            (base64.encodebytes(LOG), base64.encodebytes(LOG).replace(b'\n', b'\r\n')),
            (b'__A53_LOG_EXPORT_END__\n', b''),
        ]
        for before, after in changes:
            with self.subTest(before=before, after=after):
                parsed = S['parse_log_export'](original.replace(before, after, 1), b'', PROCESS)
                self.assertEqual(parsed['result']['classification'], 'log-export-inconclusive')
                self.assertFalse(parsed['result']['preservation_complete'])
                self.assertFalse(parsed['result']['export_complete'])

    def test_transport_failure_retains_complete_earlier_file_blocks(self):
        raw = frame().split(b'name=kmsg.status\n', 1)[0]
        parsed = S['parse_log_export'](raw, b'transport stopped\n', {**PROCESS, 'reason': 'interrupted'})
        self.assertEqual(parsed['files'], {'kmsg.log': LOG})
        self.assertEqual(parsed['result']['files']['kmsg.log']['sha256'], hashlib.sha256(LOG).hexdigest())
        self.assertFalse(parsed['result']['transport_complete'])
        self.assertFalse(parsed['result']['export_complete'])
        self.assertFalse(parsed['result']['preservation_complete'])

    def test_native_request_is_not_recovery(self):
        raw = (f'__A53_NATIVE_RECOVERY_BEGIN__\nboot_id={BOOT}\nreboot_sha256={S["REBOOT_SHA"]}\n'
               'request_count=1\npartition_access=none\nsync_requested=no\n__A53_NATIVE_RECOVERY_END__\n').encode()
        result = S['parse_recovery_request'](raw, {**PROCESS, 'exit_status': 255}, BOOT)
        self.assertFalse(result['recovery_confirmed'])
        for changes in ({'exit_status': 0}, {'exit_status': 94}, {'reason': 'outer-timeout'}, {'stdin_complete': False}):
            with self.assertRaises(ValueError):
                S['parse_recovery_request'](raw, {**PROCESS, 'exit_status': 255, **changes}, BOOT)
        with self.assertRaises(ValueError):
            S['parse_recovery_request'](raw + b'extra\n', {**PROCESS, 'exit_status': 255}, BOOT)

    def test_known_good_requires_changed_id_exact_release(self):
        raw = f'kernel=3.18.41+\narchitecture=aarch64\nboot_id={NEW}\n'.encode()
        self.assertEqual(S['parse_gemian'](raw, b'', PROCESS, OLD, BOOT)['boot_id'], NEW)
        for data in (raw.replace(NEW.encode(), OLD.encode()), raw.replace(NEW.encode(), BOOT.encode()),
                     raw.replace(b'3.18.41+', b'7.1.3'), raw + b'extra=1\n'):
            with self.assertRaises(ValueError):
                S['parse_gemian'](data, b'', PROCESS, OLD, BOOT)

    def test_script_rejects_invalid_identity(self):
        for boot in ('', BOOT + ';id'):
            with self.assertRaises(ValueError):
                S['identity_script'](CANDIDATE, boot)
        candidate = {'members': {**CANDIDATE['members'], 'bin/reboot': {'sha256': '0' * 64}}}
        with self.assertRaises(ValueError):
            S['identity_script'](candidate, BOOT)


class HostTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix='a53-session-', dir='/tmp')
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name).resolve()
        self.root.chmod(0o700)
        self.context = {'admission': {'action': 'auth-checks'}}

    def test_default_dry_run_no_process_or_state(self):
        with patch('subprocess.Popen', side_effect=AssertionError('process forbidden')):
            self.assertEqual(F['perform'](self.context)['classification'], 'dry-run')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_step_inventory_is_bounded(self):
        self.assertEqual(F['STEPS'], {'auth-checks': {'rejected_key': 1, 'wrong_host': 1, 'positive_probe': 1},
                                     'preserve-log': {'log_export': 1},
                                     'request-recovery': {'native_reboot': 1}, 'confirm-recovery': {'known_good_probe': 1}})

    def test_phase_manifest_corruption_and_extra_member(self):
        path = self.root / 'phase'
        path.mkdir(mode=0o700)
        data = b'bounded fixture'
        (path / 'result.json').write_bytes(data)
        (path / 'result.json').chmod(0o600)
        manifest = (hashlib.sha256(data).hexdigest() + '  result.json\n').encode()
        (path / 'SHA256SUMS').write_bytes(manifest)
        (path / 'SHA256SUMS').chmod(0o600)
        expected = hashlib.sha256(manifest).hexdigest()
        # A self-consistent checksum list is insufficient without the complete
        # admitted phase inventory.
        with self.assertRaises(ValueError):
            F['verify_phase'](path, expected, 'request-recovery')
        (path / 'extra').write_text('extra')
        with self.assertRaises(ValueError):
            F['verify_phase'](path, expected, 'request-recovery')
        (path / 'extra').unlink()
        (path / 'result.json').write_text('corrupt')
        with self.assertRaises(ValueError):
            F['verify_phase'](path, expected, 'request-recovery')

    def test_existing_step_refuses_before_process(self):
        context = {'admission': {'action': 'request-recovery'}, 'attempt': self.root / BOOT}
        state = self.root / 'artifacts/a53-authenticated/sessions' / BOOT / 'request-recovery'
        state.mkdir(parents=True, mode=0o700)
        for parent in state.parents:
            if parent == self.root.parent:
                break
            parent.chmod(0o700)
        globals_ = F['perform'].__globals__
        with patch.dict(globals_, REPO=self.root), patch('subprocess.Popen', side_effect=AssertionError('network forbidden')):
            with self.assertRaises(FileExistsError):
                F['perform'](context, execute=True)


class PriorPhaseTests(unittest.TestCase):
    """Use a real validated collector attempt and actual finish phase writers.

    The collector uses an inert local process. Finish transports are replaced
    at run_once; SSH is never executed. Disposable key generation stays local.
    """
    def setUp(self):
        old_umask = os.umask(0o077)
        self.addCleanup(os.umask, old_umask)
        self.work = tempfile.TemporaryDirectory(prefix='a53-prior-phase-', dir='/tmp')
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name).resolve()
        self.repo, admission_path, deployment_path = COLLECT_FIXTURE['make_fixture'](self.root)
        admission = json.loads(admission_path.read_bytes())
        candidate_dir = self.repo / 'artifacts/a53-authenticated/candidates' / ('candidate-' + admission['candidate_sha256'])
        candidate = json.loads((candidate_dir / 'candidate.json').read_bytes())
        candidate['members']['bin/reboot']['sha256'] = S['REBOOT_SHA']
        candidate_raw = F['json_bytes'](candidate)
        self.write(candidate_dir / 'candidate.json', candidate_raw)
        deployment = deployment_path.read_text()
        deployment = deployment.replace('candidate_manifest_sha256=' + admission['candidate_manifest_sha256'],
                                        'candidate_manifest_sha256=' + F['sha'](candidate_raw))
        self.write(deployment_path, deployment.encode())
        admission.update(candidate_manifest_sha256=F['sha'](candidate_raw), deployment_receipt_sha256=F['sha'](deployment.encode()))
        self.write(admission_path, F['json_bytes'](admission))
        collector = COLLECT_FIXTURE['C']
        self.prepared = collector.prepare(self.repo, admission_path, deployment_path)
        self.boot = COLLECT_FIXTURE['BOOT']
        fake = COLLECT_FIXTURE['fake_ssh'](self.root, COLLECT_FIXTURE['good_capture'](self.prepared))
        result = collector.collect(self.prepared, True, _ssh=fake, _timeout=3)
        self.assertEqual(result['classification'], 'baseline-observation-only-pass')
        self.attempt = self.repo / 'artifacts/a53-authenticated/attempts' / admission['admission_id']
        self.sessions = self.repo / 'artifacts/a53-authenticated/sessions' / self.attempt.name
        self.write(self.repo / 'artifacts/credentials/a53-recovery-known_hosts', b'192.168.1.50 ssh-ed25519 fixture\n')
        self.write(self.repo / 'artifacts/credentials/gemini_ed25519', b'inert-not-a-private-key\n')
        globals_ = F['prepare'].__globals__
        scope = patch.dict(globals_, REPO=self.repo)
        scope.start(); self.addCleanup(scope.stop)
        self.calls = []
        self.interrupted = None
        self.export_raw = frame()
        self.transport_overrides = {}
        transport = patch.dict(F['C'], run_once=self.fake_run)
        transport.start(); self.addCleanup(transport.stop)

    def write(self, path, data):
        COLLECT_FIXTURE['write'](path, data)

    def fake_run(self, command, script, child, timeout, **_limits):
        label = child.name
        self.calls.append(label)
        if label in ('rejected-key', 'wrong-host'):
            out = b''
            err = b'Permission denied (publickey)' if label == 'rejected-key' else b'Host key verification failed'
            code = 255
        elif label == 'positive-probe':
            out, err, code = ('authenticated_boot_id=' + self.boot + '\n').encode(), b'', 0
        elif label == 'log-export':
            out, err, code = self.export_raw, b'', 0
        elif label == 'native-reboot':
            out = (f'__A53_NATIVE_RECOVERY_BEGIN__\nboot_id={self.boot}\nreboot_sha256={S["REBOOT_SHA"]}\n'
                   'request_count=1\npartition_access=none\nsync_requested=no\n__A53_NATIVE_RECOVERY_END__\n').encode()
            err, code = b'Connection closed\n', 255
        elif label == 'known-good-probe':
            self.assertEqual(command[-2:], ['gemini@192.168.1.50', '/bin/sh -s'])
            self.assertEqual(script, S['GEMIAN_PROBE'])
            out, err, code = f'kernel=3.18.41+\narchitecture=aarch64\nboot_id={NEW}\n'.encode(), b'', 0
        else:
            raise AssertionError('unadmitted fixture transport label')
        self.write(child / 'stdout.txt', out)
        self.write(child / 'stderr.txt', err)
        return {'reason': 'interrupted' if label == self.interrupted else None, 'exit_status': code,
                'stdin_complete': True, 'stdout_bytes': len(out), 'stderr_bytes': len(err), 'elapsed_seconds': 0.1,
                **self.transport_overrides.get(label, {})}

    def admission(self, action, auth_pin=None, request_pin=None, export_pin=None, *,
                  recovery_mode=None, emergency_reason=None, acknowledge=None):
        confirming = action == 'confirm-recovery'
        value = {'schema': 1, 'experiment': 'a53-authenticated-baseline', 'action': action,
                 'baseline_admission_id': self.attempt.name,
                 'baseline_manifest_sha256': F['sha']((self.attempt / 'SHA256SUMS').read_bytes()),
                 'candidate_manifest_sha256': F['sha'](self.prepared['candidate_raw']),
                 'finish_source_sha256': F['sha']((HERE / 'finish-baseline.py').read_bytes()),
                 'steps_source_sha256': F['sha']((HERE / 'session_steps.py').read_bytes()),
                 'custodian_role': 'Fixture custodian', 'custody_handoff_sha256': '1' * 64,
                 'custody_exclusive': True, 'no_other_device_operations': True,
                 'action_budgets': F['STEPS'][action], 'owner_console_accepted': confirming,
                 'physical_recovery_confirmed': confirming,
                 'known_good_known_hosts_sha256': F['sha']((self.repo / 'artifacts/credentials/a53-recovery-known_hosts').read_bytes()) if confirming else None,
                 'auth_checks_manifest_sha256': auth_pin, 'native_request_manifest_sha256': request_pin,
                 'log_export_manifest_sha256': export_pin, 'recovery_mode': recovery_mode,
                 'emergency_reason': emergency_reason, 'acknowledge_unique_ram_loss': acknowledge}
        path = self.repo / 'artifacts/a53-authenticated/records' / (action + '.json')
        self.write(path, F['json_bytes'](value))
        return path

    def phase(self, action, **admission):
        if action == 'request-recovery' and not admission:
            # Explicit fixture admission after a separately executed export.
            export = self.sessions / 'preserve-log'
            if not export.exists():
                self.phase('preserve-log')
            admission = {'recovery_mode': 'ordinary', 'export_pin': self.refresh(export)}
        context = F['prepare'](self.attempt, self.admission(action, **admission))
        result = F['perform'](context, execute=True)
        return self.sessions / action, result

    def refresh(self, directory):
        raw = ''.join(F['sha'](path.read_bytes()) + '  ' + path.relative_to(directory).as_posix() + '\n'
                      for path in sorted(directory.rglob('*'))
                      if path.name != 'SHA256SUMS' and stat.S_ISREG(path.lstat().st_mode)).encode()
        self.write(directory / 'SHA256SUMS', raw)
        return F['sha'](raw)

    def confirmation(self, auth=None, request=None, export=None):
        if export is None and (self.sessions / 'preserve-log/SHA256SUMS').exists():
            export = F['sha']((self.sessions / 'preserve-log/SHA256SUMS').read_bytes())
        return F['prepare'](self.attempt, self.admission('confirm-recovery', auth, request, export))

    def test_complete_phases_prepare_dry_run_and_confirm(self):
        auth, first = self.phase('auth-checks')
        request, second = self.phase('request-recovery')
        self.assertEqual(first['classification'], 'authentication-checks-pass')
        self.assertEqual(second['classification'], 'native-recovery-requested')
        context = self.confirmation(self.refresh(auth), self.refresh(request))
        self.assertTrue(all(item['classification'] == 'verified' for item in context['prior_proof'].values()))
        count = len(self.calls)
        dry = F['perform'](context)
        self.assertTrue(dry['full_baseline_eligible'])
        self.assertEqual(len(self.calls), count)
        self.assertFalse((self.sessions / 'confirm-recovery').exists())
        result = F['perform'](context, execute=True)
        self.assertEqual(result['baseline_classification'], 'first-authenticated-baseline-and-recovery-pass')
        self.assertEqual(self.calls[count:], ['known-good-probe'])

    def test_missing_prior_proof_still_allows_only_recovery_confirmation(self):
        context = self.confirmation()
        self.assertEqual({item['classification'] for item in context['prior_proof'].values()}, {'missing'})
        self.assertFalse(F['perform'](context)['full_baseline_eligible'])
        result = F['perform'](context, execute=True)
        self.assertEqual(result['baseline_classification'], 'recovered-with-baseline-incomplete')
        self.assertEqual(self.calls, ['known-good-probe'])

    def test_interrupted_native_request_remains_observable_without_full_pass(self):
        auth, _ = self.phase('auth-checks')
        self.interrupted = 'native-reboot'
        request, result = self.phase('request-recovery')
        self.assertEqual(result['classification'], 'inconclusive')
        context = self.confirmation(self.refresh(auth), self.refresh(request))
        self.assertEqual(context['prior_proof']['request-recovery']['classification'], 'incomplete')
        count = len(self.calls)
        result = F['perform'](context, execute=True)
        self.assertEqual(result['baseline_classification'], 'recovered-with-baseline-incomplete')
        self.assertEqual(self.calls[count:], ['known-good-probe'])

    def test_prior_admission_source_candidate_baseline_and_budget_changes_refuse(self):
        directory, _ = self.phase('auth-checks')
        path = directory / 'admission.json'
        original = path.read_bytes()
        for field, value in (('schema', True), ('candidate_manifest_sha256', '0' * 64), ('finish_source_sha256', '0' * 64),
                             ('steps_source_sha256', '0' * 64), ('baseline_manifest_sha256', '0' * 64),
                             ('baseline_admission_id', OLD), ('action', 'confirm-recovery'),
                             ('action_budgets', {'rejected_key': 99})):
            with self.subTest(field=field):
                changed = json.loads(original)
                changed[field] = value
                self.write(path, F['json_bytes'](changed))
                context = self.confirmation(self.refresh(directory))
                self.assertEqual(context['prior_proof']['auth-checks']['classification'], 'incomplete')
        self.write(path, original)

    def test_claim_and_fixed_command_changes_refuse(self):
        for action in ('auth-checks', 'preserve-log', 'request-recovery'):
            directory, _ = self.phase(action)
            paths = [directory / 'claim.json', *(directory / label / 'command.sh' for label in F['PHASE_LABELS'][action])]
            for path in paths:
                with self.subTest(action=action, path=path.name):
                    original = path.read_bytes()
                    if path.name == 'claim.json':
                        changed = json.loads(original); changed['phase_admission_sha256'] = '0' * 64
                        self.write(path, F['json_bytes'](changed))
                    else:
                        self.write(path, original + b'printf injected\n')
                    pin = self.refresh(directory)
                    context = self.confirmation(pin if action == 'auth-checks' else None,
                                                pin if action == 'request-recovery' else None,
                                                pin if action == 'preserve-log' else None)
                    self.assertEqual(context['prior_proof'][action]['classification'], 'incomplete')
                    self.write(path, original)

    def test_complete_inventory_rejects_missing_files_extra_directories_and_links(self):
        directory, _ = self.phase('auth-checks')
        for relative in ('admission.json', 'claim.json', 'positive-probe/command.sh', 'positive-probe/process.json'):
            with self.subTest(missing=relative):
                path = directory / relative; original = path.read_bytes(); path.unlink()
                context = self.confirmation(self.refresh(directory))
                self.assertEqual(context['prior_proof']['auth-checks']['classification'], 'incomplete')
                self.write(path, original)
        for kind in ('directory', 'symlink', 'file', 'hardlink'):
            with self.subTest(extra=kind):
                extra = directory / 'unexpected'
                if kind == 'directory': extra.mkdir(mode=0o700)
                elif kind == 'symlink': extra.symlink_to(directory / 'positive-probe', target_is_directory=True)
                elif kind == 'hardlink': os.link(directory / 'result.json', extra)
                else: self.write(extra, b'extra')
                context = self.confirmation(self.refresh(directory))
                self.assertEqual(context['prior_proof']['auth-checks']['classification'], 'incomplete')
                if kind == 'directory': extra.rmdir()
                else: extra.unlink()

    def test_duplicate_manifest_and_json_fields_refuse(self):
        directory, _ = self.phase('request-recovery')
        self.refresh(directory)
        path = directory / 'SHA256SUMS'; original = path.read_bytes()
        self.write(path, original + original.splitlines(keepends=True)[0])
        context = self.confirmation(request=F['sha'](path.read_bytes()))
        self.assertEqual(context['prior_proof']['request-recovery']['classification'], 'incomplete')
        for relative, field, value in (('admission.json', 'action', 'request-recovery'), ('claim.json', 'budget', 'consumed')):
            path = directory / relative; original = path.read_bytes()
            self.write(path, original.rstrip()[:-1] + b', ' + json.dumps(field).encode() + b': ' + json.dumps(value).encode() + b'}\n')
            context = self.confirmation(request=self.refresh(directory))
            self.assertEqual(context['prior_proof']['request-recovery']['classification'], 'incomplete')
            self.write(path, original)

    def test_process_record_counts_and_types_refuse(self):
        directory, _ = self.phase('auth-checks')
        path = directory / 'positive-probe/process.json'; original = path.read_bytes()
        for field, value in (('stdout_bytes', 1), ('exit_status', False), ('elapsed_seconds', 50),
                             ('stdin_complete', False), ('extra', 'unexpected')):
            with self.subTest(field=field):
                changed = json.loads(original); changed[field] = value
                self.write(path, F['json_bytes'](changed))
                context = self.confirmation(auth=self.refresh(directory))
                self.assertEqual(context['prior_proof']['auth-checks']['classification'], 'incomplete')

    def test_claim_and_result_boolean_integer_substitution_refuses(self):
        directory, _ = self.phase('request-recovery')
        for relative in ('claim.json', 'result.json'):
            with self.subTest(relative=relative):
                path = directory / relative; original = path.read_bytes()
                value = json.loads(original)
                if relative == 'claim.json': value['action_budgets']['native_reboot'] = True
                else: value['request_count'] = True
                self.write(path, F['json_bytes'](value))
                context = self.confirmation(request=self.refresh(directory))
                self.assertEqual(context['prior_proof']['request-recovery']['classification'], 'incomplete')
                self.write(path, original)

    def test_evidence_changed_after_prepare_cannot_promote(self):
        auth, _ = self.phase('auth-checks'); request, _ = self.phase('request-recovery')
        context = self.confirmation(self.refresh(auth), self.refresh(request))
        self.write(auth / 'positive-probe/command.sh', b'changed after preparation\n')
        result = F['perform'](context, execute=True)
        self.assertEqual(result['baseline_classification'], 'recovered-with-baseline-incomplete')

    def test_repaired_evidence_cannot_upgrade_incomplete_preparation(self):
        auth, _ = self.phase('auth-checks'); request, _ = self.phase('request-recovery')
        auth_pin, request_pin = self.refresh(auth), self.refresh(request)
        path = auth / 'positive-probe/command.sh'; original = path.read_bytes()
        self.write(path, b'corrupt before preparation\n')
        context = self.confirmation(auth_pin, request_pin)
        self.assertEqual(context['prior_proof']['auth-checks']['classification'], 'incomplete')
        self.write(path, original)
        result = F['perform'](context, execute=True)
        self.assertEqual(result['prior_proof']['auth-checks']['classification'], 'verified')
        self.assertEqual(result['baseline_classification'], 'recovered-with-baseline-incomplete')

    def test_auth_timeout_stops_without_export_then_separate_preservation_is_available(self):
        self.transport_overrides['rejected-key'] = {'reason': 'outer-timeout'}
        auth, result = self.phase('auth-checks')
        self.assertEqual(result['classification'], 'inconclusive')
        self.assertEqual(self.calls, ['rejected-key'])
        self.assertEqual((auth / 'rejected-key/stderr.txt').read_bytes(), b'Permission denied (publickey)')
        export, result = self.phase('preserve-log')
        self.assertEqual(self.calls, ['rejected-key', 'log-export'])
        self.assertTrue(result['export']['preservation_complete'])
        request, _ = self.phase('request-recovery')
        result = F['perform'](self.confirmation(self.refresh(auth), self.refresh(request)), execute=True)
        self.assertEqual(result['baseline_classification'], 'recovered-with-baseline-incomplete')
        with self.assertRaises(FileExistsError):
            self.phase('preserve-log')
        self.assertEqual(self.calls.count('log-export'), 1)
        for name in F['EXPORT_FILES']:
            self.assertEqual(stat.S_IMODE((export / name).stat().st_mode), 0o600)

    def test_preexited_failure_preserves_partial_and_allows_only_incomplete_baseline(self):
        self.phase('auth-checks')
        partial = b'schema=gemini-kmsg-v1\nsealed=no\nresult=failed\nreason=status-write-error\n'
        self.export_raw = frame(raw_status=status(result='failed', reason='deadline-expired', elapsed_ms='600000'),
                                stop='preexisting-terminal', overrides={
                                    'kmsg-exit': {'data': b'1\n'},
                                    'kmsg.status.partial': {'data': partial, 'state': 'regular',
                                                           'size_before': str(len(partial)), 'size_after': str(len(partial)),
                                                           'read_status': '0', 'encode_status': '0', 'stable': 'yes'}})
        export, result = self.phase('preserve-log')
        self.assertEqual(result['classification'], 'log-export-inconclusive')
        self.assertTrue(result['export']['preservation_complete'])
        self.assertEqual(result['export']['signal_attempts'], 0)
        self.assertEqual((export / 'kmsg.status.partial').read_bytes(), partial)
        self.assertEqual((export / 'kmsg-exit').read_bytes(), b'1\n')
        request, result = self.phase('request-recovery')
        self.assertEqual(result['classification'], 'native-recovery-requested')
        context = self.confirmation(self.refresh(self.sessions / 'auth-checks'), self.refresh(request))
        self.assertFalse(F['perform'](context)['full_baseline_eligible'])
        self.assertEqual(F['perform'](context, execute=True)['baseline_classification'], 'recovered-with-baseline-incomplete')

    def test_interrupted_export_keeps_raw_and_decoded_prefix_but_requires_emergency(self):
        self.export_raw = frame().split(b'name=kmsg.status\n', 1)[0]
        self.transport_overrides['log-export'] = {'reason': 'outer-timeout', 'exit_status': -15}
        export, result = self.phase('preserve-log')
        self.assertFalse(result['export']['export_complete'])
        self.assertFalse(result['export']['preservation_complete'])
        self.assertEqual((export / 'kmsg.log').read_bytes(), LOG)
        self.assertEqual((export / 'kmsg.status').read_bytes(), b'')
        self.assertEqual((export / 'log-export/stdout.txt').read_bytes(), self.export_raw)
        self.assertEqual(json.loads((export / 'log-export/process.json').read_bytes())['reason'], 'outer-timeout')
        count = len(self.calls)
        with self.assertRaises(ValueError):
            F['prepare'](self.attempt, self.admission('request-recovery', export_pin=self.refresh(export), recovery_mode='ordinary'))
        self.assertEqual(len(self.calls), count)
        self.assertFalse((self.sessions / 'request-recovery').exists())
        request, result = self.phase('request-recovery', export_pin=self.refresh(export), recovery_mode='emergency',
                                     emergency_reason='log-preservation-incomplete', acknowledge=True)
        self.assertEqual(result['recovery_mode'], 'emergency')
        self.assertTrue(result['acknowledge_unique_ram_loss'])
        self.assertEqual(self.calls[count:], ['native-reboot'])
        result = F['perform'](self.confirmation(request=self.refresh(request)), execute=True)
        self.assertEqual(result['baseline_classification'], 'recovered-with-baseline-incomplete')

    def test_unavailable_export_requires_exact_emergency_admission(self):
        invalid = [dict(recovery_mode='ordinary'), dict(recovery_mode='emergency'),
                   dict(recovery_mode='emergency', emergency_reason='anything', acknowledge=True),
                   dict(recovery_mode='emergency', emergency_reason='log-export-unavailable', acknowledge=1),
                   dict(recovery_mode='emergency', emergency_reason='log-preservation-incomplete', acknowledge=True)]
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                F['prepare'](self.attempt, self.admission('request-recovery', **changes))
        self.assertEqual(self.calls, [])
        path = self.admission('auth-checks', emergency_reason='immediate-safety-stop', acknowledge=True)
        with self.assertRaises(ValueError):
            F['prepare'](self.attempt, path)
        request, result = self.phase('request-recovery', recovery_mode='emergency',
                                     emergency_reason='log-export-unavailable', acknowledge=True)
        self.assertEqual(result['preservation_proof']['classification'], 'missing')
        self.assertEqual(self.calls, ['native-reboot'])
        self.assertEqual((request / 'admission.json').stat().st_mode & 0o777, 0o600)

    def test_available_export_rejects_unavailable_reason_and_nonnull_normal_ack(self):
        export, _ = self.phase('preserve-log')
        pin = self.refresh(export)
        for values in [dict(recovery_mode='emergency', emergency_reason='log-export-unavailable', acknowledge=True),
                       dict(recovery_mode='emergency', emergency_reason='log-preservation-incomplete', acknowledge=True),
                       dict(recovery_mode='ordinary', acknowledge=False),
                       dict(recovery_mode='ordinary', emergency_reason='immediate-safety-stop')]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                F['prepare'](self.attempt, self.admission('request-recovery', export_pin=pin, **values))
        context = F['prepare'](self.attempt, self.admission('request-recovery', export_pin=pin,
                                  recovery_mode='emergency', emergency_reason='immediate-safety-stop', acknowledge=True))
        self.assertEqual(F['perform'](context)['recovery_mode'], 'emergency')
        self.assertEqual(self.calls, ['log-export'])

    def test_partial_local_evidence_mutation_refuses_ordinary_recovery(self):
        export, _ = self.phase('preserve-log')
        for relative in ('kmsg.log', 'kmsg.status', 'kmsg.status.partial', 'kmsg-exit', 'result.json', 'log-export/command.sh'):
            with self.subTest(relative=relative):
                path = export / relative; original = path.read_bytes()
                self.write(path, original + b'changed\n')
                pin = self.refresh(export)
                with self.assertRaises(ValueError):
                    F['prepare'](self.attempt, self.admission('request-recovery', export_pin=pin, recovery_mode='ordinary'))
                self.assertEqual(self.confirmation(export=pin)['prior_proof']['preserve-log']['classification'], 'incomplete')
                self.write(path, original)
        self.assertEqual(self.calls, ['log-export'])

    def test_preservation_changed_after_prepare_refuses_before_native_request(self):
        export, _ = self.phase('preserve-log')
        context = F['prepare'](self.attempt, self.admission('request-recovery', export_pin=self.refresh(export), recovery_mode='ordinary'))
        self.write(export / 'kmsg.log', LOG + b'changed\n')
        result = F['perform'](context, execute=True)
        self.assertEqual(result['classification'], 'inconclusive')
        self.assertEqual(self.calls, ['log-export'])
        self.assertFalse((self.sessions / 'request-recovery/native-reboot').exists())

    def test_parser_failure_preserves_bounded_streams_and_consumes_export(self):
        with patch.dict(F['S'], parse_log_export=lambda *_args: (_ for _ in ()).throw(ValueError('fixture parser failure'))):
            export, result = self.phase('preserve-log')
        self.assertEqual(result['classification'], 'inconclusive')
        self.assertEqual((export / 'log-export/stdout.txt').read_bytes(), self.export_raw)
        self.assertTrue((export / 'log-export/stderr.txt').exists())
        self.assertTrue((export / 'log-export/process.json').exists())
        self.assertTrue((export / 'SHA256SUMS').exists())
        with self.assertRaises(FileExistsError):
            self.phase('preserve-log')
        with self.assertRaises(ValueError):
            F['prepare'](self.attempt, self.admission('request-recovery', export_pin=self.refresh(export), recovery_mode='ordinary'))
        context = F['prepare'](self.attempt, self.admission('request-recovery', export_pin=self.refresh(export),
                                  recovery_mode='emergency', emergency_reason='log-export-unavailable', acknowledge=True))
        self.assertEqual(F['perform'](context)['preservation_proof']['classification'], 'incomplete')
        self.assertEqual(self.calls, ['log-export'])

    def check_unpreserved_export(self, raw):
        self.export_raw = raw
        export, result = self.phase('preserve-log')
        self.assertTrue(result['export']['export_complete'])
        self.assertFalse(result['export']['preservation_complete'])
        self.assertEqual(result['classification'], 'log-export-inconclusive')
        pin = self.refresh(export)
        with self.assertRaises(ValueError):
            F['prepare'](self.attempt, self.admission('request-recovery', export_pin=pin, recovery_mode='ordinary'))
        context = F['prepare'](self.attempt, self.admission('request-recovery', export_pin=pin,
                                   recovery_mode='emergency', emergency_reason='log-preservation-incomplete', acknowledge=True))
        self.assertEqual(F['perform'](context)['preservation_proof']['classification'], 'verified')
        self.assertEqual(self.calls, ['log-export'])
        self.assertEqual((export / 'log-export/stdout.txt').read_bytes(), raw)

    def test_read_error_with_full_framing_refuses_ordinary_recovery(self):
        self.check_unpreserved_export(frame(overrides={'kmsg.log': {'read_status': '1'}}))

    def test_changed_snapshot_with_full_framing_refuses_ordinary_recovery(self):
        self.check_unpreserved_export(frame(overrides={'kmsg.log': {'stable': 'no', 'size_after': str(len(LOG) + 1)}}))

    def test_unconfirmed_terminal_logger_refuses_ordinary_recovery(self):
        missing = {'data': None, 'state': 'missing', 'size_before': '-', 'size_after': '-',
                   'read_status': 'none', 'encode_status': 'none', 'stable': 'not-applicable'}
        self.check_unpreserved_export(frame(stop='wait-timeout', overrides={'kmsg.status': missing, 'kmsg-exit': missing}))

    def test_logger_exiting_after_log_copy_cannot_authorize_ordinary_recovery(self):
        # All four later blocks are otherwise healthy/stable. A terminal
        # status obtained after the log cannot establish that the earlier
        # copy included records appended before that later exit.
        self.check_unpreserved_export(frame(terminal_before_export='no'))

    def test_prefix_cap_refuses_ordinary_recovery(self):
        self.check_unpreserved_export(frame(log=b'x' * 2097152, overrides={
            'kmsg.log': {'size_before': '2097153', 'size_after': '2097153', 'truncated': 'yes'}}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
