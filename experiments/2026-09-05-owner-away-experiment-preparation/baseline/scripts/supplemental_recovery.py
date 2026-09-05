#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One supplemental timeout/changed-ID recovery proof; never original success.

Read-only archive verification using the unchanged original source closure.
Caller bindings must be independently reviewed, not inferred from the archive.
"""
import hashlib
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGGREGATE_SHA = 'ba70f6df476283c0113d433ae856940cc9c031f864019da95f014324e16c926e'
ANNOUNCEMENT = b'Candidate AB: kernel restart requested now (BusyBox reboot -n -f).\n'
FAILED = {'classification': 'inconclusive', 'reason': 'native request/SSH disconnect unconfirmed',
          'budget': 'consumed', 'next_action': 'review evidence; no repeat; physical recovery if identity or USB is unavailable'}


def original_verifier():
    path = HERE / 'verified_baseline.py'
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != AGGREGATE_SHA:
        raise ValueError('supplemental-original-verifier-source')
    spec = importlib.util.spec_from_file_location('supplemental_original', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(root, bindings):
    A = original_verifier()
    A.fields(bindings, ('admission_id', 'candidate_sha256', 'candidate_manifest_sha256',
                       'baseline_manifest_sha256', 'confirmation_manifest_sha256', 'phase_manifests'), 'supplemental-bindings')
    A.need(type(bindings['admission_id']) is str and A.UUID.fullmatch(bindings['admission_id']), 'supplemental-id')
    A.need(all(A.valid_hash(bindings[k]) for k in bindings if k not in ('admission_id', 'phase_manifests')), 'supplemental-hashes')
    pins = bindings['phase_manifests']
    A.fields(pins, ('auth-checks', 'preserve-log', 'request-recovery'), 'supplemental-phase-pins')
    A.need(all(A.valid_hash(v) for v in pins.values()), 'supplemental-phase-hash')
    C, F, D = A.tools()  # Exact original closure, before evidence interpretation.
    root = Path(root).absolute()
    A.private_dir(root)
    attempt = root / 'attempts' / bindings['admission_id']
    sessions = root / 'sessions' / bindings['admission_id']
    A.private_dir(sessions)
    A.need({p.name for p in sessions.iterdir()} == set(F.STEPS), 'supplemental-session-inventory')
    context = A.original(attempt, bindings, C, F, D)
    boot = context['baseline']['boot_id']
    A.need(context['prepared']['candidate']['members']['bin/reboot']['sha256'] == F.S['REBOOT_SHA'], 'supplemental-wrapper-pin')
    confirmation = sessions / 'confirm-recovery'
    final = A.confirm_inventory(confirmation, bindings['confirmation_manifest_sha256'], F)
    final_context = A.finish_admission(confirmation, 'confirm-recovery', context, pins, F, final)
    # finish_admission requires both actual owner predicates and all prior pins.
    proof = {}
    for action in ('auth-checks', 'preserve-log', 'request-recovery'):
        directory = sessions / action
        F.verify_phase(directory, pins[action], action)
        manifest = A.read(directory / 'SHA256SUMS', 16384)
        A.need(A.digest(manifest) == pins[action], 'supplemental-phase-manifest')
        snapshot = A.private_snapshot(directory, manifest, F)
        prior = A.finish_admission(directory, action, context, pins, F, snapshot)
        F.verify_phase_commands(directory, prior, action, snapshot=snapshot)
        if action == 'auth-checks':
            result = F.recheck_auth(directory, boot, snapshot=snapshot)
        elif action == 'preserve-log':
            result = F.recheck_export(directory, boot, snapshot=snapshot)
            A.need(result['classification'] == 'complete-log-through-seal' and
                   result['export']['preservation_complete'] is True, 'supplemental-incomplete-log')
        else:
            out = F.snapshot_read(snapshot, 'native-reboot/stdout.txt', 131072)
            err = F.snapshot_read(snapshot, 'native-reboot/stderr.txt', 16384)
            proc = A.process_value(F.snapshot_load(snapshot, 'native-reboot/process.json'), out, err, 15)
            expected = (f'__A53_NATIVE_RECOVERY_BEGIN__\nboot_id={boot}\nreboot_sha256={F.S["REBOOT_SHA"]}\n'
                        'request_count=1\npartition_access=none\nsync_requested=no\n__A53_NATIVE_RECOVERY_END__\n').encode() + ANNOUNCEMENT
            A.need(out == expected and err == b'' and proc['stdin_complete'] is True and
                   proc['reason'] == 'outer-timeout' and proc['exit_status'] == 255 and
                   14 <= proc['elapsed_seconds'] <= 15, 'supplemental-exact-timeout-witness')
            try:
                F.S['parse_recovery_request'](out, proc, boot)
            except ValueError as error:
                A.need(str(error) == FAILED['reason'], 'supplemental-original-refusal-changed')
            else:
                raise A.Refused('supplemental-original-unexpected-pass')
            result = FAILED
        A.need(A.encoded(F.snapshot_load(snapshot, 'result.json')) == A.encoded(result), 'supplemental-stored-result-drift')
        item = {'classification': 'verified', 'manifest_sha256': pins[action]}
        if action == 'preserve-log':
            item.update(preservation_complete=True, complete_log=True)
        if action == 'request-recovery':
            item.update(classification='incomplete', reason=FAILED['reason'])
        proof[action] = item
    A.need(F.snapshot_read(final, 'known-good-probe/command.sh', 65536) == F.S['GEMIAN_PROBE'], 'supplemental-confirm-command')
    out = F.snapshot_read(final, 'known-good-probe/stdout.txt', 131072)
    err = F.snapshot_read(final, 'known-good-probe/stderr.txt', 16384)
    proc = A.process_value(F.snapshot_load(final, 'known-good-probe/process.json'), out, err, 15)
    result = F.S['parse_gemian'](out, err, proc, context['prepared']['recovery_id'], boot)
    result.update(prior_proof=proof, baseline_classification='recovered-with-baseline-incomplete')
    A.need(A.encoded(F.snapshot_load(final, 'result.json')) == A.encoded(result), 'supplemental-confirm-result')
    A.need(not F.full_baseline_eligible(final_context, proof), 'supplemental-original-eligibility-changed')
    A.need(F.verified_attempt(attempt) == context['manifest'], 'supplemental-baseline-changed')
    for action, pin in pins.items():
        F.verify_phase(sessions / action, pin, action)
    A.confirm_inventory(confirmation, bindings['confirmation_manifest_sha256'], F)
    A.sources()
    return {'classification': 'supplemental-authenticated-baseline-recovery-verified',
            'original_baseline_classification': 'recovered-with-baseline-incomplete',
            'original_request_classification': 'inconclusive', 'orderly_ssh_disconnect_proven': False,
            'baseline_manifest_sha256': bindings['baseline_manifest_sha256'],
            'confirmation_manifest_sha256': bindings['confirmation_manifest_sha256'],
            'phase_manifests': dict(pins), 'owner_return_observed': True,
            'changed_ID_Gemian': True, 'network_access': 'none', 'dependent_admission': False}
