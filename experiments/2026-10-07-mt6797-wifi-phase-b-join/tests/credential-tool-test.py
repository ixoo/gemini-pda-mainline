#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise helper/extract-gemian-credential.py with a fake ssh that runs the
real remote program (GLib through ctypes) against a fake filesystem root.
No device, no network, no real credential; the secrets here are constants.
"""
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOOL = HERE / 'helper/extract-gemian-credential.py'
BOOT = '11111111-2222-3333-4444-555555555555'
SSID = 'fixture net'
PASSPHRASE = 'fixture\\pass  phrase\t42'  # exercises GLib escapes on the way in
SERVICE = 'wifi_0200000000a1_666978747572655f6e6574_managed_psk'


def key_file(name, passphrase, security='psk'):
    escaped = passphrase.replace('\\', '\\\\').replace('\t', '\\t').replace('  ', ' \\s')
    return '[%s]\nName=%s\nSSID=%s\nSecurity=%s\nPassphrase=%s\nFavorite=true\n' % (
        name, SSID, SSID.encode().hex(), security, escaped)


def fake_root(work, tag, boot=BOOT, kernel='3.18.41+', debian='9.13', services=None, after_boot=None):
    root = work / tag
    for rel, text in (('proc/sys/kernel/random/boot_id', boot), ('proc/sys/kernel/osrelease', kernel), ('etc/debian_version', debian)):
        p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text + '\n')
    base = root / 'var/lib/connman'; base.mkdir(parents=True)
    for name, content, mode in (services if services is not None else [(SERVICE, key_file(SERVICE, PASSPHRASE), 0o600)]):
        d = base / name; d.mkdir()
        if content is None:
            (d / 'settings').symlink_to('/etc/passwd')
        else:
            (d / 'settings').write_text(content); (d / 'settings').chmod(mode)
    if after_boot:
        (root / 'after_boot').write_text(after_boot)
    return root


def fake_ssh(work):
    # Ignores ssh options; runs the remote program from stdin with the fake root
    # named by FAKE_ROOT; the identity "after" the read can be changed by a file.
    ssh = work / 'fake-ssh'
    ssh.write_text('''#!/usr/bin/env python3
import os, subprocess, sys
root = os.environ['FAKE_ROOT']
cmd = sys.argv[-1].split()
assert cmd[:4] == ['sudo', '-n', 'python3', '-'], cmd
program = sys.stdin.read()
after = os.path.join(root, 'after_boot')
if os.path.exists(after):
    program = program.replace("identity('after')", "open(os.path.join(root,'proc/sys/kernel/random/boot_id'),'w').write(open(%r).read()); identity('after')" % after)
sys.exit(subprocess.run([sys.executable, '-', root] + cmd[5:], input=program.encode()).returncode)
''')
    ssh.chmod(0o700)
    return ssh


def run(work, root, out, boot=BOOT, ssid=SSID):
    target = work / ('target-%s.json' % out.name); target.write_text(json.dumps({'ssid': ssid}))
    env = dict(os.environ, FAKE_ROOT=str(root))
    return subprocess.run([sys.executable, str(TOOL), '--target', str(target), '--expect-boot-id', boot, '--output-dir', str(out),
                           '--ssh', str(work / 'fake-ssh')], env=env, capture_output=True, text=True, timeout=120)


def main():
    global TOOL
    with tempfile.TemporaryDirectory(prefix='credential-tool-') as directory:
        work = Path(directory); fake_ssh(work)
        root = fake_root(work, 'good')
        out = work / 'input-good'
        result = run(work, root, out)
        if os.geteuid() != 0:
            # Not root here: the owner gate must refuse with no files written.
            assert result.returncode == 2 and 'match-count-0' in result.stderr, result.stderr
            assert not (out / 'psk.hex').exists()
            # Patch the owner gate for the rest of this run by letting the fake root be the current uid.
            tool = TOOL.read_text().replace('st.st_uid != 0 or', 'st.st_uid != os.getuid() or')
            patched = work / 'tool-uid.py'; patched.write_text(tool); patched.chmod(0o700)
            TOOL = patched
            out = work / 'input-good-2'; result = run(work, root, out)
        assert result.returncode == 0, result.stderr
        assert PASSPHRASE not in result.stdout + result.stderr and 'Traceback' not in result.stderr
        assert stat.S_IMODE(out.stat().st_mode) == 0o700
        for name in ('remote-report', 'passphrase', 'psk.hex'):
            assert stat.S_IMODE((out / name).stat().st_mode) == 0o600, name
        assert (out / 'passphrase').read_bytes() == PASSPHRASE.encode()  # GLib decoded the escapes
        expected = hashlib.pbkdf2_hmac('sha1', PASSPHRASE.encode(), SSID.encode(), 4096, 32).hex()
        assert (out / 'psk.hex').read_text() == expected + '\n'
        prov = json.loads((out / 'provenance.json').read_text())
        assert prov['remote_settings_path'].endswith(SERVICE + '/settings') and prov['psk_sha256'] == hashlib.sha256(bytes.fromhex(expected)).hexdigest()
        assert PASSPHRASE not in json.dumps(prov) and expected not in json.dumps(prov)
        # Existing output directory: refused before any ssh.
        assert run(work, root, out).returncode == 2
        # Refusals: wrong boot, wrong kernel, wrong Debian, boot changed during the read, zero matches,
        # two matches, symlinked settings, group-readable settings, non-psk security, short passphrase.
        cases = {
            'boot': fake_root(work, 'boot', boot='99999999-2222-3333-4444-555555555555'),
            'kernel': fake_root(work, 'kernel', kernel='4.4.0'),
            'debian': fake_root(work, 'debian', debian='10.0'),
            'changed': fake_root(work, 'changed', after_boot='99999999-2222-3333-4444-555555555555'),
            'zero': fake_root(work, 'zero', services=[]),
            'two': fake_root(work, 'two', services=[(SERVICE, key_file(SERVICE, PASSPHRASE), 0o600), (SERVICE.replace('a1', 'a2'), key_file('x', PASSPHRASE), 0o600)]),
            'symlink': fake_root(work, 'symlink', services=[(SERVICE, None, 0)]),
            'mode': fake_root(work, 'mode', services=[(SERVICE, key_file(SERVICE, PASSPHRASE), 0o644)]),
            'security': fake_root(work, 'security', services=[(SERVICE, key_file(SERVICE, PASSPHRASE, 'none'), 0o600)]),
            'short': fake_root(work, 'short', services=[(SERVICE, key_file(SERVICE, 'short'), 0o600)]),
        }
        for tag, bad in cases.items():
            target_out = work / ('refused-' + tag)
            result = run(work, bad, target_out)
            assert result.returncode == 2, (tag, result.stderr)
            assert not (target_out / 'psk.hex').exists() and not (target_out / 'passphrase').exists(), tag
            assert PASSPHRASE not in result.stdout + result.stderr and 'Traceback' not in result.stderr, tag
    print('credential-tool: PASS (real remote program on a fake root under GLib; 0700/0600 outputs; escapes decoded by GLib; '
          'identity before/after, uniqueness, symlink, owner, mode, security and length refusals; no secret or traceback in output)')


if __name__ == '__main__':
    main()
