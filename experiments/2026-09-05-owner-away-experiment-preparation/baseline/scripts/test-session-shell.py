#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixed generated-session shell fixtures; every target effect is intercepted.

Defaults to host /bin/sh. --busybox FILE --qemu PROGRAM uses the exact static
ARM64 BusyBox instead. No target kill, reboot, mount or network call can execute.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
S = runpy.run_path(str(HERE / 'session_steps.py'))
BOOT = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
PINS = {'seal': '0dd2822ae10990b5b2d7fe888a6ea8114e334aa35438137beb8ef6e34d679005',
        'recovery': '2228aff8c2f4d12816fd813debc3fc2c8dd8f4dc36a88814db54d958c07d0266'}
COMMON_CASES = ['good', 'boot-mismatch', 'kernel-mismatch', 'cpu-mismatch', 'member-mismatch',
                'swap-active', 'persistent-run', 'persistent-root', 'duplicate-run', 'duplicate-root',
                'a53-submount', 'log-submount', 'run-symlink', 'a53-symlink', 'mode-mismatch',
                'owner-mismatch', 'existing-claim']
SEAL_CASES = ['existing-status', 'existing-exit', 'dangling-status', 'dangling-exit',
              'preexited-failure', 'preexited-deadline', 'preexited-partial', 'preexited-cap', 'preexited-gap',
              'preexited-malformed-exit', 'late-terminal', 'helper-refusal', 'exit-timeout', 'logger-failed',
              'partial-status', 'dangling-partial', 'exit-symlink', 'missing-status',
              'status-symlink', 'log-symlink', 'log-replaced', 'log-vanished', 'oversize-log',
              'empty-log', 'failed-status', 'oversize-status', 'read-failed']
EXPECTED_CASES = ['seal:' + case for case in COMMON_CASES + SEAL_CASES] + ['recovery:' + case for case in COMMON_CASES]
# Exact emulation measured 14.596 seconds for healthy seal (68 safe calls).
# This harness-only ceiling does not alter the target's 30-second export budget.
CASE_TIMEOUT_SECONDS = 45
CLEANUP_SECONDS = 1
STREAM_LIMITS = {'stdout': 3 * 1024 * 1024, 'stderr': 16384}
PROXY = r'''
import base64,json,os,pathlib,subprocess,sys,textwrap
def require(value, reason):
    if not value: raise SystemExit(reason)
root=pathlib.Path(__file__).parent
c=json.loads((root/'fixture.json').read_text())
name=pathlib.Path(sys.argv[0]).name
args=sys.argv[1:]
with (root/'calls.jsonl').open('a') as stream:
    stream.write(json.dumps({'name':name,'args':args})+'\n')
case=c['case']
ram=root/'run/a53'
if name=='helper-reboot':
    raise SystemExit(0)
if name=='helper-kmsg-seal':
    require((ram/'log-seal-attempt').is_dir(), 'claim missing before signal helper')
    if case=='helper-refusal': raise SystemExit(1)
    if case in ('exit-timeout','late-terminal'): raise SystemExit(0)
    (ram/'kmsg-exit').write_text('1\n' if case=='logger-failed' else '0\n')
    if case=='exit-symlink':
        (ram/'kmsg-exit').rename(ram/'exit-copy')
        (ram/'kmsg-exit').symlink_to('exit-copy')
    if case!='partial-status': (ram/'kmsg.status.partial').unlink(missing_ok=True)
    if case=='dangling-partial': (ram/'kmsg.status.partial').symlink_to('missing-partial')
    if case=='missing-status': raise SystemExit(0)
    status=(root/'expected-status').read_bytes()
    if case=='failed-status': status=status.replace(b'result=pass',b'result=failed')
    if case=='oversize-status': status=b'x'*8193
    if case=='status-symlink':
        (ram/'status-copy').write_bytes(status)
        (ram/'kmsg.status').symlink_to('status-copy')
    else: (ram/'kmsg.status').write_bytes(status)
    if case=='log-symlink':
        (ram/'kmsg.log').rename(ram/'log-copy')
        (ram/'kmsg.log').symlink_to('log-copy')
    raise SystemExit(0)
require(name=='bb-proxy', 'unreviewed helper refused')
applet,*args=args
if applet=='uname':
    print('wrong-kernel' if case=='kernel-mismatch' else c['release'])
elif applet=='sha256sum':
    value=c['hashes'].get(args[0])
    require(value, 'unreviewed hash path')
    print(('0'*64 if case=='member-mismatch' else value)+'  '+args[0])
elif applet=='stat':
    if len(args)==3 and args[:2]==['-c','%u:%g:%a'] and args[2] in (str(root/'run'),str(ram)):
        print('0:0:755' if case=='mode-mismatch' else '1:0:700' if case=='owner-mismatch' else '0:0:700')
    else:
        require(len(args)==3 and args[0] in ('-c','-Lc') and args[1] in ('%d:%i','%s') and
                (args[2]==c['fd_path'] or args[2].startswith(str(ram)+'/')), 'unreviewed stat path/arguments')
        if case=='late-terminal' and args==['-c','%d:%i',str(ram/'kmsg.log')]:
            (ram/'kmsg-exit').write_text('0\n')
            (ram/'kmsg.status').write_bytes((root/'expected-status').read_bytes())
            (ram/'kmsg.status.partial').unlink(missing_ok=True)
        if case in ('log-replaced','log-vanished') and args==['-c','%d:%i',str(ram/'kmsg.log')] and not (root/'replaced').exists():
            st=(ram/'kmsg.log').lstat()
            (ram/'kmsg.log').rename(ram/'original-log')
            if case=='log-replaced':
                (ram/'decoy').write_bytes(b'NEVER EXPORT THIS REPLACEMENT\n')
                (ram/'kmsg.log').symlink_to('decoy')
            (root/'replaced').write_text('yes\n')
            print(str(st.st_dev)+':'+str(st.st_ino))
            raise SystemExit(0)
        if c['busybox']:
            raise SystemExit(subprocess.call(c['runner']+['stat']+args,
                                             pass_fds=(3,) if args[2]==c['fd_path'] else ()))
        st=os.fstat(3) if args[2]==c['fd_path'] else pathlib.Path(args[2]).lstat()
        print(str(st.st_size) if args[1]=='%s' else str(st.st_dev)+':'+str(st.st_ino))
elif applet=='sleep':
    require(args==['1'], 'unreviewed sleep arguments')
elif applet=='base64' and not c['busybox']:
    require(args in ([],['-d']), 'unreviewed base64 arguments')
    data=sys.stdin.buffer.read(2097153)
    require(len(data)<=2097152, 'base64 input bound')
    sys.stdout.buffer.write(base64.b64decode(data,validate=True) if args else base64.encodebytes(data))
elif applet in ('cat','awk','mkdir','wc','printf','base64','head'):
    if applet=='head':
        require(args in (['-c','5'],['-c','8192'],['-c','2097152']), 'unreviewed head arguments')
        if case=='read-failed':
            sys.stdout.buffer.write(sys.stdin.buffer.read(7))
            raise SystemExit(1)
    if applet=='base64': require(args in ([],['-d']), 'unreviewed base64 arguments')
    for arg in args:
        if arg.startswith('/'):
            require(arg.startswith(str(root)+'/'), 'absolute path escaped fixture')
    if c['busybox']:
        command=c['runner']+[applet]+args
    else:
        executable={'cat':'/bin/cat','awk':'/usr/bin/awk','mkdir':'/bin/mkdir','wc':'/usr/bin/wc',
                    'printf':'/usr/bin/printf','head':'/usr/bin/head'}[applet]
        command=[executable]+args
    raise SystemExit(subprocess.call(command))
else:
    raise SystemExit('unreviewed applet, including direct kill, refused')
'''


def require(value, reason):
    if not value:
        raise ValueError(reason)


class FixtureExecutionError(ValueError):
    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
        super().__init__(json.dumps(diagnostic, sort_keys=True))


def fixture_diagnostic(root, phase, case, reason, process, buffers, started):
    recent = []
    path = root / 'calls.jsonl'
    if path.is_file() and not path.is_symlink():
        with path.open('rb') as stream:
            size = stream.seek(0, os.SEEK_END)
            stream.seek(max(0, size - 8192))
            raw = stream.read(8192)
        lines = raw.splitlines()
        if size > 8192:
            lines = lines[1:]
        recent = [line[-1024:].decode('utf-8', errors='backslashreplace') for line in lines[-8:]]
    return {'classification': 'session-shell-fixture-failed', 'phase': phase, 'case': case,
            'reason': reason, 'elapsed_seconds': round(time.monotonic() - started, 3),
            'return_code': process.returncode if process else None,
            'captured_bytes': {name: len(data) for name, data in buffers.items()},
            'stdout_tail': bytes(buffers['stdout'][-4096:]).decode('utf-8', errors='backslashreplace'),
            'stderr_tail': bytes(buffers['stderr'][-4096:]).decode('utf-8', errors='backslashreplace'),
            'recent_calls': recent, 'cleanup_budget_seconds': CLEANUP_SECONDS}


def run_fixture(command, root, phase, case, timeout=CASE_TIMEOUT_SECONDS, env=None):
    """Capture bounded fixture output; stop its isolated group on every exit."""
    started = time.monotonic()
    deadline = started + timeout
    buffers = {name: bytearray() for name in STREAM_LIMITS}
    selector = selectors.DefaultSelector()
    process, reason = None, None
    interrupted, handlers = [], {}

    def drain(wait):
        nonlocal reason
        for key, _event in selector.select(wait):
            try:
                data = os.read(key.fileobj.fileno(), 65536)
            except BlockingIOError:
                continue
            if not data:
                selector.unregister(key.fileobj)
                key.fileobj.close()
                continue
            name = key.data
            available = STREAM_LIMITS[name] - len(buffers[name])
            buffers[name].extend(data[:available])
            if len(data) > available:
                reason = reason or name + '-limit'

    def signal_group(number):
        if process is not None:
            try:
                os.killpg(process.pid, number)
            except ProcessLookupError:
                pass

    try:
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            handlers[number] = signal.signal(number, lambda received, _frame: interrupted.append(received))
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True, env=env)
        for name in STREAM_LIMITS:
            stream = getattr(process, name)
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map() or process.poll() is None:
            if interrupted:
                reason = 'interrupted-' + str(interrupted[0])
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                reason = 'fixture-timeout'
                break
            drain(min(0.05, remaining))
            if reason:
                break
    finally:
        # A leader can exit while a descendant keeps a pipe open, or close all
        # pipes while leaving a background process. Clean the whole new group.
        cleanup_deadline = time.monotonic() + CLEANUP_SECONDS
        signal_group(signal.SIGTERM)
        grace = min(cleanup_deadline, time.monotonic() + 0.2)
        while process is not None and time.monotonic() < grace:
            if selector.get_map():
                drain(min(0.02, max(0, grace - time.monotonic())))
            else:
                time.sleep(min(0.01, max(0, grace - time.monotonic())))
        if process is not None:
            process.poll()  # Reap an exited leader before signalling remaining group members.
        signal_group(signal.SIGKILL)
        if process is not None:
            try:
                process.wait(timeout=max(0.01, cleanup_deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                reason = reason or 'fixture-cleanup-timeout'
            while selector.get_map() and time.monotonic() < cleanup_deadline:
                drain(min(0.02, max(0, cleanup_deadline - time.monotonic())))
            for name in STREAM_LIMITS:
                stream = getattr(process, name)
                if stream and not stream.closed:
                    stream.close()
        selector.close()
        for number, previous in handlers.items():
            signal.signal(number, previous)
    if interrupted:
        reason = reason or 'interrupted-' + str(interrupted[0])
    if reason:
        raise FixtureExecutionError(fixture_diagnostic(root, phase, case, reason, process, buffers, started))
    return subprocess.CompletedProcess(command, process.returncode, bytes(buffers['stdout']), bytes(buffers['stderr']))


def runner_checks(root):
    """Real disposable process fixtures; never launch target/device operations."""
    root.mkdir(mode=0o700)
    cases = 0
    result = run_fixture([sys.executable, '-c', 'import sys; print("normal"); print("stderr",file=sys.stderr)'],
                         root, 'runner', 'normal', timeout=2)
    require(result.returncode == 0 and result.stdout == b'normal\n' and result.stderr == b'stderr\n', 'runner normal capture')
    cases += 1
    (root / 'calls.jsonl').write_text(''.join(json.dumps({'fixture_call': n}) + '\n' for n in range(2000)))
    for name, source, expected in (
        ('timeout', 'import time; print("before-timeout",flush=True); time.sleep(10)', 'fixture-timeout'),
        ('stdout-limit', 'import os; os.write(1,b"x"*(4*1024*1024))', 'stdout-limit'),
        ('stderr-limit', 'import os; os.write(2,b"x"*32768)', 'stderr-limit')):
        started = time.monotonic()
        try:
            run_fixture([sys.executable, '-c', source], root, 'runner', name, timeout=0.4 if name == 'timeout' else 2)
        except FixtureExecutionError as error:
            diagnostic = error.diagnostic
            require(diagnostic['phase'] == 'runner' and diagnostic['case'] == name and
                    diagnostic['reason'] == expected and len(diagnostic['recent_calls']) == 8 and
                    len(diagnostic['stdout_tail']) <= 4096 and len(diagnostic['stderr_tail']) <= 4096 and
                    all(diagnostic['captured_bytes'][stream] <= ceiling for stream, ceiling in STREAM_LIMITS.items()) and
                    time.monotonic() - started < 3.5, 'runner bounded failure diagnostic')
            if name == 'timeout':
                require('before-timeout' in diagnostic['stdout_tail'], 'timeout lost partial output')
        else:
            raise ValueError('runner accepted ' + name)
        cases += 1
    markers = []
    for keep_pipe in (True, False):
        marker = root / ('child-linger-' + str(keep_pipe))
        markers.append(marker)
        child = ('import os,signal,time; from pathlib import Path; signal.signal(signal.SIGTERM,signal.SIG_IGN); '
                 + ('' if keep_pipe else 'os.close(1); os.close(2); ') +
                 'time.sleep(1.4); Path(' + repr(str(marker)) + ').write_text("lingered"); time.sleep(10)')
        parent = 'import subprocess,sys; subprocess.Popen([sys.executable,"-c",' + repr(child) + '])'
        try:
            run_fixture([sys.executable, '-c', parent], root, 'runner', 'descendant-' + str(keep_pipe), timeout=0.4)
        except FixtureExecutionError as error:
            require(keep_pipe and error.diagnostic['reason'] == 'fixture-timeout', 'descendant timeout framing')
        else:
            require(not keep_pipe, 'pipe-holding descendant escaped timeout')
        cases += 1
    time.sleep(1.5)
    require(not any(marker.exists() for marker in markers), 'fixture descendant survived group cleanup')
    real_sleep = time.sleep
    injected = False
    def interrupt_after_eof(seconds):
        nonlocal injected
        if not injected:
            injected = True
            os.kill(os.getpid(), signal.SIGTERM)
        real_sleep(seconds)
    time.sleep = interrupt_after_eof
    try:
        try:
            run_fixture([sys.executable, '-c', 'print("EOF",flush=True)'], root, 'runner', 'signal-after-eof', timeout=2)
        except FixtureExecutionError as error:
            require(injected and error.diagnostic['reason'] == 'interrupted-' + str(signal.SIGTERM) and
                    'EOF' in error.diagnostic['stdout_tail'], 'post-EOF signal accepted')
        else:
            raise ValueError('post-EOF signal ignored during cleanup')
    finally:
        time.sleep = real_sleep
    cases += 1
    return cases


def candidate():
    result = {'members': {name: {'sha256': hashlib.sha256(name.encode()).hexdigest()} for name in
                         ('init', 'bin/busybox', 'bin/reboot', 'bin/kmsg-capture', 'bin/kmsg-seal')}}
    result['members']['bin/reboot']['sha256'] = S['REBOOT_SHA']
    return result


def fixture(root, phase, case, script, runner, exact):
    root.mkdir(mode=0o700)
    for name in ('run/a53', 'proc/sys/kernel/random', 'sys/devices/system/cpu'):
        (root / name).mkdir(parents=True, mode=0o700)
    (root / 'run/a53/boot-id').write_text(BOOT + '\n')
    (root / 'proc/sys/kernel/random/boot_id').write_text(
        '00000000-0000-0000-0000-000000000000\n' if case == 'boot-mismatch' else BOOT + '\n')
    for name, value in (('online', '0-7'), ('offline', '8-9'), ('possible', '0-9'), ('present', '0-9')):
        (root / 'sys/devices/system/cpu' / name).write_text(
            '0-9\n' if case == 'cpu-mismatch' and name == 'online' else value + '\n')
    (root / 'proc/swaps').write_text('Filename Type Size Used Priority\n' +
                                   ('fixture partition 1 0 -2\n' if case == 'swap-active' else ''))
    run_mount = str(root / 'run')
    mounts = 'rootfs / ' + ('ext4' if case == 'persistent-root' else 'rootfs') + ' rw 0 0\n'
    mounts += 'tmpfs ' + run_mount + ' ' + ('ext4' if case == 'persistent-run' else 'tmpfs') + ' rw 0 0\n'
    if case == 'duplicate-run':
        mounts += 'overmount ' + run_mount + ' ext4 rw 0 0\n'
    if case == 'duplicate-root':
        mounts += 'overmount / ext4 rw 0 0\n'
    if case == 'a53-submount':
        mounts += 'submount ' + run_mount + '/a53 ext4 rw 0 0\n'
    if case == 'log-submount':
        mounts += 'submount ' + run_mount + '/a53/kmsg.log ext4 rw 0 0\n'
    (root / 'proc/mounts').write_text(mounts)
    ram = root / 'run/a53'
    log = b'6,0,1,-;fixture first record\n6,1,2,-;fixture second record\n'
    if case == 'oversize-log':
        log = b'x' * (S['LIMIT'] + 1)
    if case == 'preexited-cap':
        log = b'x' * S['LIMIT']
    if case == 'preexited-gap':
        log = log.replace(b'6,1,2,', b'6,3,2,')
    if case == 'empty-log':
        log = b''
    (ram / 'kmsg.log').write_bytes(log)
    (ram / 'kmsg.status.partial').write_bytes(b'')
    (ram / 'kmsg-pid').write_text('42\n')
    status = ('schema=gemini-kmsg-v1\nsealed=yes\nresult=pass\nreason=sealed-on-sigterm\n'
              'first_seq=0\nlast_seq=1\nrecords=2\nbytes=' + str(len(log)) + '\n'
              'elapsed_ms=100\nbyte_limit=2097152\ndeadline_ms=600000\n').encode()
    (root / 'expected-status').write_bytes(status)
    if case == 'existing-status':
        (ram / 'kmsg.status').write_bytes(status)
    if case == 'existing-exit':
        (ram / 'kmsg-exit').write_text('0\n')
    if case.startswith('preexited-'):
        (ram / 'kmsg-exit').write_text('1\n')
        if case == 'preexited-malformed-exit':
            (ram / 'kmsg-exit').write_bytes(b'0\0')
        status = status.replace(b'result=pass', b'result=failed')
        reason = {'preexited-deadline': 'deadline-expired', 'preexited-cap': 'byte-limit',
                  'preexited-gap': 'sequence-gap'}.get(case, 'ring-overrun')
        status = status.replace(b'reason=sealed-on-sigterm', b'reason=' + reason.encode())
        if case == 'preexited-partial':
            (ram / 'kmsg.status.partial').write_bytes(status)
        else:
            (ram / 'kmsg.status.partial').unlink()
            (ram / 'kmsg.status').write_bytes(status)
    if case == 'dangling-status':
        (ram / 'kmsg.status').symlink_to('missing-status')
    if case == 'dangling-exit':
        (ram / 'kmsg-exit').symlink_to('missing-exit')
    if case == 'existing-claim':
        (ram / ('log-seal-attempt' if phase == 'seal' else 'native-recovery-attempt')).mkdir()
    fd_path = '/proc/self/fd/3' if Path('/proc/self/fd').is_dir() else '/dev/fd/3'
    paths = {'/bin/busybox': str(root / 'bb-proxy'), '/bin/reboot': str(root / 'helper-reboot'),
             '/bin/kmsg-seal': str(root / 'helper-kmsg-seal'), '/bin/kmsg-capture': str(root / 'logger-file'),
             '/init': str(root / 'init-file'), '/proc/self/fd/3': fd_path, '/proc/': str(root / 'proc') + '/',
             '/sys/': str(root / 'sys') + '/', '/run': str(root / 'run')}
    pattern = re.compile('|'.join(re.escape(path) for path in sorted(paths, key=len, reverse=True)))
    transformed = pattern.sub(lambda match: paths[match[0]], script.decode())
    # Source pins above are the authority for this exact transformation set.
    hashes = {paths['/' + name]: value['sha256'] for name, value in candidate()['members'].items()}
    config = {'case': case, 'release': S['RELEASE'], 'hashes': hashes, 'runner': runner, 'busybox': exact, 'fd_path': fd_path}
    (root / 'fixture.json').write_text(json.dumps(config))
    for name in ('bb-proxy', 'helper-reboot', 'helper-kmsg-seal'):
        path = root / name
        path.write_text('#!' + sys.executable + '\n' + PROXY)
        path.chmod(0o700)
    if case == 'run-symlink':
        (root / 'run').rename(root / 'run-real')
        (root / 'run').symlink_to('run-real')
    if case == 'a53-symlink':
        ram.rename(root / 'run/a53-real')
        ram.symlink_to('a53-real')
    path = root / 'script.sh'
    path.write_text(transformed)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-root', type=Path, default=Path(tempfile.gettempdir()).resolve())
    parser.add_argument('--busybox', type=Path)
    parser.add_argument('--qemu', default='qemu-aarch64-static')
    args = parser.parse_args()
    work_root = args.work_root.resolve(strict=True)
    require(not any(char.isspace() or char in "'\"$`\\" for char in str(work_root)), 'unsupported work-root characters')
    scripts = {'seal': S['seal_script'](candidate(), BOOT), 'recovery': S['recovery_script'](candidate(), BOOT)}
    for phase, script in scripts.items():
        require(hashlib.sha256(script).hexdigest() == PINS[phase], 'generated effect source changed: ' + phase)
        require(b'$BB kill ' not in script and b'kill -' not in script, 'direct numeric signal forbidden')
    exact = args.busybox is not None
    busybox_sha256 = None
    runner = []
    if exact:
        require(args.busybox.is_file() and not args.busybox.is_symlink(), 'BusyBox must be regular')
        binary = args.busybox.read_bytes()
        busybox_sha256 = hashlib.sha256(binary).hexdigest()
        require(binary[:6] == b'\x7fELF\x02\x01' and binary[18:20] == b'\xb7\x00', 'ARM64 BusyBox required')
        qemu = shutil.which(args.qemu)
        require(qemu is not None, 'QEMU missing; exact shell not tested')
        runner = [qemu, str(args.busybox.resolve())]
        inventory = run_fixture(runner + ['--list'], HERE, 'inventory', 'busybox-applet-list', timeout=5)
        require(inventory.returncode == 0 and not inventory.stderr, 'BusyBox applet inventory failed')
        require({'sh', 'stat', 'awk', 'cat', 'mkdir', 'sha256sum', 'uname', 'sleep', 'wc', 'base64', 'printf', 'head'} <=
                set(inventory.stdout.decode().splitlines()), 'required applet missing')
    results = []
    with tempfile.TemporaryDirectory(prefix='a53-session-shell-', dir=work_root) as work:
        base = Path(work)
        runner_test_cases = runner_checks(base / 'runner-checks')
        guard_root = base / 'effect-guards'
        fixture(guard_root, 'seal', 'good', scripts['seal'], runner, exact)
        guard_cases = [('bb-proxy', ['kill', '-TERM', '1'], b'unreviewed applet'),
                       ('bb-proxy', ['cat', '/outside-a53-fixture-do-not-read'], b'absolute path escaped fixture'),
                       ('bb-proxy', ['sleep', '9'], b'unreviewed sleep arguments'),
                       ('bb-proxy', ['stat', '-c', '%u:%g:%a', '/outside-a53-fixture'], b'unreviewed stat'),
                       ('helper-kmsg-seal', [], b'claim missing before signal helper')]
        for optimization in ('0', '1'):
            for name, arguments, diagnostic in guard_cases:
                process = run_fixture([str(guard_root / name)] + arguments, guard_root, 'effect-guard',
                                      name + '-opt' + optimization, timeout=5,
                                      env={**os.environ, 'PYTHONOPTIMIZE': optimization})
                require(process.returncode != 0 and diagnostic in process.stderr and not process.stdout,
                        'effect guard disabled at Python optimization ' + optimization)
        for phase, script in scripts.items():
            for case in COMMON_CASES + (SEAL_CASES if phase == 'seal' else []):
                root = base / (phase + '-' + case)
                path = fixture(root, phase, case, script, runner, exact)
                command = runner + ['sh', str(path)] if exact else ['/bin/sh', str(path)]
                process = run_fixture(command, root, phase, case)
                calls_file = root / 'calls.jsonl'
                calls = [json.loads(line) for line in calls_file.read_text().splitlines()] if calls_file.exists() else []
                effects = [call for call in calls if call['name'] in ('helper-reboot', 'helper-kmsg-seal')]
                expected_effect = 'helper-kmsg-seal' if phase == 'seal' else 'helper-reboot'
                if case == 'good':
                    require([call['name'] for call in effects] == [expected_effect], phase + ' good effect count')
                    if phase == 'seal':
                        require(process.returncode == 0, 'positive seal shell failed')
                        S['parse_seal'](process.stdout, process.stderr,
                                        {'exit_status': 0, 'reason': None, 'stdin_complete': True})
                        for altered in ({'exit_status': 255, 'reason': None, 'stdin_complete': True},
                                        {'exit_status': 0, 'reason': 'outer-timeout', 'stdin_complete': True},
                                        {'exit_status': 0, 'reason': None, 'stdin_complete': False}):
                            rejected = S['parse_log_export'](process.stdout, b'', altered)
                            require(rejected['files']['kmsg.log'] and not rejected['result']['preservation_complete'] and
                                    rejected['result']['classification'] == 'log-export-inconclusive', 'transport failure promoted/lost data')
                        partial = process.stdout.split(b'__A53_LOG_FILE_END__\n', 1)[0] + b'__A53_LOG_FILE_END__\n'
                        rejected = S['parse_log_export'](partial, b'', {'exit_status': 255, 'reason': None, 'stdin_complete': True})
                        require(rejected['files']['kmsg.log'] and not rejected['result']['export_complete'] and
                                not rejected['result']['preservation_complete'], 'partial transport lost completed log block')
                    else:
                        require(process.returncode == 94 and process.stdout.endswith(b'__A53_NATIVE_RECOVERY_END__\n'),
                                'native helper return must remain a failure (94)')
                elif case in COMMON_CASES:
                    require(process.returncode != 0 and not effects, phase + ' guard did not refuse: ' + case)
                    if case in COMMON_CASES and case != 'existing-claim':
                        claim = root / 'run/a53' / ('log-seal-attempt' if phase == 'seal' else 'native-recovery-attempt')
                        require(not claim.exists(), phase + ' guard consumed remote claim: ' + case)
                else:
                    terminal_before = case.startswith('preexited-') or case in (
                        'existing-status', 'existing-exit', 'dangling-status', 'dangling-exit')
                    require([call['name'] for call in effects] == ([] if terminal_before else ['helper-kmsg-seal']),
                            'terminal logger signalled/helper retry: ' + case)
                    exported = S['parse_log_export'](process.stdout, process.stderr,
                                                   {'exit_status': process.returncode, 'reason': None, 'stdin_complete': True})
                    require(process.returncode == 0 and exported['result']['export_complete'],
                            'failed logger evidence export incomplete: ' + case + ': ' + str(exported['result']))
                    require(exported['result']['classification'] == 'log-export-inconclusive', 'failed logger promoted: ' + case)
                    if case not in ('log-symlink', 'log-replaced', 'log-vanished'):
                        require('kmsg.log' in exported['files'], 'available log discarded: ' + case)
                    else:
                        require('kmsg.log' not in exported['files'] and
                                exported['result']['files']['kmsg.log']['state'] ==
                                {'log-symlink': 'symlink', 'log-replaced': 'changed', 'log-vanished': 'unreadable'}[case],
                                'unsafe log read')
                    if case.startswith('preexited-') and case != 'preexited-malformed-exit':
                        require(exported['result']['preservation_complete'] and exported['files']['kmsg-exit'] == b'1\n',
                                'terminal failed evidence not preserved')
                    if case in ('oversize-log', 'oversize-status'):
                        name = 'kmsg.log' if case == 'oversize-log' else 'kmsg.status'
                        require(len(exported['files'][name]) == S['EXPORT_FILES'][name] and
                                exported['result']['files'][name]['truncated'] == 'yes' and
                                not exported['result']['preservation_complete'], 'oversize prefix/mark lost')
                    if case in ('read-failed', 'exit-timeout', 'helper-refusal', 'dangling-partial', 'exit-symlink',
                                'late-terminal', 'preexited-malformed-exit'):
                        require(not exported['result']['preservation_complete'], 'unsafe export promoted as preserved')
                    if case in ('late-terminal', 'preexited-malformed-exit'):
                        require(not exported['result']['terminal_before_export'], 'unproved initial termination accepted')
                    if case == 'exit-timeout':
                        sleeps = [call for call in calls if call['name'] == 'bb-proxy' and call['args'] == ['sleep', '1']]
                        require(len(sleeps) == 10, 'logger exit wait bound changed')
                results.append(phase + ':' + case)
    print(json.dumps({'classification': 'session-shell-fixtures-pass', 'cases': results,
                      'case_count': len(results), 'parser_transport_cases': 4,
                      'runner_test_cases': runner_test_cases, 'fixture_timeout_seconds': CASE_TIMEOUT_SECONDS,
                      'fixture_cleanup_seconds': CLEANUP_SECONDS,
                      'shell': 'exact-ARM64-BusyBox-under-QEMU' if exact else 'host-/bin/sh',
                      'generated_source_sha256': PINS, 'effects': 'intercepted; no actual target signal or reboot',
                      'effect_guard_cases': len(guard_cases) * 2, 'effect_guard_optimization_levels': [0, 1],
                      'python_optimization': sys.flags.optimize,
                      'busybox_sha256': busybox_sha256,
                      'pidfd_kernel_behavior': 'not-tested', 'device_access': 'none',
                      'private_fixtures': 'removed'}, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except FixtureExecutionError as error:
        # Buildbox redirects stdout to the retained fixture receipt; do not
        # leave the useful diagnostic only in an ephemeral traceback.
        print(json.dumps(error.diagnostic, sort_keys=True))
        raise SystemExit(2)
