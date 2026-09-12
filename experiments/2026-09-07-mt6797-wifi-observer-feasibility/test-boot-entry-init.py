#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""RE-VM shell control test; inject the log sink and restart, never boot a PDA.

Run as root with the extracted, pinned ARM64 BusyBox binary as the sole argument.
Each case gets private mount/PID namespaces and a temporary minimal chroot.
"""
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
BUSYBOX_SHA256 = '61781806ad3650b0b9d2b3fc6971e2bffdca967af1a95375abd0578bafff14fb'


def main():
    if len(sys.argv) != 2 or os.geteuid() != 0 or platform.machine() != 'aarch64':
        raise SystemExit('usage in ARM64 RE VM as root: test-boot-entry-init.py BUSYBOX')
    binary = Path(sys.argv[1]).read_bytes()
    assert hashlib.sha256(binary).hexdigest() == BUSYBOX_SHA256
    raw = (HERE / 'boot-entry-init.sh').read_text()
    script = raw
    replacements = {
        'exec 3>/dev/kmsg': 'exec 3>&1',
        'while :; do /bin/busybox sleep 3600; done': 'exit 42',
        '/bin/busybox reboot -f || :': "/bin/busybox printf 'restart-request\\n' || :",
        '$(/bin/busybox uname -r)': '$(/bin/busybox printf 3.18.41+)',
        '< /proc/cmdline': '< /tests/cmdline',
    }
    for old, new in replacements.items():
        assert script.count(old) == 1, old
        script = script.replace(old, new)
    # Prove the real restart command is absent from every executed test script.
    assert '/bin/busybox reboot' not in script
    cmdline = ('bootopt=64S3,32N2,64N2 log_buf_len=4M rdinit=/init panic=0 '
               'cpuidle.off=1 ramoops.pmsg_capture=1 '
               'wifi_cycle=7f21b732-da47-4245-ad83-e985044054a6')
    cases = {
        'success-returned-restart': (cmdline, script),
        'wrong-session': (cmdline.replace('7f21b732', '7f21b733'), script),
        'duplicate-panic': (cmdline + ' panic=0', script),
        'sysrq-override': (cmdline + ' sysrq_always_enabled', script),
        'wrong-kernel': (cmdline, script.replace('printf 3.18.41+', 'printf other')),
        'wrong-log-node': (cmdline, script.replace('[ -c /dev/kmsg ]', '/bin/busybox false')),
        'failed-marker': (cmdline, script.replace('exec 3>&1', 'exec 3>/dev/full')),
        'failed-proc-mount': (cmdline, script.replace(
            '/bin/busybox mount -t proc -o nosuid,nodev,noexec proc /proc',
            '/bin/busybox false')),
    }
    with tempfile.TemporaryDirectory(prefix='wifi-boot-entry-test-') as tmp:
        root = Path(tmp)
        for name in ('bin', 'dev', 'proc', 'tests'):
            (root / name).mkdir()
        (root / 'bin/busybox').write_bytes(binary)
        (root / 'bin/busybox').chmod(0o500)
        command = ['unshare', '--mount', '--pid', '--fork', '--kill-child',
                   'sh', '-ceu', 'mount --make-rprivate /; exec chroot "$1" /bin/busybox sh -s',
                   'test', str(root)]
        for name, (parameters, body) in cases.items():
            (root / 'tests/cmdline').write_text(parameters + '\n')
            result = subprocess.run(command, input=body, capture_output=True,
                                    text=True, timeout=15, check=False)
            assert result.returncode == 42, (name, result.returncode, result.stderr)
            rows = result.stdout.splitlines()
            markers = [row for row in rows if row.startswith('<11>wifi-boot-entry-v1 ')]
            requests = rows.count('restart-request')
            if name == 'success-returned-restart':
                assert requests == 1 and len(markers) == 1, (name, rows)
                boot = markers[0].split(' boot=', 1)[1].split(' ', 1)[0]
                assert str(uuid.UUID(boot)) == boot
                expected = ('<11>wifi-boot-entry-v1 control=7f21b732-da47-4245-ad83-e985044054a6 '
                            f'boot={boot} stage=before-normal-restart')
                assert markers == [expected]
                assert len(expected.encode()) + 1 <= 192
            else:
                assert not markers and not requests, (name, rows)
            print(name + '=passed')
    print('PASS eight ARM64 PID1 shell paths; log/restart injected; no device access')


if __name__ == '__main__':
    main()
