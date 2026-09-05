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
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
S = runpy.run_path(str(HERE / 'session_steps.py'))
BOOT = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
PINS = {'seal': 'e639b8550cfc696e1357b80c1599f75f3e67da1ce996ce724b8b3039eb65af5d',
        'recovery': '2228aff8c2f4d12816fd813debc3fc2c8dd8f4dc36a88814db54d958c07d0266'}
PROXY = r'''
import base64,json,pathlib,subprocess,sys,textwrap
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
    if case=='exit-timeout': raise SystemExit(0)
    (ram/'kmsg-exit').write_text('1\n' if case=='logger-failed' else '0\n')
    if case=='exit-symlink':
        (ram/'kmsg-exit').rename(ram/'exit-copy')
        (ram/'kmsg-exit').symlink_to('exit-copy')
    if case!='partial-status': (ram/'kmsg.status.partial').unlink(missing_ok=True)
    if case=='dangling-partial': (ram/'kmsg.status.partial').symlink_to('missing-partial')
    if case=='missing-status': raise SystemExit(0)
    status=(root/'expected-status').read_bytes()
    if case=='failed-status': status=status.replace(b'result=pass',b'result=failed')
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
    require(len(args)==3 and args[:2]==['-c','%u:%g:%a'] and args[2] in (str(root/'run'),str(ram)),
            'unreviewed stat path/arguments')
    print('0:0:755' if case=='mode-mismatch' else '1:0:700' if case=='owner-mismatch' else '0:0:700')
elif applet=='sleep':
    require(args==['1'], 'unreviewed sleep arguments')
elif applet=='base64' and not c['busybox']:
    require(len(args)==1 and args[0].startswith(str(root)+'/'), 'unreviewed base64 path')
    data=base64.b64encode(pathlib.Path(args[0]).read_bytes()).decode()
    print('\n'.join(textwrap.wrap(data,76)))
elif applet in ('cat','awk','mkdir','wc','printf','base64'):
    for arg in args:
        if arg.startswith('/'):
            require(arg.startswith(str(root)+'/'), 'absolute path escaped fixture')
    if c['busybox']:
        command=c['runner']+[applet]+args
    else:
        executable={'cat':'/bin/cat','awk':'/usr/bin/awk','mkdir':'/bin/mkdir','wc':'/usr/bin/wc',
                    'printf':'/usr/bin/printf'}[applet]
        command=[executable]+args
    raise SystemExit(subprocess.call(command))
else:
    raise SystemExit('unreviewed applet, including direct kill, refused')
'''


def require(value, reason):
    if not value:
        raise ValueError(reason)


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
    if case == 'dangling-status':
        (ram / 'kmsg.status').symlink_to('missing-status')
    if case == 'dangling-exit':
        (ram / 'kmsg-exit').symlink_to('missing-exit')
    if case == 'existing-claim':
        (ram / ('log-seal-attempt' if phase == 'seal' else 'native-recovery-attempt')).mkdir()
    paths = {'/bin/busybox': str(root / 'bb-proxy'), '/bin/reboot': str(root / 'helper-reboot'),
             '/bin/kmsg-seal': str(root / 'helper-kmsg-seal'), '/bin/kmsg-capture': str(root / 'logger-file'),
             '/init': str(root / 'init-file'), '/proc/': str(root / 'proc') + '/',
             '/sys/': str(root / 'sys') + '/', '/run': str(root / 'run')}
    pattern = re.compile('|'.join(re.escape(path) for path in sorted(paths, key=len, reverse=True)))
    transformed = pattern.sub(lambda match: paths[match[0]], script.decode())
    # Source pins above are the authority for this exact transformation set.
    hashes = {paths['/' + name]: value['sha256'] for name, value in candidate()['members'].items()}
    config = {'case': case, 'release': S['RELEASE'], 'hashes': hashes, 'runner': runner, 'busybox': exact}
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
        inventory = subprocess.run(runner + ['--list'], capture_output=True, timeout=5, check=True)
        require({'sh', 'stat', 'awk', 'cat', 'mkdir', 'sha256sum', 'uname', 'sleep', 'wc', 'base64', 'printf'} <=
                set(inventory.stdout.decode().splitlines()), 'required applet missing')
    common = ['good', 'boot-mismatch', 'kernel-mismatch', 'cpu-mismatch', 'member-mismatch',
              'swap-active', 'persistent-run', 'persistent-root', 'duplicate-run', 'duplicate-root',
              'a53-submount', 'log-submount',
              'run-symlink', 'a53-symlink', 'mode-mismatch', 'owner-mismatch', 'existing-claim']
    seal_only = ['existing-status', 'existing-exit', 'dangling-status', 'dangling-exit',
                 'helper-refusal', 'exit-timeout', 'logger-failed',
                 'partial-status', 'dangling-partial', 'exit-symlink', 'missing-status',
                 'status-symlink', 'log-symlink', 'oversize-log',
                 'empty-log', 'failed-status']
    results = []
    with tempfile.TemporaryDirectory(prefix='a53-session-shell-', dir=work_root) as work:
        base = Path(work)
        guard_root = base / 'effect-guards'
        fixture(guard_root, 'seal', 'good', scripts['seal'], runner, exact)
        guard_cases = [('bb-proxy', ['kill', '-TERM', '1'], b'unreviewed applet'),
                       ('bb-proxy', ['cat', '/outside-a53-fixture-do-not-read'], b'absolute path escaped fixture'),
                       ('bb-proxy', ['sleep', '9'], b'unreviewed sleep arguments'),
                       ('bb-proxy', ['stat', '-c', '%u:%g:%a', '/outside-a53-fixture'], b'unreviewed stat'),
                       ('helper-kmsg-seal', [], b'claim missing before signal helper')]
        for optimization in ('0', '1'):
            for name, arguments, diagnostic in guard_cases:
                process = subprocess.run([str(guard_root / name)] + arguments,
                                         env={**os.environ, 'PYTHONOPTIMIZE': optimization},
                                         capture_output=True, timeout=5)
                require(process.returncode != 0 and diagnostic in process.stderr and not process.stdout,
                        'effect guard disabled at Python optimization ' + optimization)
        for phase, script in scripts.items():
            for case in common + (seal_only if phase == 'seal' else []):
                root = base / (phase + '-' + case)
                path = fixture(root, phase, case, script, runner, exact)
                command = runner + ['sh', str(path)] if exact else ['/bin/sh', str(path)]
                process = subprocess.run(command, capture_output=True, timeout=8)
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
                    else:
                        require(process.returncode == 94 and process.stdout.endswith(b'__A53_NATIVE_RECOVERY_END__\n'),
                                'native helper return must remain a failure (94)')
                elif case in common or case in ('existing-status', 'existing-exit', 'dangling-status', 'dangling-exit'):
                    require(process.returncode != 0 and not effects, phase + ' guard did not refuse: ' + case)
                    if case in common and case != 'existing-claim':
                        claim = root / 'run/a53' / ('log-seal-attempt' if phase == 'seal' else 'native-recovery-attempt')
                        require(not claim.exists(), phase + ' guard consumed remote claim: ' + case)
                else:
                    require([call['name'] for call in effects] == ['helper-kmsg-seal'], 'sealing helper retry/unexpected effect')
                    if case in ('empty-log', 'failed-status'):
                        require(process.returncode == 0, 'malformed-status fixture did not reach independent parser')
                        try:
                            S['parse_seal'](process.stdout, process.stderr,
                                            {'exit_status': 0, 'reason': None, 'stdin_complete': True})
                        except ValueError:
                            pass
                        else:
                            raise ValueError('independent parser accepted ' + case)
                    else:
                        require(process.returncode != 0 and b'__A53_LOG_SEAL_END__' not in process.stdout,
                                'incomplete logger accepted: ' + case)
                    if case == 'exit-timeout':
                        sleeps = [call for call in calls if call['name'] == 'bb-proxy' and call['args'] == ['sleep', '1']]
                        require(len(sleeps) == 10, 'logger exit wait bound changed')
                results.append(phase + ':' + case)
    print(json.dumps({'classification': 'session-shell-fixtures-pass', 'cases': results,
                      'case_count': len(results), 'shell': 'exact-ARM64-BusyBox-under-QEMU' if exact else 'host-/bin/sh',
                      'generated_source_sha256': PINS, 'effects': 'intercepted; no actual target signal or reboot',
                      'effect_guard_cases': len(guard_cases) * 2, 'effect_guard_optimization_levels': [0, 1],
                      'python_optimization': sys.flags.optimize,
                      'busybox_sha256': busybox_sha256,
                      'pidfd_kernel_behavior': 'not-tested', 'device_access': 'none',
                      'private_fixtures': 'removed'}, sort_keys=True))


if __name__ == '__main__':
    main()
