#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixed host/exact-BusyBox guard fixtures. No target body or device is executed.

The genuine baseline tail is byte-checked before one fixed boundary is replaced
with a sentinel. The exact read exec argv dispatches only a fixture sentinel.
All fixture processes share the existing bounded runner's disposable group.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import signal
import stat
import sys
import tempfile
import threading
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in HERE.parents if (parent / 'AGENTS.md').is_file())
EXPERIMENT = REPO / 'experiments/2026-09-05-owner-away-experiment-preparation'
BUSYBOX_SHA = '52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933'
QEMU_SHA = '4f55e2e88dc05dc0f619562d5795b8eb25ed2ad2547504fb4835207a6911c350'
SOURCE_PINS = {
    'guarded_observation.py': '5fe4472b3ed61812cc05b6662decac89f6799d81de06def4f8bae51cb920317d',
    'baseline/scripts/collect-baseline.py': 'efbca1e464e04005d3b7d503742b426eb9f642140ec289c40bc43563852208cf',
    'baseline/scripts/session_steps.py': '762616bb386647e0a25addd36ad9dba2f6384ebde4858f89a806a32678fc60fc',
    'emmc/test_packet.py': '763ee75fef4ab36204c5ebfbf7b1326dcd66af9d9bf93edbdafa3efd50b32a83',
    'emmc/classify.py': '0be35e88eb3868e515d2185932519d0fb878260eced50f336e6dde301983acc3',
    'historical-observer': 'bfa7b11a355263f181285b12d99a07c1ca71ac6b8f13570730da7783937e9fe4',
}
BOOT = '11111111-2222-3333-4444-555555555555'
CASE_SECONDS = 90
TOTAL_SECONDS = 600
MAX_FIXTURE_BYTES = 2 * 1024 * 1024
OBSERVER_SENTINEL = b"printf '__FIXTURE_OBSERVER_ENTERED__\\n'\n"
HASH_MEMBERS = {'busybox': b'fixture-busybox-member\n', 'emmc-observe': OBSERVER_SENTINEL,
                'kmsg-capture': b'fixture-kmsg-capture-member\n'}
HASH_CASES = [name + '-' + kind for name in HASH_MEMBERS for kind in ('hash-error', 'hash-mismatch')]
TERMINAL_CASES = [name + '-' + kind for name in ('status', 'exit') for kind in ('present', 'directory', 'dangling')]
FILE_CASES = [name + '-' + kind for name in ('log', 'pidfile') for kind in ('missing', 'directory', 'symlink', 'dangling')]
PID_VALUES = {'pid-empty': '', 'pid-zero': '0', 'pid-double-zero': '00', 'pid-leading-zero': '01', 'pid-one': '1',
              'pid-negative': '-2', 'pid-plus': '+2', 'pid-nondigit': '2x', 'pid-space': '2 3',
              'pid-interior-newline': '2\n3', 'pid-eleven-digits': '12345678901'}
REFUSAL_CASES = HASH_CASES + TERMINAL_CASES + FILE_CASES + ['pid-cat-error'] + list(PID_VALUES) + \
                ['held-stat-error', 'expected-stat-error', 'logger-identity-mismatch']
POSITIVE_CASES = ['compose-pre', 'compose-read', 'compose-post', 'pid-ten-digits', 'pid-trailing-newlines']
CONTROL_CASES = ['stdout-cap', 'stderr-cap', 'deadline', 'signal', 'late-signal-refusal']
HOSTILE_CASES = ['hostile-applet', 'hostile-dev', 'hostile-proc', 'hostile-sys', 'hostile-shell', 'hostile-symlink']
EXPECTED_CASES = ['constructor-refusals'] + POSITIVE_CASES + REFUSAL_CASES + CONTROL_CASES + HOSTILE_CASES

PROXY = r'''import hashlib,json,os,pathlib,subprocess,sys,time
def need(value, reason):
    if not value: raise SystemExit('fixture refusal: '+reason)
root=pathlib.Path(__file__).absolute().parent.parent
need(root.name.startswith('gemini-emmc-fixture-') and root.is_dir() and not root.is_symlink(), 'managed root')
need(root.stat().st_mode & 0o077 == 0, 'private root')
config=json.loads((root/'fixture.json').read_bytes())
need(config['root']==str(root), 'root binding')
prefix=config['prefix']
need(type(prefix) is list and len(prefix) in (0,2), 'exact prefix')
args=sys.argv[1:]
need(1<=len(args)<=8 and all(len(value)<=512 for value in args), 'argument count/bound')
applet,*args=args
def confined(value):
    path=pathlib.Path(value)
    need(path.is_absolute() and '..' not in path.parts and path.is_relative_to(root), 'unconfined path')
    need(path.resolve().is_relative_to(root), 'symlink escape')
    return path
def record(name, values):
    path=root/'dispatch-calls.jsonl'
    need(not path.exists() or path.stat().st_size<32768, 'trace bound')
    with path.open('a') as stream:
        stream.write(json.dumps({'applet':name,'args':[value.replace(str(root),'<fixture>') for value in values]})+'\n')
def body(name):
    with (root/'body-calls.jsonl').open('a') as stream: stream.write(json.dumps(name)+'\n')
def ordinary(name, values):
    record('ordinary-'+('exact' if prefix else 'host'), [name])
    if prefix: raise SystemExit(subprocess.call(prefix+[name]+values))
    if name=='sha256sum': print(hashlib.sha256(pathlib.Path(values[0]).read_bytes()).hexdigest()+'  '+values[0])
    elif name=='cat': sys.stdout.buffer.write(pathlib.Path(values[0]).read_bytes())
    elif name=='stat':
        info=pathlib.Path(values[-1]).stat(); print(str(info.st_dev)+':'+str(info.st_ino))
    elif name=='sh': raise SystemExit(subprocess.call(['/bin/sh']+values))
    else: raise SystemExit('fixture refusal: host applet')
    raise SystemExit(0)
record(applet,args)
case=config['case']
if applet=='sha256sum':
    need(len(args)==1, 'hash arguments')
    path=confined(args[0]); name=path.name
    need(path.parent==root/'bin' and name in ('busybox','emmc-observe','kmsg-capture'), 'hash member')
    if case in ('deadline','signal','late-signal-refusal'):
        (root/'stall-ready').write_text('ready\n')
        while True: time.sleep(1)
    if case==name+'-hash-error': raise SystemExit(3)
    selected=root/'hash-members'/('wrong' if case==name+'-hash-mismatch' else name)
    ordinary(applet,[str(selected)])
elif applet=='cat':
    need(args==[str(root/'run/a53/kmsg-pid')], 'PID read arguments')
    confined(args[0])
    if case=='pid-cat-error': raise SystemExit(4)
    ordinary(applet,args)
elif applet=='stat':
    need(len(args)==3 and args[:2]==['-Lc','%d:%i'], 'stat arguments')
    path=confined(args[-1])
    held=root/'proc'/config['pid']/'exe'
    expected=root/'bin/kmsg-capture'
    need(path in (held,expected), 'stat path')
    if (case=='held-stat-error' and path==held) or (case=='expected-stat-error' and path==expected): raise SystemExit(5)
    ordinary(applet,args)
elif applet=='sh':
    need(args==config['read_argv'], 'exact observer argv required')
    for value in args[:1]: confined(value)
    need(hashlib.sha256(pathlib.Path(args[0]).read_bytes()).hexdigest()==config['sentinel_sha256'], 'observer sentinel changed')
    body('read'); ordinary('sh',args)
elif applet=='fixture-baseline':
    need(args==[config['phase']] and config['phase'] in ('pre','post'), 'fixed baseline boundary')
    body(config['phase'])
    if case=='stdout-cap': sys.stdout.buffer.write(b'x'*131073)
    elif case=='stderr-cap': sys.stderr.buffer.write(b'x'*16385)
    else: print('__FIXTURE_BASELINE_ENTERED__')
else: raise SystemExit('fixture refusal: unreviewed applet')
'''


def require(value, reason):
    if not value: raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_path(name):
    if name == 'guarded_observation.py': return HERE / name
    if name == 'historical-observer':
        return REPO / 'experiments/2026-09-04-mt6797-pwrap-reset-serviceability/scripts/remote_observe.sh'
    return EXPERIMENT / name


def check_sources():
    for name, expected in SOURCE_PINS.items():
        path = source_path(name)
        require(path.is_file() and all(not item.is_symlink() for item in (path, *path.parents)), 'source missing/symlink')
        require(sha(path.read_bytes()) == expected, 'fixture source drift: ' + name)


def write(path, raw, executable=False):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(raw)
    path.chmod(0o700 if executable else 0o600)


def configuration(args):
    work = args.work_root.absolute()
    require(work.is_dir() and not work.is_symlink(), 'explicit existing managed work root required')
    work = work.resolve(strict=True)
    require(re.fullmatch(r'[A-Za-z0-9_./-]+', str(work)) and work != Path('/') and
            not any(work.is_relative_to(Path(value)) for value in ('/dev', '/proc', '/sys')), 'unsafe work root')
    require(work.stat().st_uid == os.getuid(), 'work root owner')
    if args.busybox is None:
        require(args.qemu is None, 'emulator requires BusyBox')
        return work, [], None
    binary = args.busybox.resolve(strict=True)
    require(binary.is_file() and sha(binary.read_bytes()) == BUSYBOX_SHA, 'exact retained BusyBox pin')
    found = shutil.which(args.qemu or 'qemu-aarch64-static')
    require(found is not None, 'QEMU executable missing')
    emulator = Path(found).resolve(strict=True)
    require(emulator.is_file() and os.access(emulator, os.X_OK) and sha(emulator.read_bytes()) == QEMU_SHA,
            'retained canonical QEMU identity')
    return work, [str(emulator), str(binary)], QEMU_SHA


def prepared_fixture(C):
    members = {name: {'mode': '0o100755', 'size': 32, 'sha256': sha(name.encode())} for name in C['MEMBERS'].values()}
    for name, raw in HASH_MEMBERS.items(): members['bin/' + name] = {'mode': '0o100755', 'size': len(raw), 'sha256': sha(raw)}
    return {'candidate': {'members': members, 'files': {'boot.img': 'a' * 64, 'boot2-padded.img': 'b' * 64,
                                                       'kernel.config': 'c' * 64}},
            'admission': {'candidate_sha256': 'a' * 64}}


def constructors(G, prepared, baseline, release):
    import copy
    for member in HASH_MEMBERS:
        for value in ('a' * 63, 'A' * 64, 'a' * 64 + '\n', None):
            bad = copy.deepcopy(prepared); bad['candidate']['members']['bin/' + member]['sha256'] = value
            try: G['observer_guard'](bad['candidate'])
            except ValueError: pass
            else: raise ValueError('constructor accepted member digest')
    for phase, boot, body, token in [('other', BOOT, baseline, release), ('read', None, b'', release),
        ('read', BOOT + ';x', b'', release), ('pre', None, 'not bytes', release), ('pre', None, b'', release),
        ('pre', None, baseline, 'kernel;false'), ('pre', None, baseline, 'x' * 129),
        ('pre', None, baseline, 'kernel\n'), ('read', BOOT, b'', None)]:
        try: G['script_for'](prepared, phase, boot, body, token)
        except ValueError: pass
        else: raise ValueError('constructor accepted invalid phase/UUID/body/release')
    bad = copy.deepcopy(prepared); bad['candidate']['files']['boot2-padded.img'] = 'bad'
    try: G['script_for'](bad, 'read', BOOT, b'', release)
    except ValueError: pass
    else: raise ValueError('constructor accepted padded digest')


def make_case(root, name, phase, prefix, G, prepared, baseline, release):
    pid = '9999999999' if name == 'pid-ten-digits' else '2'
    proxy = ('#!' + sys.executable + '\n').encode() + PROXY.encode()
    write(root / 'bin/busybox', proxy, True)
    write(root / 'bin/emmc-observe', OBSERVER_SENTINEL)
    write(root / 'bin/kmsg-capture', HASH_MEMBERS['kmsg-capture'])
    for member, raw in HASH_MEMBERS.items(): write(root / 'hash-members' / member, raw)
    write(root / 'hash-members/wrong', b'intentionally different fixture member\n')
    ram = root / 'run/a53'
    write(ram / 'kmsg.log', b'fixture-only log\n')
    value = PID_VALUES.get(name, pid) + ('\n\n' if name == 'pid-trailing-newlines' else '\n')
    write(ram / 'kmsg-pid', value.encode())
    proc = root / 'proc' / pid / 'exe'; proc.parent.mkdir(mode=0o700, parents=True)
    if name == 'logger-identity-mismatch':
        write(root / 'bin/logger-decoy', b'fixture wrong logger\n'); proc.symlink_to(root / 'bin/logger-decoy')
    else: proc.symlink_to(root / 'bin/kmsg-capture')
    for label, target in [('status', ram / 'kmsg.status'), ('exit', ram / 'kmsg-exit')]:
        if name == label + '-present': write(target, b'fixture terminal\n')
        elif name == label + '-directory': target.mkdir(mode=0o700)
        elif name == label + '-dangling': target.symlink_to(ram / 'absent-terminal')
    for label, target in [('log', ram / 'kmsg.log'), ('pidfile', ram / 'kmsg-pid')]:
        if name.startswith(label + '-') and name in FILE_CASES:
            raw = target.read_bytes(); target.unlink()
            kind = name.removeprefix(label + '-')
            if kind == 'directory': target.mkdir(mode=0o700)
            elif kind == 'symlink': write(ram / 'decoy', raw); target.symlink_to(ram / 'decoy')
            elif kind == 'dangling': target.symlink_to(ram / 'absent-file')
    original = G['script_for'](prepared, phase, BOOT, baseline if phase != 'read' else b'', release)
    guard = G['observer_guard'](prepared['candidate'])
    require(original.startswith(guard) and original.count(guard) == 1, 'exact guard boundary')
    if phase != 'read':
        require(original == guard + baseline, 'genuine baseline tail differs')
        instrumented = guard + ('$BB fixture-baseline ' + phase + '\n').encode()
    else:
        expected = (f'exec /bin/busybox sh /bin/emmc-observe {BOOT} {release} '
                    f'{prepared["candidate"]["files"]["boot2-padded.img"]} {sha(HASH_MEMBERS["busybox"])}\n').encode()
        require(original == guard + expected, 'exact observer exec boundary')
        instrumented = original
    mapped = re.sub(rb'(?<![A-Za-z0-9_/])/(?:bin/busybox|bin/emmc-observe|bin/kmsg-capture|run|proc)(?=[/"\s)]|$)',
                    lambda match: str(root).encode() + match.group(), instrumented)
    require(not re.search(rb'(?<![A-Za-z0-9_/])/(?:dev|proc|sys|run|bin)/', mapped), 'live path remained in executable fixture')
    write(root / 'original.sh', original)
    write(root / 'phase.sh', mapped)
    config = {'root': str(root), 'case': name, 'phase': phase, 'prefix': prefix, 'pid': pid,
              'read_argv': [str(root / 'bin/emmc-observe'), BOOT, release,
                            prepared['candidate']['files']['boot2-padded.img'], sha(HASH_MEMBERS['busybox'])],
              'sentinel_sha256': sha(OBSERVER_SENTINEL)}
    write(root / 'fixture.json', json.dumps(config, sort_keys=True).encode())
    return {'guard_sha256': sha(guard), 'original_sha256': sha(original),
            'baseline_tail_sha256': sha(baseline) if phase != 'read' else None}


def run_suite(work, prefix, emulator_sha):
    check_sources()
    G = runpy.run_path(str(source_path('guarded_observation.py')))
    C = runpy.run_path(str(source_path('baseline/scripts/collect-baseline.py')))
    S = runpy.run_path(str(source_path('baseline/scripts/session_steps.py')))
    runner = runpy.run_path(str(source_path('emmc/test_packet.py')))
    prepared = prepared_fixture(C)
    baseline = C['remote_script'](prepared)
    constructors(G, prepared, baseline, S['RELEASE'])
    started = time.monotonic(); deadline = started + TOTAL_SECONDS
    completed = ['constructor-refusals']; programs = {}
    shell = [*prefix, 'sh'] if prefix else ['/bin/sh']
    for name in EXPECTED_CASES[1:]:
        require(time.monotonic() < deadline - 2, 'suite total deadline')
        case_deadline = min(time.monotonic() + CASE_SECONDS, deadline)
        def remaining():
            allowance = case_deadline - time.monotonic() - runner['FIXTURE_CLEANUP_SECONDS']
            require(allowance > 0, 'case/suite deadline exhausted')
            return allowance
        phase = name.removeprefix('compose-') if name.startswith('compose-') else \
                'pre' if name in ('stdout-cap', 'stderr-cap') else 'read'
        with tempfile.TemporaryDirectory(prefix='gemini-emmc-fixture-', dir=work) as temporary:
            root = Path(temporary).resolve()
            identities = make_case(root, name, phase, prefix, G, prepared, baseline, S['RELEASE'])
            environment = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'EMMC_FIXTURE_ROOT': str(root)}
            if name.startswith('compose-'):
                syntax = runner['bounded_process']([*shell, '-n', str(root / 'original.sh')], environment, remaining())
                require(syntax.returncode == 0 and not syntax.stdout and not syntax.stderr, 'combined exact shell syntax')
                programs[phase] = identities
            command = [*shell, str(root / 'phase.sh')]
            if name in HOSTILE_CASES:
                hostile = {'hostile-applet': ['mount'], 'hostile-dev': ['sha256sum', '/dev/mmcblk0'],
                           'hostile-proc': ['cat', '/proc/self/stat'], 'hostile-sys': ['stat', '-Lc', '%d:%i', '/sys'],
                           'hostile-shell': ['sh', '-c', 'exit 0']}
                if name == 'hostile-symlink':
                    (root / 'escape').symlink_to(root.parent / 'absent-outside-fixture')
                    values = ['sha256sum', str(root / 'escape/member')]
                else: values = hostile[name]
                command = [sys.executable, '-O', str(root / 'bin/busybox'), *values]
            stopped = threading.Event(); runner_done = threading.Event()
            thread = None; sent = []; late_signals = []; outer_handler = None
            if name in ('signal', 'late-signal-refusal'):
                # bounded_process temporarily installs its own handler, then
                # restores this scoped guard. Keep it installed until the sole
                # self-signal helper has definitely finished, including a late
                # delivery after bounded_process has restored its handlers.
                outer_handler = signal.signal(signal.SIGTERM, lambda number, _frame: late_signals.append(number))
                def interrupt():
                    until = min(case_deadline, time.monotonic() + 8)
                    while not stopped.wait(0.01) and time.monotonic() < until:
                        if (root / 'stall-ready').exists():
                            if name == 'late-signal-refusal' and not runner_done.wait(max(0, until - time.monotonic())):
                                return
                            sent.append(True); os.kill(os.getpid(), signal.SIGTERM); return
                thread = threading.Thread(target=interrupt, daemon=True); thread.start()
            try:
                cap = remaining()
                special_cap = min(cap, 5 if prefix else 2) if name in ('deadline', 'signal', 'late-signal-refusal') else cap
                result = runner['bounded_process'](command, environment, special_cap)
                require(name not in CONTROL_CASES, 'bounded runner missed requested stop')
                bodies = [json.loads(line) for line in (root / 'body-calls.jsonl').read_text().splitlines()] \
                         if (root / 'body-calls.jsonl').exists() else []
                if name in POSITIVE_CASES:
                    expected_output = '__FIXTURE_OBSERVER_ENTERED__\n' if phase == 'read' else '__FIXTURE_BASELINE_ENTERED__\n'
                    require(result.returncode == 0 and result.stdout == expected_output and not result.stderr and
                            bodies == [phase], 'positive dispatch must enter exactly one fixed body')
                    calls = [json.loads(line) for line in (root / 'dispatch-calls.jsonl').read_text().splitlines()]
                    ordinary = [item['args'][0] for item in calls if item['applet'] == 'ordinary-' + ('exact' if prefix else 'host')]
                    require(ordinary[:6] == ['sha256sum'] * 3 + ['cat', 'stat', 'stat'], 'guard applet order/mode')
                    require(all(item['applet'] != 'ordinary-host' for item in calls) if prefix else True, 'host applet in exact mode')
                else:
                    require(result.returncode != 0 and not bodies and not result.stdout, 'refusal entered phase body')
                    if name in HOSTILE_CASES: require('fixture refusal:' in result.stderr, 'hostile proxy did not refuse')
            except runner['FixtureRunError'] as error:
                expected = {'stdout-cap': 'stdout-limit', 'stderr-cap': 'stderr-limit',
                            'deadline': 'fixture-timeout', 'signal': 'fixture-interrupted-' + str(signal.SIGTERM),
                            'late-signal-refusal': 'fixture-timeout'}
                require(name in expected and error.diagnostic['reason'] == expected[name], 'unexpected fixture runner failure: ' + str(error))
                if name == 'signal': require(sent == [True], 'signal fixture was not delivered')
                require(error.diagnostic['captured_bytes']['stdout'] <= 131072 and
                        error.diagnostic['captured_bytes']['stderr'] <= 16384, 'runner stream ceiling')
                if name in ('deadline', 'signal', 'late-signal-refusal'):
                    require(not (root / 'body-calls.jsonl').exists(), 'stopped guard entered body')
            finally:
                runner_done.set()
                stopped.set()
                if thread:
                    thread.join(timeout=1)
                    # On a join failure, retain the scoped handler until this
                    # dedicated fixture process exits with failure. Restoring
                    # default handling while a sender survives would be unsafe.
                    require(not thread.is_alive(), 'self-signal helper did not join')
                    signal.signal(signal.SIGTERM, outer_handler)
            if name == 'late-signal-refusal':
                require(sent == [True] and late_signals == [signal.SIGTERM], 'late signal was not safely refused')
            else:
                require(not late_signals, 'late or unattributable signal cannot pass a control')
            require(sum(path.stat().st_size for path in root.rglob('*') if path.is_file() and not path.is_symlink()) <= MAX_FIXTURE_BYTES,
                    'fixture storage bound')
        require(time.monotonic() <= case_deadline, 'case deadline exceeded including directory cleanup')
        completed.append(name)
    require(completed == EXPECTED_CASES, 'fixture inventory incomplete')
    check_sources()
    if prefix:
        require(sha(Path(prefix[1]).read_bytes()) == BUSYBOX_SHA and
                sha(Path(prefix[0]).read_bytes()) == emulator_sha == QEMU_SHA,
                'exact executables changed')
    elapsed = time.monotonic() - started
    require(elapsed <= TOTAL_SECONDS, 'suite deadline exceeded')
    return {'schema': 1, 'classification': 'emmc-guard-shell-fixtures-pass', 'mode': 'exact-busybox-qemu' if prefix else 'host',
            'case_count': len(completed), 'cases': completed, 'source_sha256': SOURCE_PINS,
            'busybox_sha256': BUSYBOX_SHA if prefix else None, 'qemu_sha256': emulator_sha,
            'case_timeout_seconds': CASE_SECONDS, 'suite_timeout_seconds': TOTAL_SECONDS,
            'cleanup_seconds': runner['FIXTURE_CLEANUP_SECONDS'], 'elapsed_seconds': round(elapsed, 3),
            'programs': programs, 'target_bodies_executed': False, 'device_access': False,
            'claim': 'guard-before-fixed-body-and-exact-dispatch-only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-root', type=Path, required=True)
    parser.add_argument('--busybox', type=Path)
    parser.add_argument('--qemu')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        work, prefix, emulator_sha = configuration(args)
        result = run_suite(work, prefix, emulator_sha)
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {'classification': 'emmc-guard-shell-fixtures-failed', 'reason': str(error)}
        print(json.dumps(result, sort_keys=True)); return 2
    print(json.dumps(result, sort_keys=True)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
