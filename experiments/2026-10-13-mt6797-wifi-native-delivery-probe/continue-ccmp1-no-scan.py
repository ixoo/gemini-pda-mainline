#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ROOT-only continuation of exact claimed CCMP1 at failed log-export; offline default.

No startup, observation, probe, scan, helper launch or new session claim. Revalidate
the original private64/credential/source/receipt context, then append only pending
seal, admitted read-only regression and ONE reviewed recovery. No retries.
"""
import argparse
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
BOOT = 'da2acc9f-8821-4452-8631-ca7d487e4793'
INVENTORY_SHA = '06d1e6b89974e46f96380394c235d2d38b91e85d64e087ab4849d718493fc84c'
CUSTODIAN_SHA = 'b03329f75a3e3063389632c4281da4976eb8581c80a92e9e413cb5b0b7c584c0'
PREPARE_SOURCE_SHA = '5e3a74f75705ee37a8de1dc17487859dce33a91ef9063c6cbdee01b2c83fdf41'
SESSION_TOOL_SHA = '69ff16a879c779a0dda36a3c5f73eef89c4f3d5ce6b23c3e54e7b9daec99a19d'
PENDING = ('log-export', 'wiphy-probe', 'provider-probe', 'native-reboot')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def scope():
    inventory = (HERE / 'results/ccmp1-no-scan-inventory.json').read_bytes()
    report = (HERE / 'results/ccmp1-startup-custodian.json').read_bytes()
    require(digest(inventory) == INVENTORY_SHA and digest(report) == CUSTODIAN_SHA,
            'ROOT continuation admission changed')
    report = json.loads(report)
    require(report['session_already_claimed'] is True and report['scan_attempted'] is False and
            report['helper_started'] is False and report['recovery_requested'] is False and
            report['frozen_tooling'] == 'ca7ee96b591ae51483f8fd917c4f70b3e5e2693d',
            'not the admitted never-started no-scan failure')
    return json.loads(inventory)


def unchanged(root, inventory):
    for name, identity in inventory['files'].items():
        path = root / name
        require(path.is_file() and not path.is_symlink() and
                path.stat().st_size == identity['bytes'] and digest(path.read_bytes()) == identity['sha256'],
                'original evidence changed: ' + name)


def admit(root):
    inventory = scope()
    require(root.is_dir() and not root.is_symlink(), 'unsafe session root')
    files, directories = set(), set()
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'symlink in session evidence')
        relative = path.relative_to(root).as_posix()
        if path.is_file():
            files.add(relative)
        elif path.is_dir():
            directories.add(relative)
        else:
            raise ValueError('nonregular session evidence')
    require(files == set(inventory['files']) and directories == set(inventory['directories']),
            'not the exact unconsumed failed-log-export inventory; no retry admitted')
    unchanged(root, inventory)
    return True


def prepare(candidate):
    tool = HERE / 'laptop-session-ccmp.py'
    require(digest(tool.read_bytes()) == SESSION_TOOL_SHA, 'frozen session tool changed')
    spec = importlib.util.spec_from_file_location('ccmp1_frozen_session', tool)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ph = module.NH.PH
    root = module.NH.ROOT
    admit(root)
    phase_a = json.loads((module.NH.CAPTURE / 'phase-a-result.json').read_bytes())
    require(phase_a.get('ready_for_scan') is False and phase_a.get('wlan_firmware_stopped') is True,
            'continuation requires the captured pre-radio registration refusal')
    helper = ph.HELPER
    require(helper.record['started'] is False and helper.proc is None and helper.pgid is None,
            'a started helper cannot use no-scan continuation')
    host = ph.HOST.DOMAIN.HOST
    original = host.prepare
    # Every existing offline validator is reused. Only the initial unclaimed-root
    # assertion is replaced, exactly once, with stricter pinned continuation
    # inventory admission. Original files/guards are not edited or renamed.
    source_path = Path(original.__code__.co_filename)
    require(digest(source_path.read_bytes()) == PREPARE_SOURCE_SHA, 'offline prepare source changed')
    source = inspect.getsource(original)
    anchor = ("require({p.name for p in ROOT.iterdir()} == {'deployment-summary.txt'},\n"
              "            'session already claimed or unexpected initial files')")
    require(source.count(anchor) == 1, 'one-time preparation assertion changed')
    namespace = dict(original.__globals__)
    namespace['admit_ccmp1_continuation'] = admit
    source = source.replace(anchor, 'admit_ccmp1_continuation(ROOT)')
    exec(compile(source, str(source_path) + ':ccmp1-offline-continuation', 'exec'), namespace)
    host.prepare = namespace['prepare']
    try:
        prepared = ph.SCAN.PREPARE(candidate)  # same offline no-scan preparation, never execute()
    finally:
        host.prepare = original
    prepared['finish'].REPO = module.PRIVATE_REPO
    collector = prepared['collector']
    claim = json.loads(collector.regular(root / 'execution-claim.json', 16384),
                       object_pairs_hook=collector.no_duplicates)
    require(claim == {**prepared['claim'], 'budget': 'consumed'}, 'original consumed claim/context differs')
    require(collector.regular(root / 'ssh-command.json', 16384) == host.encoded(prepared['command']),
            'original authenticated command differs')
    # Reload the pinned BASE invoker, not the C2/helper/export wrapper. There is
    # no supplicant/cycle/quiescence record to invent when the leaf never ran.
    base = module.ORIGINAL_RUN_PATH(str(host.SERVICE / 'a53-ram-host.py'))
    plain = base['invoke']
    budgets = {name: (claim['phase_budgets'][name]['seconds'],
                      claim['phase_budgets'][name]['stdout_bytes']) for name in PENDING}
    require(all(claim['phase_budgets'][name]['connections'] == 1 and
                claim['phase_budgets'][name]['stderr_bytes'] == 16384 for name in PENDING),
            'pending budgets changed')
    plain.__globals__['BUDGETS'] = budgets  # excludes observation/probe/startup/radio/C2 effects
    runtime = prepared['execute'].__globals__
    runtime['invoke'] = plain  # pending read-only regression wrappers retain their original bodies
    require(prepared['steps'].probe_script(prepared['context']['candidate'], BOOT) ==
            collector.regular(root / 'probe/command.sh', 131072), 'saved probe script differs')
    base['probe_ok'](collector.regular(root / 'probe/stdout.txt', 131072),
                     collector.regular(root / 'probe/stderr.txt', 16384),
                     json.loads(collector.regular(root / 'probe/process.json', 16384)), BOOT)
    observed = prepared['binding']['classify_observation'](prepared['context'], collector,
        collector.regular(root / 'observation/stdout.txt', 131072),
        collector.regular(root / 'observation/stderr.txt', 16384),
        json.loads(collector.regular(root / 'observation/process.json', 16384)))
    require(observed['classification'] == 'baseline-observation-only-pass' and observed['boot_id'] == BOOT,
            'saved observation no longer passes')
    require(collector.regular(root / 'observation/command.sh', 131072) ==
            collector.remote_script(prepared['context']), 'saved observation script differs')
    return prepared, plain, runtime['preserved_snapshot'], host.encoded


def execute(prepared, invoke, snapshot, encoded):
    root, collector, finish = prepared['root'], prepared['collector'], prepared['finish']
    admit(root)
    status = prepared['network'].require_ready()
    require(status['ready'], 'direct USB route absent')
    collector.write_new(root / 'ccmp1-continuation-claim.json', encoded({
        'boot': BOOT, 'original_inventory_sha256': INVENTORY_SHA, 'custodian_report_sha256': CUSTODIAN_SHA,
        'program_sha256': digest(Path(__file__).read_bytes()), 'pending_budget': 'consumed',
        'phase_allowlist': list(PENDING), 'helper_quiescence': 'not-applicable-never-started'}))
    finish.sync_directory(root)
    result = {'mainline_boot': BOOT, 'phase': 'log-export', 'recovery_requested': False,
              'recovery_confirmed': False, 'regression_pass': False, 'scan_attempted': False,
              'ccmp_compatibility_pass': False}
    try:
        raw, err, process = invoke(prepared, 'log-export',
            prepared['steps'].seal_script(prepared['context']['candidate'], BOOT), network_status=status)
        export = prepared['steps'].parse_log_export(raw, err, process)
        require(set(export['files']) <= set(finish.EXPORT_FILES), 'log export file scope changed')
        for name in finish.EXPORT_FILES:
            collector.write_new(root / name, export['files'].get(name, b''))
        collector.write_new(root / 'log-result.json', encoded(export['result']))
        unchanged(root, scope())
        result['phase'] = 'preservation'
        proof = snapshot(prepared, BOOT)  # original read-only probes/full seal/regression binding
        require(proof['log_complete'] is True, 'full log-through-seal proof required before recovery')
        result['preservation'] = proof
        result['phase'] = 'native-reboot'
        result['recovery_requested'] = None
        raw, _err, process = invoke(prepared, 'native-reboot',
            prepared['steps'].recovery_script(prepared['context']['candidate'], BOOT))
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
            result['regression_pass'] = proof['log_complete']
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result['reason'] = str(error)
    collector.write_new(root / 'ccmp1-continuation-result.json', encoded(result))
    finish.sync_directory(root)
    finish.sync_directory(root.parent)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    prepared, invoke, snapshot, encoded = prepare(args.candidate)
    if not args.execute:
        print('offline-continuation-preflight=pass; device_action=none; no claim consumed')
        return 0
    result = execute(prepared, invoke, snapshot, encoded)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['regression_pass'] and result['recovery_confirmed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
