#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Copy the existing Gemian Wi-Fi credential for the exact private target into
fresh local mode-0600 input files. Runs on the laptop; read-only on the device.

One SSH session runs one remote read program as root (sudo -n) that verifies
the device identity, requires the exact boot id, kernel release and Debian
version before any read and again after it, refuses any connman PSK service
whose directory or settings file is a symlink, not root-owned, group-readable,
malformed or oversized (one such service refuses the whole read rather than
hide a match), reads each settings file through an O_NOFOLLOW descriptor with
fstat and a bounded read, parses it with GLib's own key-file reader from that
data (through ctypes; GLib decodes the escaped value, so no re-implemented
parser), reads only the PSK services named with this SSID's hex identifier (other
SSIDs, open, WEP and enterprise services are left unread), requires exactly
one such service across adapters whose group Name is the target SSID with the
Name, Security and Passphrase keys each present exactly once, and prints a
small key=value report with the secret base64-encoded. The report is streamed
straight into a private mode-0600 file. Nothing on the device is written,
reconfigured or copied in bulk. No secret reaches stdout, stderr, an argument
or a log, and failures print generic messages only.

ssh: standard client, host alias (default `gemini`), BatchMode, strict known
host, no host-key updates, IdentitiesOnly, no agent, optional identity file.
"""
import argparse
import base64
import hashlib
import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_KERNEL = '3.18.41+'
EXPECTED_DEBIAN = '9.13'

# Remote read program: argv[1] = filesystem root (always "/" on the device; the
# fixture passes a fake root), argv[2] = SSID as base64, argv[3] = expected boot
# id, argv[4] = expected kernel release, argv[5] = expected Debian version,
# argv[6] = "extract" or "diagnose" (counts and presence only, no value).
# ConnMan's service_save (src/service.c, 1.33 and 1.35) persists Name and
# Passphrase but no Security key: security is part of the service identifier
# (_managed_psk), so Security is optional in the file and, if present, must
# be psk.
REMOTE = r'''
import base64, ctypes, ctypes.util, os, re, stat, sys
root, ssid = sys.argv[1], base64.b64decode(sys.argv[2])
expect = {'boot': sys.argv[3], 'kernel': sys.argv[4], 'debian': sys.argv[5]}
diagnose = len(sys.argv) > 6 and sys.argv[6] == 'diagnose'
def read(rel):
    with open(os.path.join(root, rel.lstrip('/')), 'rb') as f:
        return f.read(4096).strip().decode('ascii', 'replace')
def identity(tag):
    seen = {'boot': read('/proc/sys/kernel/random/boot_id'),
            'kernel': read('/proc/sys/kernel/osrelease'), 'debian': read('/etc/debian_version')}
    for k in ('boot', 'kernel', 'debian'):
        print('%s_%s=%s' % (tag, k, seen[k]))
    return seen == expect
if not identity('before'):
    print('status=identity-mismatch'); sys.exit(0)
lib = ctypes.CDLL(ctypes.util.find_library('glib-2.0') or 'libglib-2.0.so.0')
lib.g_key_file_new.restype = ctypes.c_void_p
lib.g_key_file_load_from_data.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_void_p]
lib.g_key_file_get_groups.restype = ctypes.c_void_p
lib.g_key_file_get_groups.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
lib.g_key_file_get_string.restype = ctypes.c_void_p
lib.g_key_file_get_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p]
lib.g_free.argtypes = [ctypes.c_void_p]; lib.g_strfreev.argtypes = [ctypes.c_void_p]
lib.g_key_file_free.argtypes = [ctypes.c_void_p]
def value(kf, group, key):
    p = lib.g_key_file_get_string(kf, group, key, None)
    if not p:
        return None
    v = ctypes.string_at(p); lib.g_free(p); return v
def key_counts(data):
    # Raw occurrences of each key per group, so a duplicated key is refused
    # instead of silently resolved by GLib's last-key-wins.
    counts, group = {}, None
    for line in data.split(b'\n'):
        line = line.strip()
        if not line or line.startswith(b'#'):
            continue
        if line.startswith(b'['):
            group = line; counts.setdefault(group, {}); continue
        if group is None or b'=' not in line:
            continue
        key = line.split(b'=', 1)[0].strip().split(b'[', 1)[0].strip()
        counts[group][key] = counts[group].get(key, 0) + 1
    return counts
base = os.path.join(root, 'var/lib/connman')
matches, problems = [], 0
# ConnMan names a Wi-Fi service wifi_<adapter hex>_<ssid hex>_<mode>_<security>.
# Only PSK services of this exact SSID are candidates; every other service
# (other SSIDs, open, WEP, enterprise) is left unread.
candidate = re.compile(r'wifi_[0-9a-f]{12}_' + ssid.hex() + r'_managed_psk')
for name in sorted(os.listdir(base)):
    if not candidate.fullmatch(name):
        continue
    directory = os.path.join(base, name)
    try:
        dst = os.lstat(directory)
    except OSError:
        problems += 1; continue
    if stat.S_ISLNK(dst.st_mode) or not stat.S_ISDIR(dst.st_mode) or dst.st_uid != 0:
        problems += 1; continue
    path = os.path.join(directory, 'settings')
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NOCTTY)
    except OSError:
        problems += 1; continue
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or (st.st_mode & 0o077) or st.st_size > 65536:
            problems += 1; continue
        data = os.read(fd, 65536)
        if len(data) != st.st_size:
            problems += 1; continue
    finally:
        os.close(fd)
    kf = lib.g_key_file_new()
    if not lib.g_key_file_load_from_data(kf, data, len(data), 0, None):
        lib.g_key_file_free(kf); problems += 1; continue
    counts = key_counts(data)
    n = ctypes.c_size_t(); groups = lib.g_key_file_get_groups(kf, ctypes.byref(n))
    arr = ctypes.cast(groups, ctypes.POINTER(ctypes.c_char_p))
    for i in range(n.value):
        if value(kf, arr[i], b'Name') == ssid:
            raw = counts.get(b'[' + arr[i] + b']', {})
            kc = {k: raw.get(k, 0) for k in (b'Name', b'Security', b'Passphrase')}
            unique = kc[b'Name'] == 1 and kc[b'Passphrase'] == 1 and kc[b'Security'] <= 1
            matches.append(('/var/lib/connman/%s/settings' % name,
                            None if diagnose else value(kf, arr[i], b'Passphrase'),
                            value(kf, arr[i], b'Security'), unique, kc))
    lib.g_strfreev(groups); lib.g_key_file_free(kf)
if diagnose:
    # Metadata only: how many candidate services, and per matching group the
    # occurrence count of each field. No value, no path, no secret.
    print('candidates=%d' % len(matches))
    for i, m in enumerate(matches):
        print('group%d_name_count=%d' % (i, m[4][b'Name']))
        print('group%d_security_count=%d' % (i, m[4][b'Security']))
        print('group%d_passphrase_count=%d' % (i, m[4][b'Passphrase']))
        print('group%d_security_is_psk=%d' % (i, int(m[2] == b'psk')))
    print('status=diagnosed')
elif problems:
    print('status=unsafe-or-malformed-services-%d' % problems)
elif len(matches) != 1:
    print('status=match-count-%d' % len(matches))
elif not matches[0][3]:
    print('status=field-count-not-unique')
elif matches[0][1] is None or (matches[0][2] is not None and matches[0][2] != b'psk'):
    print('status=no-psk-passphrase')
else:
    print('settings=%s' % matches[0][0])
    print('passphrase_b64=%s' % base64.b64encode(matches[0][1]).decode())
    print('status=ok')
print('problems=%d' % problems)
identity('after')
'''


def refuse(message, code=2):
    print('credential: refused: ' + message, file=sys.stderr)
    sys.exit(code)


def exclusive(path, mode=0o600):
    return open(path, 'wb', opener=lambda p, f: os.open(p, f | os.O_CREAT | os.O_EXCL, mode))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True, type=Path, help='private AP target JSON with an ssid field')
    parser.add_argument('--expect-boot-id', required=True, help='live Gemian boot id verified beforehand')
    parser.add_argument('--output-dir', required=True, type=Path, help='fresh directory; refused if it exists')
    parser.add_argument('--host', default='gemini', help='ssh host alias of the known-good Gemian endpoint')
    parser.add_argument('--identity', type=Path, help='optional private key file for ssh -i')
    parser.add_argument('--ssh', default='ssh', help=argparse.SUPPRESS)
    parser.add_argument('--diagnose', action='store_true',
                        help='metadata only: candidate count and field occurrence counts; reads no value')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        target = json.loads(args.target.read_text())
    except (OSError, ValueError):
        refuse('target file unreadable or not JSON')
    ssid = target.get('ssid') if isinstance(target, dict) else None
    if not isinstance(ssid, str) or not 1 <= len(ssid.encode()) <= 32 or any(c in ssid for c in '\n\r\0'):
        refuse('target ssid missing or not a plain SSID')
    import re
    if not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', args.expect_boot_id):
        refuse('boot id must be a UUID')
    if args.output_dir.exists():
        refuse('output directory already exists')
    if args.identity and (not args.identity.is_file() or stat.S_IMODE(args.identity.stat().st_mode) & 0o077):
        refuse('identity file missing or not mode 0600')
    ssh = [args.ssh, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no',
           '-o', 'IdentitiesOnly=yes', '-o', 'IdentityAgent=none', '-o', 'ConnectTimeout=20']
    if args.identity:
        ssh += ['-i', str(args.identity)]
    remote = 'sudo -n python3 - / %s %s %s %s %s' % (base64.b64encode(ssid.encode()).decode(), args.expect_boot_id,
                                                    EXPECTED_KERNEL, EXPECTED_DEBIAN,
                                                    'diagnose' if args.diagnose else 'extract')
    args.output_dir.mkdir(mode=0o700, parents=False)
    report_file = args.output_dir / 'remote-report'
    try:
        with exclusive(report_file) as out:
            result = subprocess.run(ssh + ['--', args.host, remote], input=REMOTE.encode(),
                                    stdout=out, stderr=subprocess.DEVNULL, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        refuse('ssh session failed to run')
    if result.returncode != 0:
        refuse('remote read failed (exit %d)' % result.returncode)
    report = {}
    for line in report_file.read_bytes().split(b'\n'):
        if b'=' in line:
            key, _, val = line.partition(b'=')
            name = key.decode('ascii', 'replace')
            if name in report:
                refuse('malformed remote report (duplicate key)')
            report[name] = val
    needed = ('before_boot', 'before_kernel', 'before_debian', 'status', 'problems', 'after_boot', 'after_kernel', 'after_debian')
    if any(k not in report for k in needed):
        refuse('incomplete remote report')
    for tag in ('before', 'after'):
        if report[tag + '_boot'].decode('ascii', 'replace') != args.expect_boot_id:
            refuse('live boot id differs from the expected Gemian boot (%s)' % tag)
        if report[tag + '_kernel'] != EXPECTED_KERNEL.encode() or report[tag + '_debian'] != EXPECTED_DEBIAN.encode():
            refuse('live system is not Gemian %s on Debian %s (%s)' % (EXPECTED_KERNEL, EXPECTED_DEBIAN, tag))
    if args.diagnose:
        if report['status'] != b'diagnosed':
            refuse('remote status ' + report['status'].decode('ascii', 'replace'))
        wanted = ('name_count', 'security_count', 'passphrase_count', 'security_is_psk')
        counts = {k: v.decode('ascii', 'replace') for k, v in report.items()
                  if k in ('candidates', 'problems') or (k.startswith('group') and '_' in k and k.split('_', 1)[1] in wanted)}
        print('credential: diagnosis ' + ' '.join('%s=%s' % kv for kv in sorted(counts.items())))
        return
    if report['status'] != b'ok':
        refuse('remote status ' + report['status'].decode('ascii', 'replace'))
    settings = report['settings'].decode('ascii', 'replace')
    if not re.fullmatch(r'/var/lib/connman/wifi_[0-9a-f]+_[0-9a-f]+_managed_psk/settings', settings):
        refuse('unexpected connman service path shape')
    try:
        passphrase = base64.b64decode(report['passphrase_b64'], validate=True)
    except ValueError:
        refuse('malformed secret encoding')
    if not 8 <= len(passphrase) <= 63 or b'\n' in passphrase or b'\0' in passphrase:
        refuse('passphrase is not one WPA2 passphrase')
    psk = hashlib.pbkdf2_hmac('sha1', passphrase, ssid.encode(), 4096, 32)
    with exclusive(args.output_dir / 'passphrase') as out:
        out.write(passphrase)
    with exclusive(args.output_dir / 'psk.hex') as out:
        out.write(psk.hex().encode() + b'\n')
    del passphrase
    for name in ('remote-report', 'passphrase', 'psk.hex'):
        if stat.S_IMODE((args.output_dir / name).stat().st_mode) != 0o600:
            refuse('output file mode is not 0600')
    provenance = {
        'source': 'gemian-connman-settings', 'remote_settings_path': settings,
        'gemian_boot_id': args.expect_boot_id, 'gemian_kernel_release': EXPECTED_KERNEL, 'debian_version': EXPECTED_DEBIAN,
        'identity_checked': 'before and after the read, in the same ssh session',
        'parser': 'GLib g_key_file_get_string on the device through ctypes',
        'remote_problem_services': int(report['problems']),
        'ssid_sha256': hashlib.sha256(ssid.encode()).hexdigest(),
        'psk_sha256': hashlib.sha256(psk).hexdigest(),
        'derivation': 'pbkdf2-hmac-sha1 4096 rounds, salt = ssid, 32 bytes',
        'created_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'files': ['remote-report (0600, holds the secret base64)', 'passphrase (0600)', 'psk.hex (0600)'],
    }
    (args.output_dir / 'provenance.json').write_text(json.dumps(provenance, indent=1) + '\n')
    print('credential: prepared one private input set in ' + str(args.output_dir) + ' (no secret shown)')


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception:  # never print a traceback that could carry a value
        refuse('unexpected failure', 3)
