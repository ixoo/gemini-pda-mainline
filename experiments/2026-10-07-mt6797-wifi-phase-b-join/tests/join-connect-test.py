#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""join-connect builds exactly the privacy-flagged open-system connect request.

Compiles the helper natively with ASan/UBSan, runs its --dump mode and parses
the netlink message: generic netlink header for NL80211_CMD_CONNECT, then the
attributes IFINDEX, SSID, WIPHY_FREQ, MAC, PRIVACY (flag) and AUTH_TYPE open
system, and nothing else (no key, cipher, IE or scan attribute). Negative
boundaries: SSID empty or 33 bytes, frequency other than 5200, malformed,
multicast or zero BSSID, wrong interface name, bad argument counts. Nothing
is sent; no socket is opened in dump mode.
"""
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SOURCE = HERE / 'helper/join-connect.c'
NL80211_CMD_CONNECT = 46
ATTR = {'IFINDEX': 3, 'MAC': 6, 'SSID': 52, 'WIPHY_FREQ': 38, 'PRIVACY': 70, 'AUTH_TYPE': 53}
NAMES = {v: k for k, v in ATTR.items()}

with tempfile.TemporaryDirectory(prefix='mt6797-join-connect-') as directory:
    binary = Path(directory) / 'join-connect'
    subprocess.run(['cc', '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-o', str(binary), str(SOURCE)], check=True)
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')

    # Sanitized binaries on the build hosts need ASLR disabled, as the other
    # fixture runners do, or a sanitizer stop can spin instead of reporting.
    prefix = ['setarch', os.uname().machine, '-R']

    def run(*args):
        return subprocess.run([*prefix, str(binary), *args], capture_output=True, env=env, timeout=30)

    good = run('--dump', '7', 'example-net', '5200', '02:11:22:33:44:55')
    assert good.returncode == 0 and good.stderr == b'', good
    raw = bytes.fromhex(good.stdout.decode().strip())
    length, msg_type, flags, seq, pid = struct.unpack_from('<IHHII', raw, 0)
    assert length == len(raw) and msg_type == 0x1234 and flags == 0x5 and seq == 2 and pid == 0, "connect uses its own sequence 2"
    cmd, version, _ = struct.unpack_from('<BBH', raw, 16)
    assert cmd == NL80211_CMD_CONNECT and version == 0
    offset, seen = 20, []
    while offset < len(raw):
        nla_len, nla_type = struct.unpack_from('<HH', raw, offset)
        payload = raw[offset + 4:offset + nla_len]
        seen.append((NAMES.get(nla_type, nla_type), payload))
        offset += (nla_len + 3) & ~3
    assert offset == len(raw)
    assert [name for name, _ in seen] == ['IFINDEX', 'SSID', 'WIPHY_FREQ', 'MAC', 'PRIVACY', 'AUTH_TYPE'], seen
    values = dict(seen)
    assert struct.unpack('<I', values['IFINDEX'])[0] == 7
    assert values['SSID'] == b'example-net'
    assert struct.unpack('<I', values['WIPHY_FREQ'])[0] == 5200
    assert values['MAC'] == bytes.fromhex('021122334455')
    assert values['PRIVACY'] == b''
    assert struct.unpack('<I', values['AUTH_TYPE'])[0] == 0, 'open system'
    # 32-byte SSID is the maximum; non-ASCII bytes pass through unchanged.
    assert run('--dump', '7', 'x' * 32, '5200', '02:11:22:33:44:55').returncode == 0
    for bad in (('--dump', '7', '', '5200', '02:11:22:33:44:55'),
                ('--dump', '7', 'x' * 33, '5200', '02:11:22:33:44:55'),
                ('--dump', '7', 'net', '5180', '02:11:22:33:44:55'),
                ('--dump', '7', 'net', '5200', '03:11:22:33:44:55'),      # multicast
                ('--dump', '7', 'net', '5200', '00:00:00:00:00:00'),
                ('--dump', '7', 'net', '5200', '02:11:22:33:44'),
                ('--dump', '7', 'net', '5200', '02:11:22:33:44:5g'),
                ('--dump', '7', 'net', '5200', '02:11:22:33:44:-5'),
                ('--dump', '0', 'net', '5200', '02:11:22:33:44:55'),
                ('--dump', '7', 'net', '5200'),
                ('eth0', 'net', '5200', '02:11:22:33:44:55'),             # not the admitted wlan0
                ('wlan0', 'net', '5200')):
        result = run(*bad)
        assert result.returncode == 1 and result.stdout == b'', (bad, result)
print('join-connect: PASS (privacy-flagged open-system connect request; attribute set exact; boundaries refused)')

# Production transport fixture: the helper's own source with a scripted kernel.
with tempfile.TemporaryDirectory(prefix='mt6797-join-connect-transport-') as directory:
    helper = Path(directory) / 'join-connect'
    subprocess.run(['cc', '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-o', str(helper), str(SOURCE)], check=True)
    binary = Path(directory) / 'transport-test'
    subprocess.run(['cc', '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-o', str(binary), str(HERE / 'tests/join-connect-transport-test.c')], check=True)
    out = subprocess.run(['setarch', os.uname().machine, '-R', str(binary)], capture_output=True, timeout=30,
                         env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
    assert out.returncode == 0 and out.stdout.strip().splitlines()[-1] == b'transport=pass', out
    # Real host-side generic netlink: one bounded lookup with its data reply and
    # acknowledgement against the running kernel, no connect, no interface.
    # nlctrl is always family 16; an unknown name is acknowledged with -ENOENT.
    smoke = subprocess.run([*prefix, str(helper), '--family-lookup', 'nlctrl'], capture_output=True,
                           timeout=30, env=env)
    assert smoke.returncode == 0 and smoke.stdout.strip() == b'family=16', smoke
    # The real nl80211 reply exceeds 512 bytes; when cfg80211 is present on the
    # host its lookup must succeed, which proves the reply-sized destination.
    if Path('/sys/module/cfg80211').exists():
        big = subprocess.run([*prefix, str(helper), '--family-lookup', 'nl80211'], capture_output=True,
                             timeout=30, env=env)
        assert big.returncode == 0 and big.stdout.startswith(b'family='), big
    unknown = subprocess.run([*prefix, str(helper), '--family-lookup', 'no-such-family-x'],
                             capture_output=True, timeout=30, env=env)
    assert unknown.returncode == 2 and unknown.stdout == b'', unknown
print('join-connect transport: PASS (distinct sequences, header PID not required, combined datagrams, family ack consumed before connect, kernel -95 retained, one request, bounded; real nlctrl lookup framing)')
