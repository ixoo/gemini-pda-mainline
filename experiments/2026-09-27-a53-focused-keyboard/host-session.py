#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One focused A53 keyboard trial, private evidence, and reviewed return."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / 'experiments/2026-09-09-standard-kernel-package'
FOCUSED = ROOT / 'experiments/2026-09-27-a53-focused-keyboard'
KEYBOARD = ROOT / 'experiments/2026-09-05-owner-away-experiment-preparation/keyboard'
HOST = runpy.run_path(str(EXPERIMENT / 'a53-ram-host.py'))
SESSION = runpy.run_path(str(FOCUSED / 'session.py'))
PARENT_SESSION = runpy.run_path(str(EXPERIMENT / 'a53-ram-session.py'))
INSTALLER = runpy.run_path(str(FOCUSED / 'installer.py'))
RETURN = runpy.run_path(str(EXPERIMENT / 'a53-ram-return-v2.py'))
CAPTURE = runpy.run_path(str(KEYBOARD / 'capture.py'))
ANALYZE = runpy.run_path(str(KEYBOARD / 'analyze-focused.py'))
CANDIDATE = ROOT / 'artifacts/a53-focused-keyboard/candidate-ea8adc121fdd2ee1008fe6cca852db4e05e35c0cb9698930b4ceb657018adac2'
OUT = ROOT / 'artifacts/a53-focused-keyboard/session-1'
PREVIOUS = '8bda7be0-2678-4092-b3e4-5b8b9a953505'
PADDED_SHA = '34b56a58abe0932d1e7374ed7e668487518fa9d6067a9bf6d60c19d313780020'
KEYS = ROOT / 'artifacts/credentials/a53-auth'
TRUST = ROOT / 'artifacts/credentials/a53-recovery-known_hosts'
GEMIAN_KEY = ROOT / 'artifacts/credentials/gemini_ed25519'
sha = HOST['sha']
encoded = HOST['encoded']
require = HOST['require']
HOST['BUDGETS']['keyboard'] = (55, 131072)


def keyboard_script(context, steps, boot):
    candidate = context['candidate']
    guard = steps.identity_script(candidate, boot) + steps.ram_guard_script()
    guard += CAPTURE['console_guard'](candidate) + CAPTURE['reader_guard']()
    guard += r'''
event_count=0
event_name=
event_minor=
for path in /sys/class/input/event*; do
  [ -e "$path" ] || continue
  if [ "$($BB cat "$path/device/name")" = keyboard-matrix ]; then
    event_count=$((event_count+1))
    event_name=${path##*/}
    event_minor=$($BB cat "$path/dev")
  fi
done
[ "$event_count" = 1 ]
[ "$event_minor" = 13:64 ]
[ "$event_name" = event0 ]
[ "$($BB cat /proc/sys/kernel/random/boot_id)" = ''' + boot + r''' ]
$BB printf '__A53_KEYBOARD_BEGIN__\nboot_id=%s\ninput=%s %s\n' ''' + boot + r''' "$event_name" "$event_minor"
/bin/keyboard-observe --diagnose "$event_name" 13 64
$BB printf '__A53_KEYBOARD_END__\n'
'''
    guard += steps.identity_script(candidate, boot)
    guard += CAPTURE['console_guard'](candidate)
    return guard.encode('ascii')


def prepare():
    evidence = ROOT / 'artifacts/device-install-evidence/a53-focused-keyboard-deployment-1'
    deployment = evidence / 'deployment-summary.txt'
    sums = evidence / 'SHA256SUMS'
    require(evidence.is_dir() and not evidence.is_symlink(), 'deployment evidence absent')
    require(deployment.is_file() and not deployment.is_symlink() and
            sums.is_file() and not sums.is_symlink(), 'deployment receipt files unsafe')
    summary = deployment.read_bytes()
    require(len(summary) <= 16384, 'deployment receipt size')
    checks = sums.read_text()
    require(checks == sha(summary) + '  deployment-summary.txt\n', 'deployment checksum differs')
    INSTALLER['receipt'](summary.decode('ascii'), PADDED_SHA, INSTALLER['MANIFEST_SHA'], PREVIOUS)
    context, collector, steps, finish = SESSION['prepare'](CANDIDATE, PREVIOUS)
    require(sha(collector.regular(CANDIDATE / 'boot2-padded.img', 16777216)) == PADDED_SHA,
            'installed image pin differs')
    require(context['candidate']['members']['bin/keyboard-observe']['sha256'] ==
            SESSION['READER_SHA'],
            'keyboard helper differs')
    validator = runpy.run_path(str(ROOT / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/validate-candidate.py'))
    authorized, host_key, known = validator['check_credentials'](KEYS)
    require(sha(authorized) == context['candidate']['members']['root/.ssh/authorized_keys']['sha256'] and
            sha(host_key) == context['candidate']['members']['etc/dropbear/host_key']['sha256'] and
            sha(known) == sha(collector.regular(KEYS / 'known_hosts', 8192)),
            'mainline authentication differs')
    require(sha(collector.regular(TRUST, 8192)) == RETURN['TRUST_SHA'], 'Gemian trust changed')
    credentials = {path: sha(collector.regular(path, 16384)) for path in
                   (KEYS / 'admin', KEYS / 'known_hosts', TRUST, GEMIAN_KEY)}
    network = runpy.run_path(str(ROOT / 'experiments/2026-09-05-owner-away-experiment-preparation/emmc/mainline_host.py'))
    return {'context': context, 'collector': collector, 'steps': steps, 'finish': finish,
            'network': type('Network', (), {'require_ready': staticmethod(network['require_ready'])})(),
            'credentials': credentials, 'command': collector.ssh_command(KEYS), 'root': OUT}


def phase(prepared, label, script, status=None):
    raw, err, process = HOST['invoke'](prepared, label, script, network_status=status)
    HOST['process_ok'](raw, err, process)
    return raw, process


def run(prepared, status):
    c, s, f = prepared['collector'], prepared['steps'], prepared['finish']
    ctx, root = prepared['context'], prepared['root']
    root.mkdir(mode=0o700)
    c.write_new(root / 'claim.json', encoded({'budget': 'consumed', 'previous_gemian_boot': PREVIOUS,
                'boot2_full_sha256': PADDED_SHA, 'candidate_sha256': ctx['admission']['candidate_sha256'],
                'runner_sha256': sha(Path(__file__).read_bytes()),
                'phase_budgets': HOST['BUDGETS'], 'direct_usb': status}))
    f.sync_directory(root)
    result = {'classification': 'inconclusive', 'phase': 'observation', 'recovery_requested': False}
    try:
        raw, err, process = HOST['invoke'](prepared, 'observation', c.remote_script(ctx), network_status=status)
        observed = PARENT_SESSION['classify_observation'](ctx, c, raw, err, process)
        c.write_new(root / 'observation-result.json', encoded(observed))
        require(observed['classification'] == 'baseline-observation-only-pass', 'A53 observation failed')
        boot = observed['boot_id']
        require(boot != PREVIOUS, 'mainline boot did not change')
        result['mainline_boot'] = boot
        result['phase'] = 'probe'
        raw, err, process = HOST['invoke'](prepared, 'probe', s.probe_script(ctx['candidate'], boot))
        HOST['probe_ok'](raw, err, process, boot)
        result['phase'] = 'keyboard'
        print('Keyboard phase beginning now.', flush=True)
        result['keyboard_pass'] = False
        try:
            raw, process = phase(prepared, 'keyboard', keyboard_script(ctx, s, boot))
            begin = ('__A53_KEYBOARD_BEGIN__\nboot_id=' + boot + '\ninput=event0 13:64\n').encode()
            end = b'__A53_KEYBOARD_END__\n'
            require(raw.count(begin) == 1 and raw.count(end) == 1 and raw.startswith(begin), 'keyboard framing')
            capture, suffix = raw[len(begin):].split(end, 1)
            require(not suffix, 'keyboard trailing data')
            analysis = ANALYZE['analyze'](capture, repeat_aware=True)
            c.write_new(root / 'keyboard-result.json', encoded(analysis))
            result['keyboard_pass'] = (analysis['outcome'] == 'observations-complete' and
                all(case['input'] == 'match' and case['repeat_aware_vt'] == 'match'
                    for case in analysis['cases']))
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            result['keyboard_reason'] = str(error)
        result['phase'] = 'log-export'
        raw, err, process = HOST['invoke'](prepared, 'log-export', s.seal_script(ctx['candidate'], boot))
        export = s.parse_log_export(raw, err, process)
        require(set(export['files']) <= set(f.EXPORT_FILES), 'log export file scope')
        for name in f.EXPORT_FILES:
            c.write_new(root / name, export['files'].get(name, b''))
        c.write_new(root / 'log-result.json', encoded(export['result']))
        require(f.recheck_export(root, boot)['export']['preservation_complete'] is True,
                'complete RAM log required before recovery')
        result['phase'] = 'preservation'
        manifest = ''.join(sha(c.regular(p, 4 * 1024 * 1024)) + '  ' +
                           p.relative_to(root).as_posix() + '\n'
                           for p in sorted(root.rglob('*')) if p.is_file()).encode()
        c.write_new(root / 'PRE_RECOVERY_SHA256SUMS', manifest)
        for path in root.iterdir():
            if path.is_dir(): f.sync_directory(path)
        f.sync_directory(root)
        f.sync_directory(root.parent)
        snapshot = f.verified_snapshot(root, manifest)
        if 'keyboard-result.json' in snapshot:
            require(snapshot['keyboard-result.json'] == encoded(analysis), 'keyboard evidence changed')
        require(f.recheck_export(root, boot, snapshot=snapshot)['export']['preservation_complete'] is True,
                'saved RAM log incomplete')
        result['phase'] = 'native-reboot'
        raw, err, process = HOST['invoke'](prepared, 'native-reboot', s.recovery_script(ctx['candidate'], boot))
        request = f.parse_recovery_request(raw, process, boot,
                {'finish_source_sha256': PARENT_SESSION['SOURCE_PINS']['finish-baseline.py']})
        c.write_new(root / 'native-request-result.json', encoded(request))
        result['recovery_requested'] = True
        result['phase'] = 'gemian-return'
        returning = RETURN['watch']({'collector': c, 'finish': f,
            'command': f.known_good_command({'prepared': {'keys': KEYS}}),
            'key': GEMIAN_KEY, 'key_sha256': prepared['credentials'][GEMIAN_KEY],
            'trust': TRUST, 'previous': PREVIOUS, 'mainline': boot,
            'output': root / 'gemian-return',
            'binding': {'runner_sha256': sha(Path(__file__).read_bytes()),
                        'previous_gemian_boot': PREVIOUS, 'mainline_boot': boot}})
        result['return'] = returning
        result['classification'] = ('keyboard-method-pass' if result['keyboard_pass'] and
                                    returning['recovery_confirmed'] else 'keyboard-method-inconclusive')
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result['reason'] = str(error)
    c.write_new(root / 'result.json', encoded(result))
    f.sync_directory(root)
    f.sync_directory(root.parent)
    print(json.dumps(result, sort_keys=True), flush=True)
    return result


def main():
    os.umask(0o077)
    prepared = prepare()
    if '--execute' not in sys.argv:
        print(json.dumps({'classification': 'offline-prepared', 'candidate': CANDIDATE.name,
                          'previous_gemian_boot': PREVIOUS, 'device_action': 'none'}))
        return 0
    require(not OUT.exists(), 'keyboard trial already claimed')
    try:
        prepared['network'].require_ready()
    except ValueError:
        pass
    else:
        raise ValueError('USB route already active before owner selection')
    print('A53 keyboard collector armed; waiting for a new direct USB route.', flush=True)
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        try: status = prepared['network'].require_ready()
        except ValueError:
            time.sleep(1)
            continue
        return 0 if run(prepared, status)['classification'] == 'keyboard-method-pass' else 2
    print('Collector expired without a direct USB route.', flush=True)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
