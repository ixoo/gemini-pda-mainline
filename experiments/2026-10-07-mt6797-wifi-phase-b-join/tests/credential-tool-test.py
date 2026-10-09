#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise helper/extract-gemian-credential.py against a fake remote helper.

The fake helper answers the four remote commands from canned values; no device,
no network, no real credential. Secrets here are test constants.
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
SSID = 'fixture-net'
PASSPHRASE = 'fixture passphrase 42'
SERVICE = '/var/lib/connman/wifi_0200000000a1_6669787475726500_managed_psk/settings'


def fake_helper(work, boot=BOOT, release='3.18.41+', services=(SERVICE,), passphrase=PASSPHRASE):
    helper = work / 'fake-ssh'
    listing = '\\n'.join(services)
    helper.write_text(f"""#!/usr/bin/env python3
import sys
cmd = sys.argv[1]
if cmd == 'cat /proc/sys/kernel/random/boot_id':
    print({boot!r})
elif cmd == 'uname -r':
    print({release!r})
elif cmd.startswith('grep -lxF -- '):
    sys.stdout.write({listing!r} + ('\\n' if {listing!r} else ''))
elif cmd.startswith("sed -n 's/^Passphrase=//p' "):
    print({passphrase!r})
else:
    sys.exit(3)
""")
    helper.chmod(0o700)
    return helper


def run(work, helper, out, boot=BOOT, target=None):
    target = target or work / 'target.json'
    if not target.exists():
        target.write_text(json.dumps({'ssid': SSID, 'bssid': '02:00:00:00:00:a1'}))
    env = dict(os.environ, GEMINI_SSH_COMMAND=str(helper))
    return subprocess.run([sys.executable, str(TOOL), '--target', str(target), '--expect-boot-id', boot,
                           '--output-dir', str(out)], env=env, capture_output=True, text=True, timeout=60)


def main():
    with tempfile.TemporaryDirectory(prefix='credential-tool-') as directory:
        work = Path(directory)
        helper = fake_helper(work)
        out = work / 'input-1'
        result = run(work, helper, out)
        assert result.returncode == 0, result.stderr
        assert PASSPHRASE not in result.stdout + result.stderr
        assert stat.S_IMODE(out.stat().st_mode) == 0o700
        for name in ('passphrase', 'psk.hex'):
            assert stat.S_IMODE((out / name).stat().st_mode) == 0o600, name
        assert (out / 'passphrase').read_bytes() == (PASSPHRASE + '\n').encode()
        expected = hashlib.pbkdf2_hmac('sha1', PASSPHRASE.encode(), SSID.encode(), 4096, 32).hex()
        assert (out / 'psk.hex').read_text() == expected + '\n'
        provenance = json.loads((out / 'provenance.json').read_text())
        assert provenance['remote_settings_path'] == SERVICE and provenance['gemian_boot_id'] == BOOT
        assert provenance['psk_sha256'] == hashlib.sha256(bytes.fromhex(expected)).hexdigest()
        assert PASSPHRASE not in json.dumps(provenance) and expected not in json.dumps(provenance)
        # Existing output directory: refused before any remote command.
        assert run(work, helper, out).returncode == 2
        # Wrong live boot id, wrong kernel, zero matches, two matches, odd path: refused, nothing written.
        cases = [fake_helper(work, boot='99999999-2222-3333-4444-555555555555'),
                 fake_helper(work, release='4.4.0'),
                 fake_helper(work, services=()),
                 fake_helper(work, services=(SERVICE, SERVICE.replace('a1', 'a2'))),
                 fake_helper(work, services=('/etc/passwd',))]
        for i, bad in enumerate(cases):
            target_out = work / f'refused-{i}'
            result = run(work, bad, target_out)
            assert result.returncode == 2 and not target_out.exists(), (i, result.stderr)
            assert PASSPHRASE not in result.stdout + result.stderr
        # A passphrase outside the WPA2 length range is refused after being read, and the PSK is not derived.
        short = fake_helper(work, passphrase='short')
        result = run(work, short, work / 'refused-short')
        assert result.returncode == 2 and not (work / 'refused-short/psk.hex').exists()
        # Missing helper environment: refused.
        env = dict(os.environ); env.pop('GEMINI_SSH_COMMAND', None)
        result = subprocess.run([sys.executable, str(TOOL), '--target', str(work / 'target.json'), '--expect-boot-id', BOOT,
                                 '--output-dir', str(work / 'no-helper')], env=env, capture_output=True, text=True)
        assert result.returncode == 2
    print('credential-tool: PASS (fake remote; 0700/0600 outputs; PBKDF2 derivation; identity, uniqueness and shape refusals; no secret in output)')


if __name__ == '__main__':
    main()
