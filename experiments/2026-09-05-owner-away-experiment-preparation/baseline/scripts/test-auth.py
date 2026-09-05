#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the exact static AArch64 SSH server under QEMU with disposable keys."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import pwd
import signal
import socket
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('provision', HERE / 'provision.py')
provision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provision)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def run(args, **kwargs):
    return subprocess.run(args, capture_output=True, timeout=10, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--work-root', type=Path, required=True)
    args = parser.parse_args()
    package = args.package.resolve(strict=True)
    qemu = 'qemu-aarch64-static'
    cases = []
    help_result = run([qemu, str(package / 'dropbear'), '-h'])
    for forbidden in (b'Disable password logins', b'Disable local port', b'Disable remote port', b'Create hostkeys'):
        require(forbidden not in help_result.stderr, 'hardened build options were not compiled')
    require(b'Dropbear server v2026.94' in help_result.stderr, 'server version changed')
    cases.append('compiled-authentication-surface')
    with tempfile.TemporaryDirectory(prefix='a53-auth-test-', dir=args.work_root) as work:
        root = Path(work)
        keys = root / 'keys'
        provision.generate(keys)
        independent = root / 'converted'
        result = run([qemu, str(package / 'dropbearconvert'), 'openssh', 'dropbear', str(keys / 'host'), str(independent)])
        require(result.returncode == 0, 'independent conversion failed')
        require(independent.read_bytes() == (keys / 'dropbear_host_key').read_bytes(), 'independent key conversion mismatch')
        cases.append('independent-host-key-conversion')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        known = root / 'known_hosts'
        public = (keys / 'host.pub').read_text().split()
        known.write_text(f'[127.0.0.1]:{port} ' + ' '.join(public[:2]) + '\n')
        # Omit runtime disable switches so they cannot mask a wrongly configured binary.
        command = [qemu, str(package / 'dropbear'), '-F', '-D', str(keys), '-r',
                   str(keys / 'dropbear_host_key'), '-p', f'127.0.0.1:{port}', '-P', str(root / 'pid'), '-I', '15', '-M', '30', '-T', '2']
        server = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, start_new_session=True)
        try:
            for _ in range(40):
                if server.poll() is not None:
                    raise ValueError('server startup refused; inspect private test stderr')
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=.1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise ValueError('server startup timeout')
            ssh = ['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'IdentityAgent=none',
                   '-o', 'StrictHostKeyChecking=yes', '-o', f'UserKnownHostsFile={known}', '-o', 'GlobalKnownHostsFile=/dev/null',
                   '-o', 'ConnectTimeout=3', '-o', 'ConnectionAttempts=1', '-p', str(port)]
            target = pwd.getpwuid(os.getuid()).pw_name + '@127.0.0.1'
            good = run(ssh + ['-i', str(keys / 'admin'), target, 'printf authenticated; printf separate >&2'])
            require(good.returncode == 0 and good.stdout == b'authenticated' and good.stderr == b'separate', 'authenticated stdout/stderr failed')
            cases.append('authorized-exec-separated-streams')
            wrong = run(ssh + ['-i', str(keys / 'host'), target, 'printf forbidden'])
            require(wrong.returncode != 0 and wrong.stdout == b'', 'wrong key admitted')
            cases.append('unapproved-key-refused')
            password = run(ssh + ['-o', 'PreferredAuthentications=password', target, 'printf forbidden'])
            require(password.returncode != 0 and b'publickey' in password.stderr and password.stdout == b'', 'password path admitted')
            cases.append('password-authentication-refused')
            known.write_text(f'[127.0.0.1]:{port} ' + ' '.join((keys / 'admin.pub').read_text().split()[:2]) + '\n')
            mismatch = run(ssh + ['-i', str(keys / 'admin'), target, 'printf forbidden'])
            require(mismatch.returncode != 0 and mismatch.stdout == b'' and b'Host key verification failed' in mismatch.stderr, 'wrong host refusal not attributable')
            cases.append('host-identity-mismatch-refused')
            known.write_text(f'[127.0.0.1]:{port} ' + ' '.join(public[:2]) + '\n')
            forward = run(ssh + ['-i', str(keys / 'admin'), '-o', 'ExitOnForwardFailure=yes', '-R', '0:127.0.0.1:1', target, 'true'])
            require(forward.returncode != 0 and b'remote port forwarding failed' in forward.stderr, 'forwarding refusal not attributable')
            alive = run(ssh + ['-i', str(keys / 'admin'), target, 'printf still-authenticated'])
            require(alive.returncode == 0 and alive.stdout == b'still-authenticated', 'server failed during negative cases')
            cases.append('forwarding-refused')
        finally:
            os.killpg(server.pid, signal.SIGTERM)
            try:
                server.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid, signal.SIGKILL)
                server.communicate(timeout=3)
        stopped = run(ssh + ['-i', str(keys / 'admin'), target, 'printf forbidden'])
        require(stopped.returncode != 0 and stopped.stdout == b'', 'interrupted server admitted')
        cases.append('interrupted-server-refused')
    print(json.dumps({'classification': 'offline-authentication-pass', 'cases': cases,
                      'server': 'exact-AArch64-binary-under-QEMU', 'command_shell': 'builder-account-shell',
                      'candidate-init-boot': 'not-tested', 'device_action': 'none', 'private-fixtures': 'removed'}, sort_keys=True))


if __name__ == '__main__':
    main()
