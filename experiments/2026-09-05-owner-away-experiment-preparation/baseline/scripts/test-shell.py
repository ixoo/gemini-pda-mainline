#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run exact AArch64 BusyBox shells against fixed, hardware-free init fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SOURCES = HERE.parent / 'initramfs'
SOURCE_DIGESTS = {
    'init': '77ec9d4cdc1b90afdd402a3569fe80e37697511891086ec739cd36bde0427416',
    'usb-auth': 'ea8c42b0d066613810d5489d8461b639554868470052f6efa953660a9db75c72',
    'console-status': 'b61d8ab47dbe36859980c3685985b9042eb71f5c1279b5c92cac5d9b9e4a7523',
}
APPLET_SET = {'sh', 'awk', 'sleep', 'ip', 'sha256sum', 'chvt', 'stty',
              'loadkmap', 'clear', 'mount', 'mkdir', 'cat', 'uname', 'init', 'dd'}
MAP_SHA = '02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c'

# The proxy owns every effectful call. It never executes mount, ip, chvt, stty,
# loadkmap, init, SSH, or an unrecognized applet. Only the four listed ordinary
# file/text applets may reach the exact candidate binary under QEMU.
PROXY = r'''
import json, os, pathlib, subprocess, sys, time
config = json.loads(pathlib.Path(__file__).with_name('fixture.json').read_text())
root = pathlib.Path(config['root'])
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
case = config['case']
with (root / 'calls.jsonl').open('a') as stream:
    stream.write(json.dumps({'name': name, 'args': args}) + '\n')
if name == 'bb-proxy':
    applet, *args = args
    if applet in ('awk', 'cat', 'mkdir'):
        # Refuse all unexpected absolute read/write destinations before exec.
        for arg in args:
            if arg.startswith('/') and not arg.startswith(str(root) + '/'):
                raise SystemExit(98)
        raise SystemExit(subprocess.call(config['runner'] + [applet] + args))
    if applet == 'sha256sum':
        print(('0' * 64 if case == 'console-map-hash' else config['map_sha']) + '  ' + args[0])
        raise SystemExit(0)
    if applet == 'sleep':
        if args == ['3600']:
            time.sleep(20)
        raise SystemExit(0)
    if applet == 'ip':
        raise SystemExit(1 if (case == 'usb-link-fail' and args[0] == 'link') or
                         (case == 'usb-address-fail' and args[0] == 'address') else 0)
    if applet == 'uname':
        print('wrong-kernel' if case == 'init-kernel-fail' else '7.1.3-gemini-mt6797-pwrap-reset')
        raise SystemExit(0)
    if applet in ('chvt', 'stty', 'loadkmap', 'clear', 'mount', 'init'):
        fail = {'chvt': 'console-vt-fail', 'stty': 'console-stty-fail',
                'loadkmap': 'console-load-fail', 'mount': 'init-mount-fail'}
        raise SystemExit(1 if case == fail.get(applet) else 0)
    raise SystemExit(99)
if name == 'helper-dropbear':
    if case == 'usb-server-hold':
        time.sleep(20)
    print('fixture-server-only', file=sys.stderr)
    raise SystemExit(7 if case == 'usb-server-fail' else 0)
if name == 'helper-unicode':
    raise SystemExit(1 if case == 'console-unicode-fail' else 0)
if name == 'helper-keymap':
    calls = [json.loads(line) for line in (root / 'calls.jsonl').read_text().splitlines()]
    verifies = sum(call['name'] == name and call['args'][0] == '--verify' for call in calls)
    if args[0] == '--preflight':
        raise SystemExit(1 if case == 'console-preflight-fail' else 0)
    if case in ('console-load-pass', 'console-load-fail', 'console-preflight-fail', 'console-readback-fail'):
        raise SystemExit(1 if verifies == 1 or case == 'console-readback-fail' else 0)
    raise SystemExit(0)
if name in ('helper-kmsg', 'helper-usb'):
    raise SystemExit(0)
raise SystemExit(99)
'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run(command, timeout=5):
    """Bound and reap the entire fixture process group, including background jobs."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    expired = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        expired = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=2)
    return process.returncode, stdout, stderr, expired


def checked(condition, message):
    if not condition:
        raise ValueError(message)


def sources():
    result = {}
    for name, expected in SOURCE_DIGESTS.items():
        path = SOURCES / name
        checked(path.is_file() and not path.is_symlink(), 'source must be regular')
        data = path.read_bytes()
        checked(digest(data) == expected, 'changed source template: ' + name)
        result[name] = data.decode('ascii')
    return result


def prepare_fixture(root, case, source_name, source, runner):
    root.mkdir(mode=0o700)
    for relative in ('run/a53', 'root/.ssh', 'etc/dropbear', 'sys/devices/system/cpu',
                     'proc/sys/kernel/random', 'dev/pts'):
        (root / relative).mkdir(parents=True, exist_ok=True)
    if case not in ('usb-missing', 'usb-wrong-interface'):
        (root / 'sys/class/net/usb0').mkdir(parents=True)
    elif case == 'usb-wrong-interface':
        (root / 'sys/class/net/usb1').mkdir(parents=True)
    for field, value in (('online', '0-7'), ('offline', '8-9'), ('possible', '0-9'), ('present', '0-9')):
        (root / 'sys/devices/system/cpu' / field).write_text(
            '0-9\n' if case == 'init-cpu-fail' and field == 'online' else value + '\n')
    (root / 'proc/sys/kernel/random/boot_id').write_text('00000000-0000-0000-0000-000000000001\n')
    (root / 'etc/gemini-us.bkeymap').write_bytes(b'fixture-only-map')
    config = {'root': str(root), 'case': case, 'runner': runner, 'map_sha': MAP_SHA}
    (root / 'fixture.json').write_text(json.dumps(config))
    proxies = {'/bin/busybox': 'bb-proxy', '/bin/dropbear': 'helper-dropbear',
               '/bin/console-unicode-mode': 'helper-unicode',
               '/bin/console-keymap-verify': 'helper-keymap',
               '/bin/kmsg-capture': 'helper-kmsg', '/bin/usb-auth': 'helper-usb'}
    transformed = source
    for fixed, helper in proxies.items():
        path = root / helper
        path.write_text('#!' + sys.executable + '\n' + PROXY)
        path.chmod(0o700)
        transformed = transformed.replace(fixed, shlex.quote(str(path)))
    for fixed in ('/sys/class/net/usb0', '/sys/devices/system/cpu/', '/etc/gemini-us.bkeymap',
                  '/run/a53', '/root/.ssh', '/etc/dropbear/host_key', '/proc/sys/kernel/random/boot_id'):
        transformed = transformed.replace(fixed, str(root) + fixed)
    # /dev/pts mkdir is the sole mkdir path outside /run/a53 in the exact init.
    # Its mount argument is mocked too, so substituting it has no host effect.
    transformed = transformed.replace('/dev/pts', str(root) + '/dev/pts')
    transformed = transformed.replace('export PATH=/bin', 'export PATH=' + shlex.quote(str(root)))
    path = root / ('source-' + source_name)
    path.write_text(transformed)
    return path


def calls(root):
    path = root / 'calls.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--busybox', type=Path, required=True)
    parser.add_argument('--work-root', type=Path, required=True)
    parser.add_argument('--qemu', default='qemu-aarch64-static')
    args = parser.parse_args()
    source_text = sources()  # Must refuse before any transformed shell executes.
    checked(args.busybox.is_file() and not args.busybox.is_symlink(), 'busybox must be regular')
    busybox = args.busybox.resolve(strict=True)
    elf = busybox.read_bytes()
    checked(elf[:6] == b'\x7fELF\x02\x01' and len(elf) >= 64 and
            int.from_bytes(elf[18:20], 'little') == 183, 'busybox must be little-endian ARM64 ELF')
    checked(args.work_root.is_dir() and not args.work_root.is_symlink(), 'work root must be a real directory')
    work_root = args.work_root.resolve(strict=True)
    checked(not any(char.isspace() or char in "'\"$`\\" for char in str(work_root)), 'work root has unsupported shell characters')
    qemu = shutil.which(args.qemu)
    checked(qemu is not None, 'QEMU unavailable; exact-shell check not run')
    runner = [qemu, str(busybox)]
    status, stdout, _stderr, expired = run(runner + ['--list'])
    checked(status == 0 and not expired, 'candidate BusyBox applet inventory failed')
    checked(APPLET_SET <= set(stdout.decode().splitlines()), 'candidate BusyBox lacks required applet')
    results = ['exact-required-applet-inventory']
    for name in source_text:
        status, _out, _err, expired = run(runner + ['sh', '-n', str(SOURCES / name)])
        checked(status == 0 and not expired, 'exact-shell syntax failed: ' + name)
        results.append('syntax-' + name)
    with tempfile.TemporaryDirectory(prefix='a53-shell-test-', dir=work_root) as work:
        root = Path(work)
        cases = [
            ('usb-missing', 'usb-auth'), ('usb-wrong-interface', 'usb-auth'),
            ('usb-link-fail', 'usb-auth'), ('usb-address-fail', 'usb-auth'),
            ('usb-pass', 'usb-auth'), ('usb-server-fail', 'usb-auth'), ('usb-server-hold', 'usb-auth'),
            ('console-pass', 'console-status'), ('console-map-hash', 'console-status'),
            ('console-vt-fail', 'console-status'), ('console-stty-fail', 'console-status'),
            ('console-unicode-fail', 'console-status'), ('console-preflight-fail', 'console-status'),
            ('console-load-fail', 'console-status'), ('console-readback-fail', 'console-status'),
            ('console-load-pass', 'console-status'), ('init-pass', 'init'),
            ('init-mount-fail', 'init'), ('init-cpu-fail', 'init'), ('init-kernel-fail', 'init'),
        ]
        for case, name in cases:
            directory = root / case
            script = prepare_fixture(directory, case, name, source_text[name], runner)
            timeout = 3 if case.endswith('-hold') or case.startswith('init-') and case != 'init-pass' else 8
            status, out, _err, expired = run(runner + ['sh', str(script)], timeout=timeout)
            observed = calls(directory)
            server = [call for call in observed if call['name'] == 'helper-dropbear']
            applets = [call['args'][0] for call in observed if call['name'] == 'bb-proxy']
            checked('nc' not in applets, 'unauthenticated fallback observed')
            if case in ('usb-missing', 'usb-wrong-interface', 'usb-link-fail', 'usb-address-fail'):
                checked(status != 0 and not expired and not server, case + ': server was admitted')
                if case in ('usb-missing', 'usb-wrong-interface'):
                    checked('ip' not in applets and applets.count('sleep') == 30, 'USB discovery bound changed')
            elif case.startswith('usb-'):
                expected_args = ['-F', '-s', '-j', '-k', '-l', 'usb0', '-p', '10.15.19.82:22',
                                 '-D', str(directory / 'root/.ssh'), '-r', str(directory / 'etc/dropbear/host_key'),
                                 '-P', str(directory / 'run/a53/ssh-pid'), '-I', '60', '-M', '360', '-T', '2']
                checked(len(server) == 1 and server[0]['args'] == expected_args, 'SSH arguments changed')
                checked(applets == ['ip', 'ip'], 'unexpected USB side effects/retry')
                if case == 'usb-server-hold':
                    checked(expired and status != 0, 'server interruption did not stop shell')
                else:
                    checked(status == (7 if case == 'usb-server-fail' else 0) and not expired,
                            'exec server exit status not retained')
            elif case.startswith('console-'):
                passed = case in ('console-pass', 'console-load-pass')
                ready = directory / 'run/a53/console.status'
                checked(not expired and (status == 0) == passed, 'console refusal changed: ' + case)
                checked(ready.exists() == passed, 'console ready published after failed gate')
                if passed:
                    checked(ready.read_text() == 'console=ready\n' and b'accepts no commands' in out,
                            'console status contract changed')
                checked(('loadkmap' in applets) == (case in ('console-load-pass', 'console-load-fail', 'console-readback-fail')),
                        'load attempted outside verified map preflight')
            else:
                launched = [call['name'] for call in observed if call['name'] in ('helper-kmsg', 'helper-usb')]
                if case == 'init-pass':
                    checked(status == 0 and not expired and sorted(launched) == ['helper-kmsg', 'helper-usb'] and
                            'init' in applets, 'init service launch mismatch')
                else:
                    checked(expired and b'hold for recovery' in out and not launched and 'init' not in applets,
                            'init failed preflight did not hold: ' + case)
            results.append(case)
        # Actual candidate shell and dd, no mocked syscalls. The regular file
        # limit is inherited by children; pipes/SSH streams are not this bound.
        limit_path = root / 'file-size-test'
        command = 'ulimit -f 1; exec ' + ' '.join(shlex.quote(p) for p in runner +
                  ['dd', 'if=/dev/zero', 'of=' + str(limit_path), 'bs=1024', 'count=4'])
        status, _out, _err, expired = run(runner + ['sh', '-c', command])
        checked(status != 0 and not expired and limit_path.exists(), 'file limit fixture did not stop write')
        block_bytes = limit_path.stat().st_size
        checked(block_bytes in (512, 1024), 'unexpected exact-shell ulimit unit')
        results.append('inherited-regular-file-size-limit')
    print(json.dumps({'classification': 'offline-exact-busybox-shell-pass', 'cases': results,
                      'busybox_sha256': digest(busybox.read_bytes()), 'source_sha256': SOURCE_DIGESTS,
                      'ulimit_f_block_bytes': block_bytes, 'ulimit_f_256_bytes': block_bytes * 256,
                      'file_limit_scope': 'inherited regular files only; pipes and SSH output need independent bounds',
                      'device_action': 'none; all effectful applets mocked',
                      'kernel_evdev_vt_ioctl': 'not-tested', 'dropbear_binary': 'not-executed-by-this-test',
                      'candidate_init_boot': 'not-tested', 'private_fixtures': 'removed'}, sort_keys=True))


if __name__ == '__main__':
    main()
