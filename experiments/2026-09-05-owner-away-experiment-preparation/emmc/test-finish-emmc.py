#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Private synthetic adapter fixtures: all subprocess creation is forbidden.

Prior baseline preparation and transport are modeled. The eMMC phase manifests,
claims, commands, raw observations, logger export and completion predecessors
are real fixture files revalidated by the adapter and reviewed parsers.
"""
import copy
import json
import os
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
M = runpy.run_path(str(HERE / 'finish-emmc.py'))
N = M['perform'].__globals__
T = runpy.run_path(str(HERE / 'test-launcher.py'))
L, C, F, S = (T[name] for name in ('L', 'C', 'F', 'S'))
W = runpy.run_path(str(L['EXPERIMENT'] / 'baseline/scripts/test-session-steps.py'))
write, process = T['write'], T['process']
FIRST, RECOVERED, OLD, BOOT = (T[name] for name in ('FIRST', 'RECOVERED', 'OLD', 'BOOT'))
NEW = '00000000-0000-0000-0000-000000000008'


class CompletionTests(unittest.TestCase):
    fixture_collect = T['LauncherTests'].fixture_collect

    def setUp(self):
        T['LauncherTests'].setUp(self)
        self.prepared['candidate']['members']['bin/reboot']['sha256'] = S['REBOOT_SHA']
        self.capture = T['T']['good_capture'](self.prepared).replace(T['T']['BOOT'].encode(), BOOT.encode())
        self.finish_calls = []
        self.finish_root = self.root / 'completion'
        self.finish_identity = M['source_identity']()
        real_regular = N['regular']

        def fixture_regular(path, limit, *args, **kwargs):
            path = Path(path)
            if path == self.prepared['keys'] / 'known_hosts': return b'fixture-host-pin'
            if path == self.root / 'artifacts/credentials/a53-recovery-known_hosts':
                return b'192.168.1.50 synthetic-fixture-host-identity\n'
            if path == self.root / 'artifacts/credentials/gemini_ed25519':
                return b'synthetic-placeholder-only'
            self.assertTrue(path.is_relative_to(self.root))
            return real_regular(path, limit, *args, **kwargs)

        def fixture_baseline_prepare(path):
            self.assertEqual(path, self.root / 'attempt/admission.json')
            actual = L['load'](path)
            self.assertEqual(actual, self.admission)
            L['check_admission'](actual)
            return self.context

        def fixture_ignored(repo, path):
            self.assertEqual(repo, self.root)
            self.assertTrue(path.is_relative_to(self.root))

        for value in (
            patch.dict(N, {'L': L, 'C': C, 'F': F, 'S': S, 'REPO': self.root, 'ROOT': self.finish_root,
                           'regular': fixture_regular, 'source_identity': lambda: self.finish_identity}),
            patch.dict(L, {'ATTEMPT_ROOT': self.root / 'attempt', 'prepare': fixture_baseline_prepare}),
            patch.dict(C, {'ignored': fixture_ignored}),
            patch.dict(F['known_good_command'].__globals__, {'REPO': self.root}),
        ):
            value.start(); self.addCleanup(value.stop)

    def seal_manifest(self, directory):
        raw = ''.join(L['sha'](path.read_bytes()) + '  ' + path.relative_to(directory).as_posix() + '\n'
                      for path in sorted(directory.rglob('*')) if path.is_file() and path.name != 'SHA256SUMS').encode()
        write(directory / 'SHA256SUMS', raw)
        return L['sha'](raw)

    def observe(self, changes=None):
        result = self.fixture_collect(changes)
        self.observation_hash = L['sha']((self.root / 'attempt/SHA256SUMS').read_bytes())
        return result

    def admission_for(self, action, **changes):
        value = {'schema': 1, 'experiment': 'a53-emmc-readonly', 'action': action,
            'observation_admission_id': self.admission['admission_id'], 'observation_manifest_sha256': self.observation_hash,
            'candidate_manifest_sha256': self.admission['candidate_manifest_sha256'], 'boot_id': BOOT,
            'source_identity': self.finish_identity, 'action_budgets': copy.deepcopy(M['STEPS'][action]),
            'custodian_role': 'Synthetic fixture', 'custody_handoff_sha256': 'e' * 64,
            'custody_exclusive': True, 'no_other_device_operations': True, 'observer_transport_stopped': True,
            'preservation_manifest_sha256': None, 'native_request_manifest_sha256': None,
            'known_good_known_hosts_sha256': None, 'physical_recovery_confirmed': False,
            'owner_console_accepted': False, 'recovery_mode': None, 'emergency_reason': None,
            'acknowledge_unique_ram_loss': None}
        if action == 'request-recovery': value['recovery_mode'] = 'ordinary'
        if action == 'confirm-recovery':
            value.update(physical_recovery_confirmed=True, known_good_known_hosts_sha256=
                         L['sha'](b'192.168.1.50 synthetic-fixture-host-identity\n'))
        value.update(changes)
        path = self.root / ('admission-' + action + '.json')
        write(path, L['json_bytes'](value))
        return M['prepare'](path)

    def execute(self, context, *, out=None, err=b'', metadata=None, interrupted=False):
        action = context['admission']['action']
        if out is None:
            if action == 'preserve-log': out = W['frame']()
            elif action == 'request-recovery':
                out = (f'__A53_NATIVE_RECOVERY_BEGIN__\nboot_id={BOOT}\nreboot_sha256={S["REBOOT_SHA"]}\n'
                       'request_count=1\npartition_access=none\nsync_requested=no\n__A53_NATIVE_RECOVERY_END__\n').encode() + b'Candidate AB: kernel restart requested now (BusyBox reboot -n -f).\n'
            else: out = f'kernel=3.18.41+\narchitecture=aarch64\nboot_id={NEW}\n'.encode()

        def transport(command, script, directory, seconds, **limits):
            self.assertTrue(directory.is_relative_to(self.root))
            self.assertEqual(script, M['script'](context))
            self.assertEqual((directory / 'command.sh').read_bytes(), script)
            self.assertEqual(json.loads((directory.parent / 'claim.json').read_bytes()), M['phase_claim'](context))
            self.assertEqual((seconds, limits['stdout_limit']), M['LIMITS'][action])
            self.assertEqual(limits['stderr_limit'], 16384)
            expected = ['gemini@192.168.1.50', '/bin/sh -s'] if action == 'confirm-recovery' else \
                       ['root@10.15.19.82', '/bin/busybox sh -s']
            self.assertEqual(command[-2:], expected)
            self.finish_calls.append(action)
            write(directory / 'stdout.txt', out); write(directory / 'stderr.txt', err)
            if interrupted: raise OSError('synthetic transport interrupted')
            return process(out, err, **({'exit_status': 255} if action == 'request-recovery' else {}) | (metadata or {}))

        with patch.dict(L, {'execution_gate': lambda: None}), patch.dict(N, {'__file__': str(L['EXPERIMENT'] / 'emmc/finish-emmc.py')}), \
             patch.dict(C, {'run_once': transport}):
            return M['perform'](context, True)

    def preservation(self, **kwargs):
        context = self.admission_for('preserve-log')
        result = self.execute(context, **kwargs)
        pin = L['sha']((self.finish_root / 'preserve-log/SHA256SUMS').read_bytes())
        return pin, result

    def native(self, preservation, **kwargs):
        context = self.admission_for('request-recovery', preservation_manifest_sha256=preservation, **kwargs)
        result = self.execute(context)
        pin = L['sha']((self.finish_root / 'request-recovery/SHA256SUMS').read_bytes())
        return pin, result

    def test_staged_execution_refused_and_dry_run_has_no_effects(self):
        self.observe(); context = self.admission_for('preserve-log')
        self.assertEqual(M['perform'](context)['classification'], 'dry-run')
        with self.assertRaisesRegex(ValueError, 'execution disabled'):
            M['perform'](context, True)
        self.assertFalse(self.finish_root.exists())
        self.assertEqual(self.finish_calls, [])

    def test_complete_raw_cycle_and_independent_one_shot_claims(self):
        self.observe(); preservation, result = self.preservation()
        self.assertEqual(result['classification'], 'complete-log-through-seal')
        native, result = self.native(preservation)
        self.assertFalse(result['recovery_confirmed'])
        context = self.admission_for('confirm-recovery', preservation_manifest_sha256=preservation,
                                     native_request_manifest_sha256=native, owner_console_accepted=True)
        result = self.execute(context)
        self.assertEqual(result['experiment_classification'], 'one-read-emmc-and-recovery-pass')
        self.assertEqual(self.finish_calls, ['preserve-log', 'request-recovery', 'confirm-recovery'])
        self.assertEqual(self.calls, ['pre', 'read', 'post'])
        for action in M['STEPS']:
            saved = L['load'](self.finish_root / action / 'admission.json')
            context = M['prepare'](self.finish_root / action / 'admission.json')
            with self.assertRaises(FileExistsError): self.execute(context)
            saved['custody_handoff_sha256'] = 'f' * 64
            path = self.root / 'new-admission.json'; write(path, L['json_bytes'](saved))
            with self.assertRaises(FileExistsError): self.execute(M['prepare'](path))
        self.assertEqual(len(self.finish_calls), 3)

    def test_strict_admission_scope_budgets_custody_identity(self):
        self.observe()
        changes = [{'schema': True}, {'boot_id': OLD}, {'candidate_manifest_sha256': 'f' * 64},
            {'source_identity': {}}, {'action_budgets': {'log_export': True}}, {'action_budgets': {'log_export': 2}},
            {'custodian_role': None}, {'custody_exclusive': False}, {'no_other_device_operations': False},
            {'observer_transport_stopped': False}, {'extra': True}, {'physical_recovery_confirmed': True}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError): self.admission_for('preserve-log', **change)

    def test_ordinary_recovery_requires_revalidated_preservation(self):
        self.observe()
        with self.assertRaises(ValueError): self.admission_for('request-recovery')
        with self.assertRaises(ValueError): self.admission_for('request-recovery', preservation_manifest_sha256='f' * 64)
        preservation, _ = self.preservation()
        directory = self.finish_root / 'preserve-log'
        # Resealing a tampered local summary cannot turn it into raw evidence.
        write(directory / 'result.json', b'{"classification":"complete-log-through-seal"}\n')
        preservation = self.seal_manifest(directory)
        with self.assertRaises(ValueError): self.admission_for('request-recovery', preservation_manifest_sha256=preservation)
        self.assertEqual(self.finish_calls, ['preserve-log'])

    def test_raw_observation_mutations_refuse_after_manifest_reseal(self):
        self.observe(); directory = self.root / 'attempt'
        cases = [('result.json', b'{"classification":"read-serviceability-only-pass"}\n'),
                 ('claim.json', b'{}\n'), ('read/command.sh', b'true\n'), ('post/claim.json', b'{}\n'),
                 ('read/process.json', L['json_bytes'](process(b'x')))]
        for name, raw in cases:
            path = directory / name; original = path.read_bytes()
            write(path, raw)
            pin = self.seal_manifest(directory)
            with self.subTest(name=name), self.assertRaises(ValueError): M['observation'](pin)
            write(path, original); self.seal_manifest(directory)

    def test_observation_parses_pinned_bytes_despite_failed_read_swap(self):
        self.observe(); directory = self.root / 'attempt'
        good = {name: (directory / name).read_bytes() for name in ('read/stdout.txt', 'read/process.json')}
        failed = T['read_frame'](self.prepared, dd_status='137')
        write(directory / 'read/stdout.txt', failed)
        write(directory / 'read/process.json', L['json_bytes'](process(failed)))
        # Pin a failed read beside the old successful result. A later good-file
        # substitution must not supply the bytes that the classifier evaluates.
        pin = self.seal_manifest(directory)
        original_inventory = N['inventory']
        swaps = []
        def swap_after_snapshot(*args):
            snapshot = original_inventory(*args)
            if args[0] == directory:
                for name, raw in good.items(): write(directory / name, raw)
                swaps.append(True)
            return snapshot
        with patch.dict(N, {'inventory': swap_after_snapshot}), self.assertRaises(ValueError):
            M['observation'](pin)
        self.assertEqual(swaps, [True])

    def test_prior_export_parses_pinned_bytes_across_both_verification_boundaries(self):
        self.observe(); self.preservation(); directory = self.finish_root / 'preserve-log'
        context = self.admission_for('preserve-log')
        good = {path.relative_to(directory).as_posix(): path.read_bytes()
                for path in directory.rglob('*') if path.is_file() and path.name != 'SHA256SUMS'}
        failed = W['frame'](raw_status=W['status'](result='failed', reason='deadline-expired'))
        parsed = S['parse_log_export'](failed, b'', process(failed))
        original_inventory, original_verify = N['inventory'], F['verify_phase']
        for boundary in ('shared-verifier', 'retained-snapshot'):
            write(directory / 'log-export/stdout.txt', failed)
            write(directory / 'log-export/process.json', L['json_bytes'](process(failed)))
            for name in F['EXPORT_FILES']: write(directory / name, parsed['files'].get(name, b''))
            pin = self.seal_manifest(directory)
            swaps = []
            def restore():
                for name, raw in good.items(): write(directory / name, raw)
                swaps.append(True)
            def swap_after_verify(*args):
                result = original_verify(*args)
                if args[0] == directory and boundary == 'shared-verifier': restore()
                return result
            def swap_after_snapshot(*args):
                snapshot = original_inventory(*args)
                if args[0] == directory and boundary == 'retained-snapshot': restore()
                return snapshot
            with self.subTest(boundary=boundary), patch.dict(F, {'verify_phase': swap_after_verify}), \
                 patch.dict(N, {'inventory': swap_after_snapshot}), self.assertRaises(ValueError):
                M['verify_prior'](context, 'preserve-log', pin)
            self.assertEqual(swaps, [True])

    def test_export_directory_entries_are_synced_after_manifest(self):
        self.observe(); events = []; original_sync = F['sync_directory']
        directory = self.finish_root / 'preserve-log'
        def sync(path):
            original_sync(path)
            events.append((path, (directory / 'SHA256SUMS').exists()))
        with patch.dict(F, {'sync_directory': sync}): self.preservation()
        self.assertEqual(events[-3:], [(directory / 'log-export', True), (directory, True), (self.finish_root, True)])
        self.assertEqual(self.finish_calls, ['preserve-log'])

    def test_changed_id_without_prior_proofs_is_recovery_only(self):
        self.observe()
        result = self.execute(self.admission_for('confirm-recovery', owner_console_accepted=True))
        self.assertEqual(result['experiment_classification'], 'recovered-with-emmc-incomplete')
        self.assertEqual(self.finish_calls, ['confirm-recovery'])

    def test_known_good_identity_and_physical_confirmation_are_required(self):
        self.observe()
        for change in ({'physical_recovery_confirmed': False}, {'known_good_known_hosts_sha256': 'f' * 64}):
            with self.subTest(change=change), self.assertRaises(ValueError): self.admission_for('confirm-recovery', **change)
        context = self.admission_for('confirm-recovery')
        for boot in (FIRST, RECOVERED, OLD, BOOT):
            raw = f'kernel=3.18.41+\narchitecture=aarch64\nboot_id={boot}\n'.encode()
            with self.subTest(boot=boot), self.assertRaises(ValueError):
                M['classify_phase'](context, raw, b'', process(raw))

    def test_late_controller_error_prevents_experiment_pass(self):
        self.observe()
        log = W['LOG'].replace(b'next message', b'mmc0: timeout waiting for hardware interrupt')
        preservation, result = self.preservation(out=W['frame'](log))
        self.assertEqual(result['classification'], 'complete-log-through-seal')
        self.assertEqual(result['controller_error_count'], 1)
        native, _ = self.native(preservation)
        context = self.admission_for('confirm-recovery', preservation_manifest_sha256=preservation,
                                     native_request_manifest_sha256=native, owner_console_accepted=True)
        self.assertEqual(self.execute(context)['experiment_classification'], 'recovered-with-emmc-incomplete')

    def test_terminal_failed_log_preserves_evidence_without_passing(self):
        self.observe()
        raw_status = W['status'](result='failed', reason='deadline-expired')
        preservation, result = self.preservation(out=W['frame'](raw_status=raw_status))
        self.assertTrue(result['export']['preservation_complete'])
        self.assertEqual(result['classification'], 'log-export-inconclusive')
        native, _ = self.native(preservation)
        context = self.admission_for('confirm-recovery', preservation_manifest_sha256=preservation,
                                     native_request_manifest_sha256=native, owner_console_accepted=True)
        self.assertEqual(self.execute(context)['experiment_classification'], 'recovered-with-emmc-incomplete')

    def test_partial_export_requires_separate_emergency_admission(self):
        self.observe(); frame = W['frame'](); raw = frame.split(b'name=kmsg.status\n')[0]
        preservation, result = self.preservation(out=raw, metadata={'reason': 'deadline'})
        self.assertFalse(result['export']['preservation_complete'])
        self.assertEqual((self.finish_root / 'preserve-log/kmsg.log').read_bytes(), W['LOG'])
        with self.assertRaises(ValueError): self.admission_for('request-recovery', preservation_manifest_sha256=preservation)
        for change in ({'acknowledge_unique_ram_loss': False}, {'emergency_reason': 'log-export-unavailable'}):
            values = {'preservation_manifest_sha256': preservation, 'recovery_mode': 'emergency',
                      'emergency_reason': 'log-preservation-incomplete', 'acknowledge_unique_ram_loss': True} | change
            with self.subTest(change=change), self.assertRaises(ValueError): self.admission_for('request-recovery', **values)
        native, result = self.native(preservation, recovery_mode='emergency',
                                    emergency_reason='log-preservation-incomplete', acknowledge_unique_ram_loss=True)
        self.assertEqual(result['recovery_mode'], 'emergency')
        context = self.admission_for('confirm-recovery', preservation_manifest_sha256=preservation,
                                     native_request_manifest_sha256=native, owner_console_accepted=True)
        self.assertEqual(self.execute(context)['experiment_classification'], 'recovered-with-emmc-incomplete')

    def test_failed_read_can_preserve_but_cannot_pass(self):
        self.observe({'read': {'out': T['read_frame'](self.prepared, dd_status='137')}})
        preservation, _ = self.preservation(); native, _ = self.native(preservation)
        context = self.admission_for('confirm-recovery', preservation_manifest_sha256=preservation,
                                     native_request_manifest_sha256=native, owner_console_accepted=True)
        self.assertEqual(self.execute(context)['experiment_classification'], 'recovered-with-emmc-incomplete')
        self.assertEqual(self.calls, ['pre', 'read'])

    def test_unattributable_preflight_and_unsealed_attempt_refuse_completion(self):
        self.observe({'pre': {'out': b'partial'}})
        with self.assertRaisesRegex(ValueError, 'attributable preflight'):
            self.admission_for('preserve-log')
        (self.root / 'attempt/SHA256SUMS').unlink()
        with self.assertRaises(ValueError): self.admission_for('preserve-log')

    def test_interruption_retains_bytes_consumes_claim_and_never_chains(self):
        self.observe(); context = self.admission_for('preserve-log')
        result = self.execute(context, out=b'synthetic partial export', interrupted=True)
        self.assertEqual(result['classification'], 'inconclusive')
        directory = self.finish_root / 'preserve-log'
        self.assertEqual((directory / 'log-export/stdout.txt').read_bytes(), b'synthetic partial export')
        self.assertTrue((directory / 'claim.json').is_file())
        self.assertTrue((directory / 'SHA256SUMS').is_file())
        with self.assertRaises(FileExistsError): self.execute(context)
        self.assertEqual(self.finish_calls, ['preserve-log'])

    def test_evidence_drift_before_dispatch_refuses_without_claim(self):
        self.observe(); context = self.admission_for('preserve-log')
        write(self.root / 'attempt/result.json', b'{}\n')
        with self.assertRaises(ValueError): self.execute(context)
        self.assertFalse(self.finish_root.exists())

    def test_completion_process_counts_types_elapsed_and_native_frame_refuse(self):
        self.observe(); context = self.admission_for('preserve-log'); raw = W['frame']()
        for changes in ({'stdout_bytes': True}, {'stdout_bytes': len(raw) + 1}, {'exit_status': False},
                        {'stdin_complete': 1}, {'reason': False}, {'elapsed_seconds': float('nan')},
                        {'elapsed_seconds': 32}, {'extra': True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                M['classify_phase'](context, raw, b'', process(raw, **changes))
        preservation, _ = self.preservation()
        context = self.admission_for('request-recovery', preservation_manifest_sha256=preservation)
        for raw in (b'', b'__A53_NATIVE_RECOVERY_BEGIN__\n', b'{"classification":"native-recovery-requested"}\n'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                M['classify_phase'](context, raw, b'', process(raw, exit_status=255))

    def test_console_acceptance_and_current_native_proof_are_independent(self):
        self.observe(); preservation, _ = self.preservation(); native, _ = self.native(preservation)
        context = self.admission_for('confirm-recovery', preservation_manifest_sha256=preservation,
                                     native_request_manifest_sha256=native)
        raw = f'kernel=3.18.41+\narchitecture=aarch64\nboot_id={NEW}\n'.encode()
        result, _ = M['classify_phase'](context, raw, b'', process(raw))
        self.assertEqual(result['experiment_classification'], 'recovered-with-emmc-incomplete')
        directory = self.finish_root / 'request-recovery'
        write(directory / 'native-reboot/stdout.txt', b'{"classification":"native-recovery-requested"}\n')
        native = self.seal_manifest(directory)
        context = self.admission_for('confirm-recovery', preservation_manifest_sha256=preservation,
                                     native_request_manifest_sha256=native, owner_console_accepted=True)
        result, _ = M['classify_phase'](context, raw, b'', process(raw))
        self.assertEqual(result['experiment_classification'], 'recovered-with-emmc-incomplete')
        self.assertEqual(result['prior_proof']['request-recovery']['classification'], 'incomplete')

    def test_prior_export_file_command_claim_inventory_tampering_refuses(self):
        self.observe(); self.preservation(); directory = self.finish_root / 'preserve-log'
        cases = [('kmsg.log', b'forged\n'), ('log-export/command.sh', b'true\n'), ('claim.json', b'{}\n'),
                 ('log-export/process.json', L['json_bytes'](process(b'', stdout_bytes=True)))]
        for name, raw in cases:
            path = directory / name; original = path.read_bytes(); write(path, raw)
            pin = self.seal_manifest(directory)
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.admission_for('request-recovery', preservation_manifest_sha256=pin)
            write(path, original); self.seal_manifest(directory)
        for kind in ('extra', 'symlink', 'hardlink'):
            path = directory / 'unexpected.txt'
            if kind == 'extra': write(path, b'synthetic')
            elif kind == 'symlink': path.symlink_to(directory / 'kmsg.log')
            else: os.link(directory / 'kmsg.log', path)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.admission_for('request-recovery', preservation_manifest_sha256=self.seal_manifest(directory))
            path.unlink(); self.seal_manifest(directory)


if __name__ == '__main__':
    unittest.main(verbosity=2)
