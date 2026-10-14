#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ROOT-only ONE unused CCMP1 native recovery after complete AVAILABLE preservation.

Offline default. No observation/probe/startup/session/export/seal retry. Retain
the logger deadline failure and false full-log/regression/compatibility verdict.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess

HERE = Path(__file__).resolve().parent
BOOT = 'da2acc9f-8821-4452-8631-ca7d487e4793'
INVENTORY_SHA = 'c72deace5e4276d99189d289d2d3b3fab52a0972b1331ae7edf7dc4334018181'
SEALED_MANIFEST_SHA = 'c467e5071ceafc87ccc702260cf5eeeabfa07683ec7cf01c9c7e4f5071a0d7e2'
CONTINUATION_SHA = '9d9588bfae6d35bb2fccf2fa9cdf355a42052beff8fdf58582c194798628d09a'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def scope():
    raw = (HERE / 'results/ccmp1-recovery-only-inventory.json').read_bytes()
    require(sha(raw) == INVENTORY_SHA, 'ROOT recovery inventory changed')
    inventory = json.loads(raw)
    require(len(inventory['files']) == 39 and len(inventory['directories']) == 5,
            'not the exact preserved CCMP1 recovery point')
    return inventory


def admit(root):
    require(root.is_dir() and not root.is_symlink(), 'unsafe session root')
    inventory = scope()
    files, directories = set(), set()
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'symlink in preserved evidence')
        name = path.relative_to(root).as_posix()
        if path.is_file():
            files.add(name)
        elif path.is_dir():
            directories.add(name)
        else:
            raise ValueError('nonregular preserved evidence')
    require(files == set(inventory['files']) and directories == set(inventory['directories']),
            'not the exact unused-recovery inventory; no repeat admitted')
    for name, identity in inventory['files'].items():
        raw = (root / name).read_bytes()
        require(len(raw) == identity['bytes'] and sha(raw) == identity['sha256'],
                'preserved evidence changed: ' + name)
    return True


def available_proof(prepared):
    root, collector, finish = prepared['root'], prepared['collector'], prepared['finish']
    manifest = collector.regular(root / 'PRE_RECOVERY_SHA256SUMS', 16384)
    require(sha(manifest) == SEALED_MANIFEST_SHA, 'original sealed manifest changed')
    saved = finish.verified_snapshot(root, manifest)
    require(len(saved) == 37, 'original37-file sealed snapshot changed')
    export = finish.recheck_export(root, BOOT, snapshot=saved)
    evidence = export['export']
    require(evidence.get('preservation_complete') is True and evidence.get('export_complete') is True and
            evidence.get('transport_complete') is True, 'complete AVAILABLE preservation required')
    # This exact recovery is not a new full-log/regression admission. Its logger
    # had already reached its finite deadline before the seal attempt.
    require(export['classification'] == 'log-export-inconclusive' and
            evidence.get('stop') == 'preexisting-terminal', 'expected bounded logger limitation changed')
    return {'available_preservation_complete': True, 'log_complete': False,
            'sealed_manifest_sha256': sha(manifest), 'sealed_files': len(saved),
            'classification': export['classification'], 'reason': evidence.get('reason')}


def prepare(candidate):
    path = HERE / 'continue-ccmp1-no-scan.py'
    require(sha(path.read_bytes()) == CONTINUATION_SHA, 'reviewed continuation source changed')
    old = runpy.run_path(str(path))
    # Reuse the already-reviewed offline context reconstruction, substituting
    # only its exact inventory admission for this later39-file state. No old
    # execute(), invoker, snapshot callback or helper is executed here.
    old['prepare'].__globals__['admit'] = admit
    prepared, invoke, _unused_snapshot, encoded = old['prepare'](candidate)
    require(prepared['root'].name == 'session-ccmp1', 'wrong runtime namespace')
    invoke.__globals__['BUDGETS'] = {'native-reboot': (15, 131072)}
    proof = available_proof(prepared)
    return prepared, invoke, encoded, proof


def execute(prepared, invoke, encoded, proof):
    root, collector, finish = prepared['root'], prepared['collector'], prepared['finish']
    admit(root)
    require(available_proof(prepared) == proof, 'available evidence changed after preflight')
    status = prepared['network'].require_ready()
    require(status['ready'], 'direct USB route absent')
    # Preserve ALL39 current files, including the old manifest and failed
    # continuation result, before consuming the still-unused native request.
    inventory = scope()
    manifest = ''.join(identity['sha256'] + '  ' + name + '\n'
                       for name, identity in sorted(inventory['files'].items())).encode()
    require(len(finish.verified_snapshot(root, manifest)) == 39, 'all39-file binding differs')
    collector.write_new(root / 'CCMP1_AVAILABLE_RECOVERY_SHA256SUMS', manifest)
    finish.sync_directory(root)
    require(collector.regular(root / 'CCMP1_AVAILABLE_RECOVERY_SHA256SUMS', 16384) == manifest,
            'all39 manifest readback differs')
    collector.write_new(root / 'ccmp1-recovery-only-claim.json', encoded({
        'boot': BOOT, 'budget': 'one-unused-native-reboot-consumed',
        'original39_inventory_sha256': INVENTORY_SHA, 'available_manifest_sha256': sha(manifest),
        'program_sha256': sha(Path(__file__).read_bytes()),
        'helper_quiescence': 'not-applicable-never-started', 'log_complete': False}))
    finish.sync_directory(root)
    result = {'mainline_boot': BOOT, 'preservation': proof, 'phase': 'native-reboot',
              'recovery_requested': None, 'recovery_confirmed': False, 'regression_pass': False,
              'ccmp_compatibility_pass': False, 'classification': 'preserved-incomplete-log-not-yet-returned'}
    try:
        raw, _err, process = invoke(prepared, 'native-reboot',
            prepared['steps'].recovery_script(prepared['context']['candidate'], BOOT), network_status=status)
        requested = finish.parse_recovery_request(raw, process, BOOT,
            {'finish_source_sha256': prepared['binding']['SOURCE_PINS']['finish-baseline.py']})
        collector.write_new(root / 'native-request-result.json', encoded(requested))
        finish.sync_directory(root)
        result['recovery_requested'] = True
        result['phase'] = 'gemian-return'
        returned = prepared['returning'].watch(prepared['returning'].prepare(prepared['candidate_path']))
        result['return'] = returned
        result['recovery_confirmed'] = returned['recovery_confirmed']
        if returned['recovery_confirmed']:
            result['returned_gemian_boot'] = returned['boot_id']
            result['classification'] = 'returned-with-incomplete-log'
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result['reason'] = str(error)
    collector.write_new(root / 'ccmp1-recovery-only-result.json', encoded(result))
    finish.sync_directory(root)
    finish.sync_directory(root.parent)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    prepared, invoke, encoded, proof = prepare(args.candidate)
    if not args.execute:
        print('offline-recovery-only-preflight=pass; device_action=none; unused request unconsumed')
        return 0
    result = execute(prepared, invoke, encoded, proof)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['recovery_confirmed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
