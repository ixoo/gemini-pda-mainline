#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Copy the existing Gemian Wi-Fi credential for the exact private target into
fresh local mode-0600 input files, on the laptop, read-only on the device.

The target SSID comes from the existing private target file; the secret is
streamed from the device straight into a local file and is never printed,
passed as an argument, logged or held longer than the PSK derivation needs.
Nothing on the device is written, reconfigured or copied in bulk.

Environment:
  GEMINI_SSH_COMMAND  private helper that runs one remote shell command on the
                      known-good Gemian endpoint: `$GEMINI_SSH_COMMAND <cmd>`
                      with stdout passed through (the project's ssh_command).
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def refuse(message):
    print('credential: refused: ' + message, file=sys.stderr)
    sys.exit(2)


def remote(helper, command, timeout=20):
    result = subprocess.run([helper, command], capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        refuse('remote command failed (exit %d)' % result.returncode)
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True, type=Path, help='private AP target JSON (ssid field)')
    parser.add_argument('--expect-boot-id', required=True, help='live Gemian boot id verified beforehand')
    parser.add_argument('--output-dir', required=True, type=Path, help='fresh directory; refused if it exists')
    args = parser.parse_args()
    os.umask(0o077)
    helper = os.environ.get('GEMINI_SSH_COMMAND')
    if not helper or not os.access(helper, os.X_OK):
        refuse('GEMINI_SSH_COMMAND is not an executable helper')
    if not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', args.expect_boot_id):
        refuse('boot id must be a UUID')
    target = json.loads(args.target.read_text())
    ssid = target.get('ssid')
    if not isinstance(ssid, str) or not 1 <= len(ssid.encode()) <= 32 or any(c in ssid for c in '\n\r\0"\\'):
        refuse('target ssid missing or not a plain SSID')
    if args.output_dir.exists():
        refuse('output directory already exists')
    # Live identity: the exact boot and a Gemian kernel, before any read.
    boot = remote(helper, 'cat /proc/sys/kernel/random/boot_id').strip()
    if boot != args.expect_boot_id:
        refuse('live boot id differs from the expected Gemian boot')
    release = remote(helper, 'uname -r').strip()
    if not release.startswith('3.18.41'):
        refuse('live kernel is not the Gemian 3.18.41 kernel')
    # Exactly one connman service whose Name equals the SSID. The SSID is an
    # identity, not a secret; it travels as a quoted remote argument.
    listing = remote(helper, 'grep -lxF -- ' + shlex.quote('Name=' + ssid) +
                     ' /var/lib/connman/wifi_*/settings 2>/dev/null; true')
    matches = [line for line in listing.splitlines() if line.strip()]
    if len(matches) != 1:
        refuse('expected exactly one matching connman service, found %d' % len(matches))
    settings = matches[0]
    if not re.fullmatch(r'/var/lib/connman/wifi_[0-9a-f]+_[0-9a-f]+_managed_psk/settings', settings):
        refuse('unexpected connman service path shape')
    args.output_dir.mkdir(mode=0o700, parents=False)
    passphrase_file = args.output_dir / 'passphrase'
    psk_file = args.output_dir / 'psk.hex'
    # Stream the one value straight into the file; no capture, no echo.
    with open(passphrase_file, 'wb', opener=lambda p, f: os.open(p, f | os.O_CREAT | os.O_EXCL, 0o600)) as out:
        result = subprocess.run([helper, "sed -n 's/^Passphrase=//p' " + shlex.quote(settings)],
                                stdout=out, stderr=subprocess.DEVNULL, timeout=20)
    if result.returncode != 0:
        refuse('reading the passphrase failed (exit %d)' % result.returncode)
    raw = passphrase_file.read_bytes().rstrip(b'\r\n')
    if b'\n' in raw or not 8 <= len(raw) <= 63:
        refuse('passphrase is not one WPA2 passphrase line')
    psk = hashlib.pbkdf2_hmac('sha1', raw, ssid.encode(), 4096, 32)
    del raw
    with open(psk_file, 'w', opener=lambda p, f: os.open(p, f | os.O_CREAT | os.O_EXCL, 0o600)) as out:
        out.write(psk.hex() + '\n')
    for path in (passphrase_file, psk_file):
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            refuse('output file mode is not 0600')
    provenance = {
        'source': 'gemian-connman-settings', 'remote_settings_path': settings,
        'gemian_boot_id': boot, 'gemian_kernel_release': release,
        'ssid_sha256': hashlib.sha256(ssid.encode()).hexdigest(),
        'psk_sha256': hashlib.sha256(psk).hexdigest(),
        'derivation': 'pbkdf2-hmac-sha1 4096 rounds, salt = ssid, 32 bytes',
        'created_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'files': ['passphrase (0600)', 'psk.hex (0600)'],
    }
    (args.output_dir / 'provenance.json').write_text(json.dumps(provenance, indent=1) + '\n')
    print('credential: prepared one private input set in ' + str(args.output_dir) + ' (no secret shown)')


if __name__ == '__main__':
    main()
